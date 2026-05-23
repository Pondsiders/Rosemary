# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Special rule for this repository specifically

Don't commit anything to git until Jeffery has had a chance to review and approve it.

## Git conventions

Use conventional-commit style for commit messages. Unless otherwise noted, the first author on Git commits should be "Alpha <alpha@alphafornow.com>" with co-authored-by going to "Jeffery Harrell <jefferyharrell@gmail.com>".

## Repository layout

This is a small monorepo. The only source tree is `mechanism/` (a Python package); everything at the repo root is infra glue (a `Dockerfile` and `compose.yml` for production, `compose-dev.yml` for the local dev stack, a `justfile`, a `.env` shared by both halves).

## Commands

All `just` recipes run from the repo root; all `uv` commands run from `mechanism/`.

Dev environment runs in Docker — Postgres+pgvector, Redis, and `mechanism` with uvicorn `--reload` on `127.0.0.1:8001`. Project name is `alpha-dev`.

```
just dev-up                # start
just dev-down              # stop (data preserved)
just dev-init <dump.sql>   # WIPE volumes and pg_restore from a dump
```

Server, tests, lint, typecheck (from `mechanism/`):

```
uv sync
uv run uvicorn mechanism.app:app --host 127.0.0.1 --port 8000
uv run pytest
uv run pytest tests/test_read_from_diary.py::test_read_from_diary_returns_recent_entries
uv run ruff check
uv run ruff format
uv run basedpyright
```

`pytest` is `asyncio_mode=auto` and the existing test is an **integration test** — it spins up the FastMCP server in-process but expects Postgres reachable at `DATABASE_URL` with the `cortex` schema populated. Run `just dev-init` first.

## Architecture

`mechanism.app:app` is a single FastAPI app that mounts two distinct surfaces:

- **`/cortex/mcp`** — a FastMCP server exposing memory/diary tools to the Alpha client over Streamable HTTP. Built by `mcp.http_app(path="/mcp")` and mounted as a sub-ASGI app; its lifespan is composed into the outer FastAPI lifespan (omitting this hand-off causes tool calls to hang).
- **`/hooks/*`** — Claude Code hook endpoints. `/hooks/timestamp` and `/hooks/memories` are `UserPromptSubmit` hooks that return `additionalContext` strings. `/hooks/reflection` is a `Stop` hook with a different envelope shape: it returns `{"decision": "block", "reason": ...}` to fire a between-turns reminder (Stop hooks don't use `additionalContext`). The reflection handler must short-circuit when `stop_hook_active=true` to avoid recursion.
- **`/livez`** — an unauthenticated health check.

### Side-effect registration pattern

Both the Cortex tool surface and the hooks surface use the same trick: a shared registry object is created in one module, and feature modules register against it via decorators at import time. Importing the feature module **is** what wires it up.

- `cortex/server.py` creates the `mcp: FastMCP` instance; each tool module (`add_to_diary.py`, `read_from_diary.py`, `search_memories.py`, `store_memory.py`, `get_memory.py`, `recent_memories.py`) decorates a function with `@mcp.tool`. `cortex/__init__.py` does a side-effect import of them all. Tool result shapes live in `cortex/models.py`; the server's tool-surface prose lives in `cortex/instructions.md` (read at startup by `server.py`).
- `hooks/__init__.py` creates `router: APIRouter`; each hook module (`timestamp.py`, `memories.py`, `reflection.py`) decorates a handler with `@router.post(...)`. `app.py` does the side-effect imports (with `# noqa: F401`).

When adding a tool or hook, follow this pattern: write the module, then add it to the side-effect import in the corresponding `__init__`/`app.py`. Failing to add the import means the surface silently won't appear.

### Long-lived clients

Two patterns, both process-singleton, both shared by hooks and MCP tools:

- **`llm.py`** — lazy module-level singletons for the OpenAI-protocol chat and embedding clients (Bifrost gateway). `get_chat_client()` / `get_chat_model()` / `get_embedding_client()` / `get_embedding_model()` construct on first call and return the same instance thereafter. No lifespan hand-off. `db.py`'s `get_pool()` follows the same shape. `llm.py` also owns `format_query_for_embedding()` — the Qwen 3 Embedding 4B input shape lives there because swapping the embedding model means revisiting both this prefix and re-embedding `cortex.memories`.
- **`app.state.redis`** — async Redis client, opened in the FastAPI lifespan and closed on shutdown. Hook handlers take `request: Request` and pull this off `request.app.state` (don't construct new Redis clients per-request). Three key families share the database: `seen:<session_id>` (memories-hook recall dedupe), `last-msg:<session_id>` (timestamp hook), and `reflection:turn:<session_id>` (reflection-hook turn counter, fires every third turn).

### Database

`db.py` holds a process-singleton `asyncpg.Pool` (`get_pool()`), lazily created on first call. Two non-obvious things:

- pgvector is registered against the `extensions` schema and the connection startup `search_path` is `public, extensions` (passed via `server_settings`, not `SET` — `SET` gets wiped on connection reset between borrows). Application tables are still schema-qualified (`cortex.memories`, `cortex.diary`).
- The dev compose stack uses `pgvector/pgvector:pg17`; in production pgvector lives in the `extensions` schema. The search-path setup tolerates either layout — a fork whose DB has pgvector in `public` will still resolve operators.

### Time

`clock.py` is the single canonical home for date/time work — other modules **do not import `datetime`, `time`, or `pendulum` directly**. PSO-8601 is the project's house format (`"Sun May 17 2026, 10:23 AM"`); "day" boundaries run from 6 AM local to 6 AM local (see `start_of_day`). The local timezone is configured via the `TIMEZONE` env var.

### Settings

`settings.py` uses Pydantic Settings; `get_settings()` is `lru_cache`'d. The `.env` file is resolved relative to `settings.py` (three parents up = repo root), and `extra="forbid"` means a stray env var will fail startup loudly. All required env vars are listed as fields on the `Settings` class.

## Conventions

- Commit `uv.lock`. We're an application, not a library; reproducibility across machines and deploys wins.
