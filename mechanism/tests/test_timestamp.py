"""Integration test for the `timestamp` MCP tool.

Pins the wire shape: ``structured_content`` is a UserPromptSubmit hook
envelope; ``content`` carries the same envelope as a JSON-encoded
``TextContent``. The ``additionalContext`` wording isn't pinned, only the
structure.
"""

from __future__ import annotations

import json
from typing import Any

from fastmcp import Client
from mcp.types import TextContent

from mechanism.mechanism import mcp


async def test_timestamp_returns_user_prompt_submit_envelope() -> None:
    """timestamp() returns a UserPromptSubmit hook envelope on both wire surfaces."""
    async with Client(mcp) as client:
        result = await client.call_tool("timestamp", {})

    assert result.is_error is False

    assert result.structured_content is not None
    structured: dict[str, Any] = result.structured_content
    hook_output = structured["hookSpecificOutput"]
    assert hook_output["hookEventName"] == "UserPromptSubmit"
    additional_context = hook_output["additionalContext"]
    assert isinstance(additional_context, str)
    assert additional_context.startswith("The user sent this message on ")

    assert len(result.content) == 1
    block = result.content[0]
    assert isinstance(block, TextContent)
    assert block.type == "text"
    text_envelope = json.loads(block.text)
    assert text_envelope == structured
