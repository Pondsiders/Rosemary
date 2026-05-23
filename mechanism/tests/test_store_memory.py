"""Integration test for `store_memory` against a live dev database.

Requires Postgres reachable at the configured DATABASE_URL and the
embedding service reachable at EMBEDDING_BASE_URL. Run via `uv run pytest`.

This test WRITES one row to cortex.memories per run. The dev DB is
disposable (next `just dev-init` wipes it), and the row is marked with
a [TEST] prefix so it's identifiable in the DB.
"""

from __future__ import annotations

from typing import Any

from fastmcp import Client

from mechanism.cortex import mcp
from mechanism.db import get_pool


async def test_store_memory_writes_a_row_with_embedding() -> None:
    """Calling store_memory inserts a row with content + a non-null embedding."""
    content = "[TEST] integration test from test_store_memory"

    async with Client(mcp) as client:
        result = await client.call_tool("store_memory", {"content": content})

    assert result.structured_content is not None
    payload: dict[str, Any] = result.structured_content
    new_id = int(payload["id"])
    assert new_id > 0
    assert isinstance(payload["created_at"], str)
    assert len(payload["created_at"]) > 0

    # Re-fetch the row directly to confirm content + embedding landed.
    pool = await get_pool()
    async with pool.acquire() as conn:
        sql = (
            "SELECT content, embedding_qwen IS NOT NULL AS has_embedding "
            "FROM cortex.memories WHERE id = $1"
        )
        row = await conn.fetchrow(sql, new_id)
    assert row is not None
    assert row["content"] == content
    assert row["has_embedding"] is True
