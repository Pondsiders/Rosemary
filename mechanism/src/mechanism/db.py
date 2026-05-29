"""Asynchronous database helpers.

The async pool is lazily created on first use and lives for the lifetime
of the process. `get_pool()` is the single entry point — callers acquire
connections from the returned pool via `async with pool.acquire() as conn:`.
"""

from __future__ import annotations

import asyncpg
from pgvector.asyncpg import (  # pyright: ignore[reportMissingTypeStubs]
    register_vector,  # pyright: ignore[reportUnknownVariableType]
)

from mechanism.settings import get_settings

_pool: asyncpg.Pool | None = None


async def _init_connection(conn: asyncpg.Connection) -> None:
    """Per-connection setup: register the pgvector codec (extension lives in public)."""
    await register_vector(conn, schema="public")


async def get_pool() -> asyncpg.Pool:
    """Return the process-singleton asyncpg pool, creating it on first call.

    pgvector is installed in the `public` schema, which is always on the
    default search_path — so its operators (`<=>`, `<->`, `<#>`) and the
    `vector` type resolve with no search_path manipulation at all. Infix
    operators can only resolve via search_path, so `public` is the one
    placement where they work natively; putting pgvector anywhere else
    would force the search_path magic we deliberately avoid.

    Application tables are explicitly schema-qualified everywhere they're
    used (`cortex.memories`, `cortex.diary`, `sage.messages`, etc.). The
    only thing leaning on default resolution is the pgvector intrinsics in
    public — exactly where the universal default belongs.
    """
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=str(get_settings().database_url),
            min_size=1,
            max_size=4,
            init=_init_connection,
        )
    return _pool


async def close_pool() -> None:
    """Close the singleton asyncpg pool if it's open. Called from the app lifespan."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
