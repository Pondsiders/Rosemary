"""Integration test for `get_memory` against a live dev database.

Requires Postgres reachable at the configured DATABASE_URL with cortex.memories
populated. Run via `uv run pytest`.
"""

from __future__ import annotations

from typing import Any

from fastmcp import Client

from mechanism.cortex import mcp


async def test_get_memory_returns_the_matching_row() -> None:
    """A get_memory call against a known-good id returns that memory."""
    async with Client(mcp) as client:
        # First, find a valid id via recent_memories so this test doesn't
        # hard-code an id that might not exist in a freshly-restored dev DB.
        recent = await client.call_tool("recent_memories", {"limit": 1})
        assert recent.structured_content is not None
        recent_memories: list[dict[str, Any]] = recent.structured_content.get("result", [])
        assert len(recent_memories) == 1
        target_id = int(recent_memories[0]["id"])

        result = await client.call_tool("get_memory", {"memory_id": target_id})

    assert result.structured_content is not None
    memory: dict[str, Any] = result.structured_content
    assert memory["id"] == target_id
    assert "content" in memory
    assert "created_at" in memory
    assert "age" in memory


async def test_get_memory_missing_id_returns_tool_error() -> None:
    """A get_memory call against a nonexistent id surfaces as a tool error."""
    async with Client(mcp) as client:
        result = await client.call_tool(
            "get_memory", {"memory_id": 999_999_999}, raise_on_error=False
        )
    assert result.is_error
