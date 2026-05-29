"""The FastMCP server instance for the `sage` archive-recall surface.

Tool modules import `mcp` from here and register themselves via the
`@mcp.tool` decorator. The package `__init__` imports the tool modules
for their side effects, so that mounting this server's ASGI app picks
up the full tool surface.

`sage` is a deploy-specific surface: it exists in Rosemary's repo (she
inherits Kylee's conversation archive) and not in Alpha's. Keeping it on
its own server rather than folding it into `mechanism` makes the fork
divergence a single mount point instead of a Sage-shaped lump in the
shared core.
"""

from __future__ import annotations

from importlib.metadata import version
from pathlib import Path

from fastmcp import FastMCP

from mechanism.auth import get_auth_verifier

_INSTRUCTIONS = (Path(__file__).parent / "instructions.md").read_text(encoding="utf-8")

mcp: FastMCP = FastMCP(
    "sage",
    instructions=_INSTRUCTIONS,
    version=version("mechanism"),
    auth=get_auth_verifier(),
)
