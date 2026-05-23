"""Integration test for the `recent_memories` MCP tool.

Asserts that recent_memories(limit=N) returns the N most recently created
memories in ascending-within-batch order. Seed loads 7 memories with
minute-scale staggered created_at; the most recent three (in seed order)
are the umbrella decoy, the philosophy-book decoy, and the sentinel.
"""

from __future__ import annotations

from typing import Any

from fastmcp import Client

from mechanism.cortex import mcp


async def test_recent_memories_returns_latest_seed_ascending(
    seeded: None,  # pyright: ignore[reportUnusedParameter]
) -> None:
    """recent_memories(limit=3) returns ids [5, 6, 7] in ascending order."""
    async with Client(mcp) as client:
        result = await client.call_tool("recent_memories", {"limit": 3})

    assert result.structured_content is not None
    memories: list[dict[str, Any]] = result.structured_content["result"]
    assert len(memories) == 3

    # Seed inserts 7 memories oldest-first; with `recent_memories` taking the
    # latest-3-then-reverse, we get ids [5, 6, 7] in ascending order. The
    # last memory (newest) is the English fixture sentinel.
    assert [m["id"] for m in memories] == [5, 6, 7]
    assert memories[-1]["content"].startswith("[FIXTURE SENTINEL")
