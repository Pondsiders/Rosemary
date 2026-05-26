"""Integration tests for the `reflection` MCP tool.

Pins the wire shape for three paths:

- Fire: ``content`` is a single ``TextContent`` with the Stop-hook
  decision payload as JSON text; ``structured_content`` is None.
- Cadence no-op: ``content=[]``, ``structured_content=None``.
- ``stop_hook_active=True``: same empty-response shape as the cadence
  no-op.

Tuning the cadence doesn't break these tests as long as the period
stays below ``_SAMPLE_WINDOW``.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from fastmcp import Client
from mcp.types import TextContent

from mechanism.mechanism import mcp

_SAMPLE_WINDOW = 10
"""How many turns to sample. Must exceed the gate's cadence period."""


async def test_reflection_fires_within_sample_window() -> None:
    """At least one of the first `_SAMPLE_WINDOW` turns fires with the documented wire shape."""
    session_id = str(uuid.uuid4())

    fires: list[Any] = []
    async with Client(mcp) as client:
        for _ in range(_SAMPLE_WINDOW):
            result = await client.call_tool(
                "reflection",
                {"session_id": session_id, "stop_hook_active": False},
            )
            if result.content:
                fires.append(result)

    assert fires, (
        f"reflection should fire at least once within {_SAMPLE_WINDOW} turns "
        f"for any realistic cadence period; got zero fires"
    )

    sample = fires[0]
    assert sample.is_error is False
    assert sample.structured_content is None
    assert len(sample.content) == 1
    block = sample.content[0]
    assert isinstance(block, TextContent)
    assert block.type == "text"

    envelope = json.loads(block.text)
    assert envelope["decision"] == "block"
    assert "Between turns" in envelope["reason"]


async def test_reflection_no_op_within_cadence_window() -> None:
    """At least one of the first `_SAMPLE_WINDOW` turns is a no-op with an empty MCP response."""
    session_id = str(uuid.uuid4())

    no_ops: list[Any] = []
    async with Client(mcp) as client:
        for _ in range(_SAMPLE_WINDOW):
            result = await client.call_tool(
                "reflection",
                {"session_id": session_id, "stop_hook_active": False},
            )
            if not result.content:
                no_ops.append(result)

    assert no_ops, (
        f"reflection should no-op at least once within {_SAMPLE_WINDOW} turns "
        f"for any realistic cadence period; got zero no-ops"
    )

    sample = no_ops[0]
    assert sample.is_error is False
    assert sample.content == []
    assert sample.structured_content is None


async def test_reflection_no_op_when_stop_hook_active() -> None:
    """stop_hook_active=True is always a no-op; recursion guard is cadence-independent."""
    session_id = str(uuid.uuid4())

    async with Client(mcp) as client:
        result = await client.call_tool(
            "reflection",
            {"session_id": session_id, "stop_hook_active": True},
        )

    assert result.is_error is False
    assert result.content == []
    assert result.structured_content is None
