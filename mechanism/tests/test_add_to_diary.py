"""Integration test for the `add_to_diary` MCP tool.

End-to-end via FastMCP's in-process client (`Client(mcp)`) against the test
stack's Postgres. Asserts the tool's return contract (id + created_at) and
that the row actually lands in `cortex.diary` with the content we sent.

Japanese content here is a small preview of the fluorescent-dye seed plan —
test data that's visually unmistakable from anything that would naturally
appear in production recall.
"""

from __future__ import annotations

from typing import Any

from fastmcp import Client

from mechanism.cortex import mcp
from mechanism.db import get_pool


async def test_add_to_diary_writes_a_row() -> None:
    """add_to_diary inserts a row in cortex.diary that round-trips verbatim."""
    content = "テストの日記エントリ — 蛍光染料"  # "test diary entry — fluorescent dye"

    async with Client(mcp) as client:
        result = await client.call_tool("add_to_diary", {"content": content})

    assert result.structured_content is not None
    payload: dict[str, Any] = result.structured_content
    new_id = int(payload["id"])
    assert new_id > 0
    assert isinstance(payload["created_at"], str)
    assert len(payload["created_at"]) > 0

    # Verify the row is actually in cortex.diary with the content we sent.
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT content FROM cortex.diary WHERE id = $1", new_id)
    assert row is not None
    assert row["content"] == content
