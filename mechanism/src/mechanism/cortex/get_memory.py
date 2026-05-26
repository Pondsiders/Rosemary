"""The `get_memory` tool — fetch a single memory by id."""

from __future__ import annotations

from typing import Annotated

from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from mechanism import clock
from mechanism.cortex.models import Memory
from mechanism.cortex.server import mcp
from mechanism.db import get_pool

_SELECT = """
SELECT id, content, created_at
  FROM cortex.memories
 WHERE id = $1
   AND NOT forgotten
"""


@mcp.tool(
    description=(
        "Fetch a single memory by id. Use this when you see a memory id "
        "referenced (in recall results, diary entries, or conversation) "
        "and want to read the full memory."
    ),
    annotations=ToolAnnotations(
        title="Get memory",
        readOnlyHint=True,
        openWorldHint=False,
    ),
    meta={
        "anthropic/maxResultSizeChars": 400000,
        "anthropic/alwaysLoad": True,
    },
)
async def get_memory(
    memory_id: Annotated[
        int,
        Field(ge=1, description="The memory id to fetch."),
    ],
) -> Memory:
    """Fetch a single memory by id.

    Args:
        memory_id: The memory id.

    Returns:
        The memory.

    Raises:
        ToolError: If no memory exists with that id, or the memory has been
            forgotten.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(_SELECT, memory_id)
    if row is None:
        msg = f"no memory with id={memory_id}"
        raise ToolError(msg)

    return Memory(
        id=row["id"],
        content=row["content"],
        created_at=clock.pso8601(row["created_at"]),
        age=clock.age(row["created_at"]),
    )
