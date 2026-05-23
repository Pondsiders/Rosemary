"""Utils MCP server — mounted at /utils/mcp, tools registered by side effect.

The `mcp` instance lives in `server`; tool modules are imported here for
their side effects (each module's `@mcp.tool` decorator registers its tool
against the shared instance). Mounting `mcp.http_app(...)` inside the
FastAPI app picks up the full tool surface.
"""

from mechanism.utils import fetch
from mechanism.utils.server import mcp

# Side-effect import — silence the unused-import warning.
_ = (fetch,)

__all__ = ["mcp"]
