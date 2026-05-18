"""Integration test for `read_from_diary` against a live dev database.

Requires Postgres reachable at the configured DATABASE_URL with cortex.diary
populated. Run via `uv run pytest`.
"""

from __future__ import annotations

from typing import Any

from fastmcp import Client

from alpha_server.cortex import mcp


async def test_read_from_diary_returns_recent_entries() -> None:
    """Calling read_from_diary against a populated dev DB returns a list."""
    async with Client(mcp) as client:
        result = await client.call_tool("read_from_diary", {})
    # The exact contents depend on the restored dump, but the call should
    # succeed and return a structured list (possibly empty if the window is
    # outside any stored entries).
    assert result.structured_content is not None
    entries: list[dict[str, Any]] = result.structured_content.get("result", [])
    assert isinstance(entries, list)
    for entry in entries:
        assert "id" in entry
        assert "content" in entry
        assert "created_at" in entry
