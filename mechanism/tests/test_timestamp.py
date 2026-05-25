"""Integration test for the `timestamp` MCP tool.

Pins the response shape — a UserPromptSubmit hook envelope with a
non-empty `additionalContext` string. The exact wording isn't pinned
(the prose can evolve); the structural contract is what tests catch.
"""

from __future__ import annotations

from typing import Any

from fastmcp import Client

from mechanism.mechanism import mcp


async def test_timestamp_returns_user_prompt_submit_envelope() -> None:
    """timestamp() returns a UserPromptSubmit hook envelope with non-empty additionalContext."""
    async with Client(mcp) as client:
        result = await client.call_tool("timestamp", {})

    assert result.structured_content is not None
    payload: dict[str, Any] = result.structured_content
    hook_output = payload["hookSpecificOutput"]
    assert hook_output["hookEventName"] == "UserPromptSubmit"
    additional_context = hook_output["additionalContext"]
    assert isinstance(additional_context, str)
    assert additional_context.startswith("The user sent this message on ")
