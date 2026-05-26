"""The `timestamp` tool — temporal grounding for UserPromptSubmit.

Returns a Claude Code UserPromptSubmit hook envelope with the current
local timestamp as ``additionalContext``.
"""

from __future__ import annotations

from mcp.types import ToolAnnotations

from mechanism import clock
from mechanism.mechanism.server import mcp


@mcp.tool(
    description=(
        "Return temporal grounding for the current user prompt as a "
        "UserPromptSubmit hook response. Sets `additionalContext` to a "
        "one-line 'was sent at' string."
    ),
    annotations=ToolAnnotations(
        title="Timestamp",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=False,
    ),
    meta={"anthropic/alwaysLoad": True},
)
async def timestamp() -> dict[str, dict[str, str]]:
    """Return a UserPromptSubmit hook response with a one-line timestamp note."""
    return {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": (f"The user sent this message on {clock.pso8601(clock.now())}."),
        }
    }
