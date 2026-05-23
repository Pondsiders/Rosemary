"""Pytest fixtures shared by all test modules."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest

from mechanism import db


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
