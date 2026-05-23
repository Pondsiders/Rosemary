"""Integration test for the `read_from_diary` MCP tool.

Asserts that read_from_diary returns the seeded diary entries from today,
in ascending created_at order, with verbatim content. Seed loads three
Japanese entries with minute-scale staggered timestamps (all firmly inside
the 6 AM day boundary regardless of test-run time).
"""

from __future__ import annotations

from typing import Any

from fastmcp import Client

from mechanism.cortex import mcp


async def test_read_from_diary_returns_seed_entries_ascending(
    seeded: None,  # pyright: ignore[reportUnusedParameter]
) -> None:
    """read_from_diary returns the 3 seeded entries in ascending created_at order."""
    async with Client(mcp) as client:
        result = await client.call_tool("read_from_diary", {})

    assert result.structured_content is not None
    entries: list[dict[str, Any]] = result.structured_content["result"]
    assert len(entries) == 3

    # Seed inserts three diary rows; with TRUNCATE ... RESTART IDENTITY they
    # take ids 1, 2, 3 in the seed-file order.
    assert [e["id"] for e in entries] == [1, 2, 3]
    assert entries[0]["content"] == "朝、猫カフェに出かけた。"
    assert entries[1]["content"] == "昼ご飯はサンドイッチだった。"
    assert entries[2]["content"] == "夕方、雨が降り始めた。"
