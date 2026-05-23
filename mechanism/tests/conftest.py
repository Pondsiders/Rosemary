"""Pytest fixtures shared by all test modules."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
import redis.asyncio as redis
from httpx import ASGITransport, AsyncClient

from mechanism import db


def pytest_configure(config: pytest.Config) -> None:  # pyright: ignore[reportUnusedParameter]
    """Refuse to run unless the test environment is explicitly configured.

    Loud safety net against the failure mode that produced #10: pytest
    reaching for a `DATABASE_URL` that happens to be set to production.
    Production code only ever reads `DATABASE_URL` / `REDIS_URL`; this hook
    rewrites them from the `TEST_*` values at session start, so
    `get_settings()` (lru_cached) picks up the test values on first call.

    The TEST_* vars must be set AND must differ from the production URLs.
    A missing or matching value causes pytest to exit immediately.
    """
    test_db = os.environ.get("TEST_DATABASE_URL")
    test_redis = os.environ.get("TEST_REDIS_URL")
    if not test_db or not test_redis:
        pytest.exit(
            "TEST_DATABASE_URL and TEST_REDIS_URL are required for the test"
            + " suite. Run `just test-up` and set both vars (see the `test`"
            + " recipe in the justfile for the canonical values).",
            returncode=2,
        )
    if test_db == os.environ.get("DATABASE_URL"):
        pytest.exit(
            "TEST_DATABASE_URL equals DATABASE_URL."
            + " Refusing to run tests against the production database.",
            returncode=2,
        )
    if test_redis == os.environ.get("REDIS_URL"):
        pytest.exit(
            "TEST_REDIS_URL equals REDIS_URL."
            + " Refusing to run tests against the production Redis.",
            returncode=2,
        )
    os.environ["DATABASE_URL"] = test_db
    os.environ["REDIS_URL"] = test_redis


@pytest.fixture(autouse=True)
async def _reset_pool_between_tests() -> AsyncGenerator[None]:  # pyright: ignore[reportUnusedFunction]
    """Close and reset `db._pool` between tests.

    asyncpg pools are bound to the event loop they were created in. Each
    pytest-asyncio test runs in a fresh event loop, so a singleton pool
    created in one test poisons subsequent tests with `cannot perform
    operation: another operation is in progress`. This fixture closes the
    pool after each test so the next test starts fresh.
    """
    yield
    if db._pool is not None:  # pyright: ignore[reportPrivateUsage]
        await db._pool.close()  # pyright: ignore[reportPrivateUsage]
        db._pool = None  # pyright: ignore[reportPrivateUsage]


@pytest.fixture
async def hooks_client() -> AsyncGenerator[AsyncClient]:
    """An httpx AsyncClient for the FastAPI app, with Redis wired in directly.

    Bypasses the full FastAPI lifespan (which handles production-only concerns
    like Logfire configuration and the mounted MCP sub-apps' startup); hook
    handlers only need `request.app.state.redis`, so we attach that and skip
    the rest. Lifespan is a production-only concern; tests inject what each
    handler actually requires.
    """
    from mechanism.app import app

    app.state.redis = redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client
    finally:
        await app.state.redis.aclose()
