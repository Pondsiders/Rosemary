"""Integration test for `GET /mechanism/livez`.

Process-up health check. Trivially true if the mechanism FastMCP server is
responding. Used by the Docker healthcheck and as a smoke test that the
test stack itself is wired correctly — if this fails, every other test
will too.

`/mechanism/livez` is a `@mcp.custom_route` on the mechanism FastMCP server
(mounted under `/mechanism` in the Starlette parent). Custom routes bypass
FastMCP's auth middleware by design.
"""

from __future__ import annotations

from httpx import AsyncClient


async def test_livez_returns_status_ok(hooks_client: AsyncClient) -> None:
    """GET /mechanism/livez returns 200 with the documented {"status": "ok"} body."""
    resp = await hooks_client.get("/mechanism/livez")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
