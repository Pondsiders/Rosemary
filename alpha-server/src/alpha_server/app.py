"""FastAPI application factory.

Run with:
    uv run uvicorn alpha_server.app:app --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import redis.asyncio as redis
from fastapi import FastAPI
from openai import AsyncOpenAI

from alpha_server.auth import BearerTokenMiddleware
from alpha_server.cortex import mcp
from alpha_server.hooks.memories import router as memories_router
from alpha_server.settings import get_settings

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

_cortex_app = mcp.http_app(path="/mcp")


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Open long-lived clients and compose the Cortex MCP lifespan.

    Born once at startup, lives for the process lifetime:
    - chat + embedding OpenAI-protocol clients (point at Bifrost gateway)
    - redis client (seen-cache for the memories hook)

    The MCP session manager also needs to start before requests arrive at
    the mounted sub-app; without this hand-off, mounted tool calls hang.
    """
    settings = get_settings()

    app.state.chat_client = AsyncOpenAI(
        base_url=str(settings.chat_base_url),
        api_key=settings.chat_api_key,
    )
    app.state.chat_model = settings.chat_model

    app.state.embedding_client = AsyncOpenAI(
        base_url=str(settings.embedding_base_url),
        api_key=settings.embedding_api_key,
    )
    app.state.embedding_model = settings.embedding_model

    app.state.redis = redis.from_url(str(settings.redis_url), decode_responses=True)

    try:
        async with _cortex_app.lifespan(app):
            yield
    finally:
        await app.state.redis.aclose()
        await app.state.chat_client.close()
        await app.state.embedding_client.close()


app = FastAPI(lifespan=_lifespan)
app.add_middleware(BearerTokenMiddleware)
app.mount("/cortex", _cortex_app)
app.include_router(memories_router, prefix="/hooks")


@app.get("/livez")
async def livez() -> dict[str, str]:
    """Process-up health check. Trivially true if FastAPI is responding."""
    return {"status": "ok"}
