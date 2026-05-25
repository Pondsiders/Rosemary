"""Integration tests for the `reflection` MCP tool.

Pins the contract without coupling to the cadence value:

1. Within a sample window generous enough for any realistic cadence
   period (10 turns easily covers any "every Nth" gate for N ≤ 9), the
   tool fires at least once for a fresh session, and when it does, the
   shape is ``{"decision": "block", "reason": "...Between turns..."}``.
2. ``stop_hook_active=True`` is always a no-op — the recursion guard
   short-circuits before the gate is evaluated, so this property is
   independent of cadence.

Tuning the gate (e.g. switching from "every 3rd starting at turn 1" to
"every 5th starting at turn 5") does not break these tests as long as
the cadence period stays below ``_SAMPLE_WINDOW``. If the period ever
needs to exceed that, raise ``_SAMPLE_WINDOW`` in lockstep with the
gate; no other test logic changes.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastmcp import Client

from mechanism.mechanism import mcp

_SAMPLE_WINDOW = 10
"""How many turns to sample. Must exceed the gate's cadence period."""


async def test_reflection_fires_within_sample_window() -> None:
    """At least one of the first `_SAMPLE_WINDOW` turns fires with the documented shape."""
    session_id = str(uuid.uuid4())

    fires: list[dict[str, Any]] = []
    async with Client(mcp) as client:
        for _ in range(_SAMPLE_WINDOW):
            result = await client.call_tool(
                "reflection",
                {"session_id": session_id, "stop_hook_active": False},
            )
            # Fire: tool returned a dict (unwrapped form on .data).
            # No-fire: tool returned None.
            if result.data is not None:
                fires.append(result.data)

    assert fires, (
        f"reflection should fire at least once within {_SAMPLE_WINDOW} turns "
        f"for any realistic cadence period; got zero fires"
    )

    # The fire shape is the load-bearing contract; pin it against a
    # representative fire (the first one).
    sample = fires[0]
    assert sample["decision"] == "block"
    assert "Between turns" in sample["reason"]


async def test_reflection_no_op_when_stop_hook_active() -> None:
    """stop_hook_active=True is always a no-op; recursion guard is cadence-independent."""
    session_id = str(uuid.uuid4())

    async with Client(mcp) as client:
        result = await client.call_tool(
            "reflection",
            {"session_id": session_id, "stop_hook_active": True},
        )

    assert result.data is None
