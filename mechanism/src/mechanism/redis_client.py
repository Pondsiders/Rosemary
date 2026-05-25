"""Process-singleton async Redis client.

The mechanism MCP tools need Redis for per-session state:

- ``last-msg:<session_id>`` — timestamp tool's previous-message timestamp
- ``seen:<session_id>`` — memories tool's recall-dedupe set
- ``reflection:turn:<session_id>`` — reflection tool's turn counter

MCP-tool handlers don't have request scope, so the client is a lazy
process-singleton — same pattern as ``db.py`` and ``llm.py``. Closed
explicitly on app shutdown via ``close_redis_client()`` in the lifespan
teardown.
"""

from __future__ import annotations

import redis.asyncio as redis

from mechanism.settings import get_settings

_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    """Return the process-singleton async Redis client, opening on first call."""
    global _client
    if _client is None:
        _client = redis.from_url(str(get_settings().redis_url), decode_responses=True)
    return _client


async def close_redis_client() -> None:
    """Close the singleton Redis client if it's open. Called from the app lifespan."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
