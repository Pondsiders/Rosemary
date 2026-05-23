"""Integration test for `POST /hooks/memories`.

End-to-end through the recall pipeline with the LLM clients mocked at their
`.create()` methods:

    prompt -> chat extracts queries -> embed each query -> search cortex
           -> filter seen -> mark seen -> format additionalContext

This test exercises the full chain against an empty cortex.memories so the
hook returns its documented no-op shape (200 with empty body). The brittle
assertions pin: the no-op contract, that the user prompt traveled into the
chat call unchanged, that each extracted query got embedded with the Qwen
`Instruct:` prefix wrapping (verifying `format_query_for_embedding` ran).

A future seed-aware test will assert on actual recall content; this test
pins the *plumbing*.
"""

from __future__ import annotations

import uuid
from typing import Any

from httpx import AsyncClient


async def test_memories_hook_chains_chat_embed_search(
    hooks_client: AsyncClient,
    mock_llm: dict[str, list[dict[str, Any]]],
) -> None:
    """Memories hook drives chat → embed → search end-to-end; empty DB → no-op response."""
    session_id = str(uuid.uuid4())
    prompt = "do you remember the cat café?"

    resp = await hooks_client.post(
        "/hooks/memories",
        json={"session_id": session_id, "prompt": prompt},
    )

    # Empty cortex.memories → empty additionalContext → documented no-op:
    # 200 with empty body (per the hook's `Response(status_code=200)` path).
    assert resp.status_code == 200
    assert resp.content == b""

    # Chat was called exactly once with our prompt as the final user message.
    assert len(mock_llm["chat_calls"]) == 1
    messages = mock_llm["chat_calls"][0]["messages"]
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == prompt

    # Embed was called exactly once with the two queries from the canned
    # chat response, each wrapped by format_query_for_embedding.
    assert len(mock_llm["embed_calls"]) == 1
    embed_input = mock_llm["embed_calls"][0]["input"]
    assert isinstance(embed_input, list)
    assert len(embed_input) == 2  # pyright: ignore[reportUnknownArgumentType]
    assert "Instruct:" in embed_input[0]
    assert "Query:test query alpha" in embed_input[0]
    assert "Query:test query beta" in embed_input[1]
