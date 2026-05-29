"""The `recall` tool — Sage-archive recall on UserPromptSubmit.

Decomposes the user's prompt into semantic-search queries, runs a hybrid
(full-text + cosine) search against `sage.messages` with speaker-based
penalties, filters messages already seen this session, and returns the
survivors as ``additionalContext`` formatted as archive-hit blocks.
Returns None when recall produces nothing.

The hybrid score reproduces the old Rosemary-SDK behavior:
``0.3 * LEAST(fts, 1.0) + 0.7 * cosine - speaker_penalty``. Kylee's own
words carry a smaller penalty (0.15) than Sage's responses (0.25): her
words are worth more as context than Sage's generic assistant output.

Only searchable, embedded rows can surface (``embedding IS NOT NULL``).
That gate excludes the archive's `tool`-speaker rows by construction —
they are stored ``searchable = false`` with null embedding and tsvector.

Uses its own ``seen-sage:<session_id>`` Redis key rather than the
``seen:<session_id>`` key shared by `memories`/`anamneses`: those query
`cortex.memories`, this queries `sage.messages` — different ID spaces that
would collide on a shared set.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, cast

import logfire
import numpy as np
from fastmcp.tools.base import ToolResult
from mcp.types import TextContent, ToolAnnotations

from mechanism import clock, llm
from mechanism.db import get_pool
from mechanism.prompts import get_prompt
from mechanism.redis_client import get_redis_client
from mechanism.sage.server import mcp

_SYSTEM_PROMPT = get_prompt("sage/recall_system")

_TOP_K_PER_QUERY = 1
_MIN_SCORE = 0.1
_KYLEE_PENALTY = 0.15
_SAGE_PENALTY = 0.25
_SEEN_TTL_SECONDS = 7 * 24 * 60 * 60  # one week
_MAX_CONTENT_CHARS = 500  # archive messages can be long; cap each hit.
_MAX_OUTPUT_CHARS = 9990  # Claude Code caps additionalContext at 10K; leave headroom.

_SEARCH_SQL = """
SELECT m.id,
       m.speaker,
       m.content,
       m.created_at,
       c.title AS conversation_title,
       0.3 * LEAST(ts_rank(m.content_tsv, plainto_tsquery('english', $2)), 1.0)
         + 0.7 * (1 - (m.embedding <=> $1))
         - CASE WHEN m.speaker = 'kylee' THEN $3::float8 ELSE $4::float8 END AS score
  FROM sage.messages m
  JOIN sage.conversations c ON c.id = m.conversation_id
 WHERE m.embedding IS NOT NULL
   AND NOT (m.id = ANY($5::int[]))
 ORDER BY score DESC
 LIMIT $6
"""


@mcp.tool(
    description=(
        "Run hybrid recall against the Sage archive (sage.messages) for a "
        "UserPromptSubmit hook. Returns matched archive passages as "
        "additionalContext, or no-op when nothing relevant is found."
    ),
    annotations=ToolAnnotations(
        title="Sage Recall",
        readOnlyHint=False,  # writes the seen-set to Redis
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=False,
    ),
)
async def recall(prompt: str, session_id: str) -> ToolResult | None:
    """Run the recall pipeline; return matched archive hits as additionalContext."""
    with logfire.span("sage.recall {session_id}", session_id=session_id):
        if prompt.startswith("/"):
            return None
        additional_context = await _run(prompt, session_id)
    if not additional_context:
        return None
    envelope = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": additional_context,
        }
    }
    return ToolResult(
        content=[TextContent(type="text", text=json.dumps(envelope))],
        structured_content=envelope,
    )


async def _run(prompt: str, session_id: str) -> str:
    """Run the recall pipeline. Returns the additionalContext string."""
    chat_client = llm.get_chat_client()
    embedding_client = llm.get_embedding_client()
    redis_client = get_redis_client()

    # 1. Ask the chat model to decompose the prompt into semantic-search queries.
    with logfire.span("sage.recall.extract_queries"):
        chat_response = await chat_client.chat.completions.create(
            model=llm.get_chat_model(),
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            top_p=0.8,
            presence_penalty=1.5,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "queries",
                    "strict": True,
                    "schema": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
            extra_body={
                "top_k": 20,
                "min_p": 0.0,
                "repetition_penalty": 1.0,
            },
            timeout=15.0,
        )

        raw = chat_response.choices[0].message.content or "[]"
        parsed: list[Any] = json.loads(raw)
        queries = [q for q in parsed if isinstance(q, str) and q.strip()]
    if not queries:
        return ""

    # 2. Embed all queries in one batched request.
    with logfire.span("sage.recall.embed_queries", count=len(queries)):
        embedding_response = await embedding_client.embeddings.create(
            model=llm.get_embedding_model(),
            input=[llm.format_query_for_embedding(q) for q in queries],
            timeout=15.0,
        )
        embeddings = [np.asarray(d.embedding, dtype=np.float32) for d in embedding_response.data]

    # 3. Pull the seen-set for this session from Redis (own key — sage.messages
    # is a different ID space from cortex.memories).
    seen_key = f"seen-sage:{session_id}"
    seen_members = cast(
        "set[str]",
        await cast("Any", redis_client.smembers(seen_key)),  # pyright: ignore[reportUnknownMemberType]
    )
    exclude = [int(m) for m in seen_members]

    # 4. Fan out hybrid searches over the asyncpg pool.
    pool = await get_pool()

    async def search(emb: np.ndarray, query: str) -> tuple[str, list[Any]]:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                _SEARCH_SQL,
                emb,
                query,
                _KYLEE_PENALTY,
                _SAGE_PENALTY,
                exclude,
                _TOP_K_PER_QUERY,
            )
        return query, cast("list[Any]", rows)

    with logfire.span("sage.recall.search_db", queries=len(queries)):
        per_query_results = await asyncio.gather(
            *(search(emb, q) for emb, q in zip(embeddings, queries, strict=True))
        )

    # 5. Merge, dedupe by id (keeping earliest-query match), filter low-score,
    # then sort by query index.
    by_id: dict[int, dict[str, Any]] = {}
    for q_idx, (query, rows) in enumerate(per_query_results):
        for row in rows:
            score = float(row["score"])
            if score < _MIN_SCORE:
                continue
            msg_id = int(row["id"])
            existing = by_id.get(msg_id)
            if existing is None or q_idx < existing["q_idx"]:
                by_id[msg_id] = {
                    "id": msg_id,
                    "speaker": row["speaker"],
                    "content": row["content"],
                    "created_at": row["created_at"],
                    "conversation_title": row["conversation_title"],
                    "score": score,
                    "query": query,
                    "q_idx": q_idx,
                }
    merged = sorted(by_id.values(), key=lambda m: m["q_idx"])
    if not merged:
        return ""

    # 6. Mark these IDs seen for this session (with TTL refresh).
    async with redis_client.pipeline(transaction=False) as pipe:
        _ = pipe.sadd(seen_key, *(str(m["id"]) for m in merged))
        _ = pipe.expire(seen_key, _SEEN_TTL_SECONDS)
        _ = await pipe.execute()

    # 7. Format as archive-hit blocks.
    blocks: list[str] = []
    total = 0
    for m in merged:
        block = _format_hit(m)
        sep_len = 2 if blocks else 0  # "\n\n" between blocks
        if total + len(block) + sep_len > _MAX_OUTPUT_CHARS:
            if not blocks:
                logfire.error(
                    "sage.recall.truncated.hard_slice",
                    queries=queries,
                    message_id=m["id"],
                    query=m["query"],
                    q_idx=m["q_idx"],
                    score=round(m["score"], 3),
                    block_chars=len(block),
                    max_chars=_MAX_OUTPUT_CHARS,
                )
                return block[:_MAX_OUTPUT_CHARS]
            logfire.error(
                "sage.recall.truncated.dropped",
                queries=queries,
                kept=[
                    {
                        "id": x["id"],
                        "q_idx": x["q_idx"],
                        "query": x["query"],
                        "score": round(x["score"], 3),
                    }
                    for x in merged[: len(blocks)]
                ],
                dropped=[
                    {
                        "id": x["id"],
                        "q_idx": x["q_idx"],
                        "query": x["query"],
                        "score": round(x["score"], 3),
                    }
                    for x in merged[len(blocks) :]
                ],
                chars_used=total,
                max_chars=_MAX_OUTPUT_CHARS,
            )
            break
        blocks.append(block)
        total += len(block) + sep_len
    return "\n\n".join(blocks)


def _format_hit(m: dict[str, Any]) -> str:
    """Format one archive hit as a Markdown block."""
    speaker = "Kylee" if m["speaker"] == "kylee" else "Sage"
    content = m["content"]
    if len(content) > _MAX_CONTENT_CHARS:
        content = content[:_MAX_CONTENT_CHARS].rstrip() + "…"
    lines = [
        f"## From the Sage archive — {speaker} said",
        "",
        f"- {clock.pso8601(m['created_at'])}",
        f"- {clock.age(m['created_at'])}",
        f"- from: {m['conversation_title']!r}",
        f"- query: {m['query']!r}",
        f"- score: {m['score']:.2f}",
        "",
        content,
    ]
    return "\n".join(lines)
