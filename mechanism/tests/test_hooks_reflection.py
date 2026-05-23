"""Integration test for `POST /hooks/reflection`.

The reflection hook fires on every third turn of a session, starting at turn 1
(so: 1, 4, 7, 10, ...). Turn count is tracked in Redis under
`reflection:turn:<session_id>` and increments atomically per hit.

This test sends seven hits with the same session_id and asserts the cadence:
turns 1, 4, 7 fire (return `decision: block` with the reminder text), turns
2, 3, 5, 6 no-op (return an empty object so the turn ends normally).

The cadence is the contract: change `_gate()` in reflection.py and this test
screams. That's the point.
"""

from __future__ import annotations

import uuid

from httpx import AsyncClient


async def test_reflection_fires_on_turns_1_4_7(hooks_client: AsyncClient) -> None:
    """Seven hits, same session_id: fires on 1/4/7, no-ops on 2/3/5/6."""
    session_id = str(uuid.uuid4())  # Fresh per-test, so the Redis counter starts clean.

    results: list[dict[str, object]] = []
    for _ in range(7):
        resp = await hooks_client.post(
            "/hooks/reflection",
            json={"session_id": session_id, "stop_hook_active": False},
        )
        assert resp.status_code == 200
        results.append(resp.json())

    # Cadence assertion: which turns produced a non-empty body?
    fired_turns = [i + 1 for i, r in enumerate(results) if r != {}]
    assert fired_turns == [1, 4, 7], f"expected fires on [1, 4, 7], got {fired_turns}"

    # Envelope-shape assertion on each fire: Stop-hook block-with-reason.
    for fired_idx in (0, 3, 6):  # turns 1, 4, 7 (0-indexed)
        envelope = results[fired_idx]
        assert envelope["decision"] == "block"
