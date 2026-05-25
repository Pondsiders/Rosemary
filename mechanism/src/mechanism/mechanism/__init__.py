"""The `mechanism` MCP server — hook-shaped tools invokable over MCP transport.

Exposed via the `mcp_tool` hook type so Claude Code harnesses can invoke
these from anywhere on the tailnet (no localhost-HTTP assumption).

The `mcp` instance lives in `server`; tool modules are imported here for
their side effects (each module's `@mcp.tool` decorator registers its
tool against the shared instance). Mounting `mcp.http_app(...)` inside
the Starlette parent picks up the full tool surface.
"""

from mechanism.mechanism import anamneses, livez, memories, reflection, timestamp
from mechanism.mechanism.server import mcp

# Side-effect imports — silence the unused-import warnings.
_ = (anamneses, livez, memories, reflection, timestamp)

__all__ = ["mcp"]
