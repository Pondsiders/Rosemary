"""The `sage` MCP server — Sage-archive recall as a hook-shaped tool.

Exposed via the `mcp_tool` hook type so the Claude Code harness can invoke
`recall` on `UserPromptSubmit` from anywhere on the tailnet.

The `mcp` instance lives in `server`; tool modules are imported here for
their side effects (each module's `@mcp.tool` decorator registers its tool
against the shared instance). Mounting `mcp.http_app(...)` inside the
Starlette parent picks up the full tool surface.
"""

from mechanism.sage import recall
from mechanism.sage.server import mcp

# Side-effect import — silence the unused-import warning.
_ = (recall,)

__all__ = ["mcp"]
