"""The `read_from_diary` tool — return yesterday's and today's diary entries."""

from __future__ import annotations

from mcp.types import ToolAnnotations

from mechanism import clock
from mechanism.cortex.models import DiaryEntry
from mechanism.cortex.server import mcp
from mechanism.db import get_pool


@mcp.tool(
    description="Return the last two diary pages.",
    annotations=ToolAnnotations(
        title="Read from diary",
        readOnlyHint=True,
        openWorldHint=False,
    ),
    meta={
        "anthropic/maxResultSizeChars": 400000,
        "anthropic/alwaysLoad": True,
    },
)
async def read_from_diary() -> list[DiaryEntry]:
    """Return entries from the last two diary pages, anchored to the latest entry.

    Always returns *something* if cortex.diary has any entries at all; returns
    [] only when the table is empty.

    Returns:
        Diary entries in the window, ordered by ascending created_at.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        last_entry = await conn.fetchval(
            "SELECT created_at FROM cortex.diary ORDER BY created_at DESC LIMIT 1"
        )
        if last_entry is None:
            return []
        since = clock.start_of_day(last_entry).subtract(days=1)
        sql = "SELECT id, content, created_at FROM cortex.diary WHERE created_at >= $1 ORDER BY created_at ASC"  # noqa: E501
        rows = await conn.fetch(sql, since)
    return [
        DiaryEntry(
            id=row["id"],
            content=row["content"],
            created_at=clock.pso8601(row["created_at"]),
            age=clock.age(row["created_at"]),
        )
        for row in rows
    ]
