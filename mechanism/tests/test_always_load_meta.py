"""Pin that every household-server tool declares ``_meta['anthropic/alwaysLoad']=True``.

The annotation is what tells Claude Code to always-load the tool's schema
into context instead of deferring it behind tool-search. The household
three MCP servers carry tools used every turn — memory, recall, fetch —
so all of them must stay always-loaded.

This test asserts against the wire-serialized shape (``model_dump`` with
``by_alias=True``) so the contract is what Claude Code actually reads,
not the Python attribute name on ``mcp.types.Tool``. Brittle by design:
if a new ``@mcp.tool`` is registered without the meta annotation, this
test fails on the next push with the offending tool name in the message.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastmcp import Client, FastMCP

from mechanism.cortex import mcp as cortex_mcp
from mechanism.mechanism import mcp as mechanism_mcp
from mechanism.utils import mcp as utils_mcp


@pytest.mark.parametrize(
    ("server", "server_name"),
    [
        (cortex_mcp, "cortex"),
        (mechanism_mcp, "mechanism"),
        (utils_mcp, "utils"),
    ],
)
async def test_all_household_tools_declare_always_load(
    server: FastMCP,
    server_name: str,
) -> None:
    """Every tool on each household server must set ``_meta['anthropic/alwaysLoad']=True``."""
    async with Client(server) as client:
        tools = await client.list_tools()

    assert tools, f"{server_name}: list_tools() returned no tools — server not loaded?"

    missing: list[str] = []
    for tool in tools:
        wire: dict[str, Any] = tool.model_dump(by_alias=True)
        meta: dict[str, Any] = wire.get("_meta") or {}
        if meta.get("anthropic/alwaysLoad") is not True:
            missing.append(f"{tool.name} (got meta={meta!r})")

    assert not missing, (
        f"{server_name}: tools missing _meta['anthropic/alwaysLoad']=True:\n"
        + "\n".join(f"  - {m}" for m in missing)
    )
