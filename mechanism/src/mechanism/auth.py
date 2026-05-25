"""Shared FastMCP token-verifier construction.

All three FastMCP servers (cortex, mechanism, utils) use the same bearer
token for tailnet-side access control. ``StaticTokenVerifier`` is the
FastMCP-native way to validate a fixed bearer token — adequate for our
single-user-per-deploy, tailnet-private deployment shape (per the FastMCP
docs, it should not be used in true production-grade deployments).

``MECHANISM_TOKEN`` is required — ``Settings`` has no default, so startup
fails loudly if it's unset rather than silently serving every tool
unauthenticated to anything on the tailnet.

``/livez`` (the `@custom_route` on the mechanism server) bypasses this
verifier by design — FastMCP's documented behavior, exactly what we want
for load-balancer and tailscale serve probes.
"""

from __future__ import annotations

from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

from mechanism.settings import get_settings


def get_auth_verifier() -> StaticTokenVerifier:
    """Return the StaticTokenVerifier for the configured token."""
    token = get_settings().mechanism_token
    return StaticTokenVerifier(tokens={token: {"client_id": "alpha"}})
