# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Git conventions

Use conventional-commit style for commit messages. Unless otherwise noted, the first author on Git commits should be "Alpha <alpha@alphafornow.com>" with co-authored-by going to "Jeffery Harrell <jefferyharrell@gmail.com>".

## Repository layout

This is a small monorepo. The only source tree is `alpha-server/` (a Python package); everything at the repo root is infra glue (Docker Compose for local dev, a Tailscale sidecar config for prod, a `justfile`, a `.env` shared by both halves).

## Commands

All `just` recipes run from the repo root; all `uv` commands run from `alpha-server/`.

Dev environment (Postgres+pgvector and Redis in Docker):

```
just dev-up                # start
just dev-down              # stop (data preserved)
just dev-init <dump.sql>   # WIPE volumes and pg_restore from a dump
```

Server, tests, lint, typecheck (from `alpha-server/`):

```
uv sync --all-extras
uv run uvicorn alpha_server.app:app --host 127.0.0.1 --port 8000
uv run pytest
uv run pytest tests/test_read_from_diary.py::test_read_from_diary_returns_recent_entries
uv run ruff check
uv run ruff format
uv run basedpyright
```

`pytest` is `asyncio_mode=auto` and the existing test is an **integration test** — it spins up the FastMCP server in-process but expects Postgres reachable at `DATABASE_URL` with the `cortex` schema populated. Run `just dev-init` first.

## Architecture

`alpha_server.app:app` is a single FastAPI app that mounts two distinct surfaces behind one bearer-token middleware:

- **`/cortex/mcp`** — a FastMCP server exposing memory/diary tools to the Alpha client over Streamable HTTP. Built by `mcp.http_app(path="/mcp")` and mounted as a sub-ASGI app; its lifespan is composed into the outer FastAPI lifespan (omitting this hand-off causes tool calls to hang).
- **`/hooks/*`** — Claude Code `UserPromptSubmit` hook endpoints (`/hooks/timestamp`, `/hooks/memories`) that return `additionalContext` strings.
- **`/livez`** — the one route that bypasses auth (see `_PUBLIC_PATHS` in `auth.py`).

### Side-effect registration pattern

Both the Cortex tool surface and the hooks surface use the same trick: a shared registry object is created in one module, and feature modules register against it via decorators at import time. Importing the feature module **is** what wires it up.

- `cortex/server.py` creates the `mcp: FastMCP` instance; each tool module (`add_to_diary.py`, `read_from_diary.py`, `get_schema.py`, `execute_query.py`) decorates a function with `@mcp.tool`. `cortex/__init__.py` does a side-effect import of all four.
- `hooks/__init__.py` creates `router: APIRouter`; each hook module (`timestamp.py`, `memories.py`) decorates a handler with `@router.post(...)`. `app.py` does the side-effect imports (with `# noqa: F401`).

When adding a tool or hook, follow this pattern: write the module, then add it to the side-effect import in the corresponding `__init__`/`app.py`. Failing to add the import means the surface silently won't appear.

### Long-lived clients on `app.state`

The lifespan in `app.py` owns process-singleton clients and exposes them via `app.state`:

- `app.state.chat_client` / `chat_model` — OpenAI-protocol client pointed at the Bifrost gateway (used by `hooks/memories.py` to extract semantic queries from prompts).
- `app.state.embedding_client` / `embedding_model` — embedding client (used by the memories hook to embed queries before pgvector search).
- `app.state.redis` — async Redis client (per-session ephemeral state: `seen:<session_id>` set for memory recall, `last-msg:<session_id>` for the timestamp hook).

Hook handlers receive `request: Request` and pull these off `request.app.state`. Don't construct new OpenAI/Redis clients per-request.

### Database

`db.py` holds a process-singleton `asyncpg.Pool` (`get_pool()`), lazily created on first call. Two non-obvious things:

- pgvector is registered against the `extensions` schema and the connection startup `search_path` is `public, extensions` (passed via `server_settings`, not `SET` — `SET` gets wiped on connection reset between borrows). Application tables are still schema-qualified (`cortex.memories`, `cortex.diary`).
- The dev compose stack uses `pgvector/pgvector:pg17`; in production pgvector lives in the `extensions` schema. The search-path setup tolerates either layout — a fork whose DB has pgvector in `public` will still resolve operators.

The `execute_query` MCP tool runs in a `readonly=True` transaction with a 5s statement timeout; writes fail at the Postgres level with error 25006.

### Time

`clock.py` is the single canonical home for date/time work — other modules **do not import `datetime`, `time`, or `pendulum` directly**. PSO-8601 is the project's house format (`"Sun May 17 2026, 10:23 AM"`); "day" boundaries run from 6 AM local to 6 AM local (see `start_of_day`). The local timezone is configured via the `TIMEZONE` env var.

### Settings

`settings.py` uses Pydantic Settings; `get_settings()` is `lru_cache`'d. The `.env` file is resolved relative to `settings.py` (three parents up = repo root), and `extra="forbid"` means a stray env var will fail startup loudly. All required env vars are listed as fields on the `Settings` class.

### Auth

`BearerTokenMiddleware` (Starlette base middleware) compares `Authorization: Bearer <token>` against `AUTH_TOKEN` with `hmac.compare_digest`. Implemented as Starlette middleware (not a FastAPI dependency) so it applies uniformly to both the FastAPI routes and the mounted FastMCP sub-app.

## Conventions

- Python 3.12+, `from __future__ import annotations` at the top of every module.
- Ruff strict rule set (`E,W,F,I,B,UP,S,SIM,RUF,D`) with Google docstring convention. Tests are exempt from `S101` and `D10x`. `__init__.py` is exempt from `D104`; `__main__.py` from `D100`.
- basedpyright is configured for `recommended` typecheckingMode with `reportExplicitAny` and `reportAny` disabled (deliberate — `Any` is honest at JSON boundaries we control).
- No `print()` for observability; the server is meant to run under uvicorn and write JSON to stdout in production.

## Production deployment

`compose.yml` (the prod stack) runs only a Tailscale sidecar that terminates HTTPS on the tailnet (`tailscale/serve-config.json` proxies `:443` → `127.0.0.1:8000`). The `alpha-server` Python process runs on the host, not in a container. `compose-dev.yml` is the local stack (Postgres + Redis only).
