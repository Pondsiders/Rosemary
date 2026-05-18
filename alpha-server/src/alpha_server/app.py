"""FastAPI application factory.

Run with:
    uv run uvicorn alpha_server.app:app --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI

from alpha_server.auth import BearerTokenMiddleware
from alpha_server.cortex import mcp

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

_cortex_app = mcp.http_app(path="/mcp")


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Compose the Cortex MCP lifespan into FastAPI's startup/shutdown.

    The MCP session manager needs to start before requests arrive at the
    mounted sub-app; without this hand-off, mounted tool calls hang.
    """
    async with _cortex_app.lifespan(app):
        yield


app = FastAPI(lifespan=_lifespan)
app.add_middleware(BearerTokenMiddleware)
app.mount("/cortex", _cortex_app)


@app.get("/livez")
async def livez() -> dict[str, str]:
    """Process-up health check. Trivially true if FastAPI is responding."""
    return {"status": "ok"}
