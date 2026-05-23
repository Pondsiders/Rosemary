"""The `store_memory` tool — embed a memory and append it to cortex.memories."""

from __future__ import annotations

from typing import Annotated

import numpy as np
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from mechanism import clock, llm
from mechanism.cortex.models import StoreResult
from mechanism.cortex.server import mcp
from mechanism.db import get_pool

_INSERT_SQL = """
INSERT INTO cortex.memories (content, embedding_qwen, created_at)
VALUES ($1, $2, $3)
RETURNING id, created_at
"""


@mcp.tool(
    description=(
        "Store a memory: embed the content and append it to your memory store. "
        "Use this for moments — first-person, timestamped, textured — not for "
        "facts (Claude Code's auto-memory is for facts)."
    ),
    annotations=ToolAnnotations(
        title="Store memory",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=False,
    ),
)
async def store_memory(
    content: Annotated[
        str,
        Field(min_length=1, description="The memory text. Must be non-empty."),
    ],
) -> StoreResult:
    """Embed content and insert a new memory row.

    Args:
        content: The memory text. Non-empty; the embedding service is the
            authority on the upper size limit and will return an error if
            content is too long to embed.

    Returns:
        The new row's id and created_at.
    """
    response = await llm.get_embedding_client().embeddings.create(
        model=llm.get_embedding_model(),
        input=[content],
        timeout=15.0,
    )
    embedding = np.asarray(response.data[0].embedding, dtype=np.float32)

    pool = await get_pool()
    now = clock.now()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(_INSERT_SQL, content, embedding, now)
    if row is None:
        msg = "INSERT INTO cortex.memories did not RETURNING a row"
        raise ToolError(msg)

    return StoreResult(
        id=row["id"],
        created_at=clock.pso8601(row["created_at"]),
    )
