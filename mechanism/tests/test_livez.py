"""Integration test for `GET /livez`.

Process-up health check. Trivially true if FastAPI is responding. Used by
the Docker healthcheck and as a smoke test that the test stack itself is
wired correctly — if this fails, every other test will too.
"""

from __future__ import annotations

from httpx import AsyncClient


async def test_livez_returns_status_ok(hooks_client: AsyncClient) -> None:
    """GET /livez returns 200 with the documented {"status": "ok"} body."""
    resp = await hooks_client.get("/livez")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
