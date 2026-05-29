"""Integration tests for the `sage` archive-recall MCP tool.

Pins the wire shape (parity with the `memories` hook) and the novel
hybrid-search behavior:

- Match: ``structured_content`` is the UserPromptSubmit hook envelope; the
  ``additionalContext`` is formatted as ``## From the Sage archive —`` blocks.
- No-op: ``content=[]``, ``structured_content=None`` (no queries, or no rows).
- Slash command: short-circuits without touching the LLM.
- Speaker penalty: Kylee's words outrank Sage's at equal similarity.
- Tool exclusion: `tool`-speaker rows (searchable=false, null embedding)
  never surface, enforced by the ``embedding IS NOT NULL`` gate.

Seeds its own `sage.*` rows with controlled unit-vector embeddings, so
ranking is deterministic rather than riding the zero-vector path.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import pytest
from fastmcp import Client
from mcp.types import TextContent
from openai.types import CreateEmbeddingResponse, Embedding
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice

from mechanism.db import get_pool
from mechanism.sage import mcp

_DIMENSIONS = 768


def _unit_vector(dim: int = 0) -> list[float]:
    """A 768-dim one-hot vector — cosine similarity 1.0 with itself."""
    v = [0.0] * _DIMENSIONS
    v[dim] = 1.0
    return v


def _install_llm(monkeypatch: pytest.MonkeyPatch, queries: list[str]) -> None:
    """Monkeypatch chat to return `queries` and embed to return unit vector e0.

    Overrides the autouse blanket mock (last setattr wins). Every embedded
    query becomes e0, so a seeded message with embedding e0 scores cosine 1.0.
    """
    from mechanism import llm

    chat_client = llm.get_chat_client()
    embed_client = llm.get_embedding_client()

    async def fake_chat(**_kwargs: Any) -> ChatCompletion:
        return ChatCompletion(
            id="fake-chatcmpl",
            object="chat.completion",
            created=0,
            model="fake-chat-model",
            choices=[
                Choice(
                    index=0,
                    finish_reason="stop",
                    message=ChatCompletionMessage(role="assistant", content=json.dumps(queries)),
                )
            ],
        )

    async def fake_embed(**kwargs: Any) -> CreateEmbeddingResponse:
        raw_input = kwargs.get("input")
        n = len(raw_input) if isinstance(raw_input, list) else 1  # pyright: ignore[reportUnknownArgumentType]
        return CreateEmbeddingResponse(
            object="list",
            model="fake-embed-model",
            usage={"prompt_tokens": 0, "total_tokens": 0},  # pyright: ignore[reportArgumentType]
            data=[
                Embedding(index=i, object="embedding", embedding=_unit_vector()) for i in range(n)
            ],
        )

    monkeypatch.setattr(chat_client.chat.completions, "create", fake_chat)
    monkeypatch.setattr(embed_client.embeddings, "create", fake_embed)


async def _seed_conversation(title: str, openai_id: str) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "INSERT INTO sage.conversations (openai_id, title) VALUES ($1, $2) RETURNING id",
            openai_id,
            title,
        )


async def _seed_message(
    conversation_id: int,
    speaker: str,
    content: str,
    sequence: int,
    *,
    searchable: bool = True,
    embedding: list[float] | None,
) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(
            """
            INSERT INTO sage.messages
                (conversation_id, speaker, content, sequence, searchable, embedding, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, now())
            RETURNING id
            """,
            conversation_id,
            speaker,
            content,
            sequence,
            searchable,
            embedding,
        )


async def test_recall_match_returns_user_prompt_submit_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """recall() returns a UserPromptSubmit hook envelope on both wire surfaces."""
    _install_llm(monkeypatch, ["the trip to paris"])
    conv = await _seed_conversation("Paris trip", "conv-1")
    _ = await _seed_message(conv, "kylee", "we walked along the seine", 0, embedding=_unit_vector())

    async with Client(mcp) as client:
        result = await client.call_tool(
            "recall",
            {"prompt": "tell me about paris", "session_id": str(uuid.uuid4())},
        )

    assert result.is_error is False
    assert result.structured_content is not None
    structured: dict[str, Any] = result.structured_content
    hook_output = structured["hookSpecificOutput"]
    assert hook_output["hookEventName"] == "UserPromptSubmit"
    additional_context = hook_output["additionalContext"]
    assert isinstance(additional_context, str)
    assert additional_context.startswith("## From the Sage archive —")
    assert "Kylee said" in additional_context
    assert "from: 'Paris trip'" in additional_context

    assert len(result.content) == 1
    block = result.content[0]
    assert isinstance(block, TextContent)
    text_envelope = json.loads(block.text)
    assert text_envelope == structured


async def test_recall_no_match_returns_empty_mcp_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """recall() no-ops when the chat model extracts no queries."""
    _install_llm(monkeypatch, [])

    async with Client(mcp) as client:
        result = await client.call_tool(
            "recall",
            {"prompt": "no recall cues here", "session_id": str(uuid.uuid4())},
        )

    assert result.is_error is False
    assert result.content == []
    assert result.structured_content is None


async def test_recall_slash_command_short_circuits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """recall() no-ops without touching the LLM when the prompt starts with '/'."""
    calls: list[str] = []

    from mechanism import llm

    async def tripwire_chat(**_kwargs: Any) -> ChatCompletion:
        calls.append("chat")
        raise AssertionError("chat should not be called for a slash command")

    monkeypatch.setattr(llm.get_chat_client().chat.completions, "create", tripwire_chat)

    async with Client(mcp) as client:
        result = await client.call_tool(
            "recall",
            {"prompt": "/compact please", "session_id": str(uuid.uuid4())},
        )

    assert result.is_error is False
    assert result.content == []
    assert result.structured_content is None
    assert calls == []


async def test_recall_applies_speaker_penalty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """At equal cosine similarity, Kylee's words outrank Sage's (smaller penalty)."""
    # Query text shares no stems with the content, so FTS contributes 0 to both
    # rows and the ranking is decided purely by the speaker penalty.
    _install_llm(monkeypatch, ["quantum chromodynamics"])
    conv = await _seed_conversation("Paris trip", "conv-1")
    _ = await _seed_message(conv, "kylee", "we walked along the seine", 0, embedding=_unit_vector())
    _ = await _seed_message(
        conv, "sage", "the seine is lovely at dusk", 1, embedding=_unit_vector()
    )

    async with Client(mcp) as client:
        result = await client.call_tool(
            "recall",
            {"prompt": "anything", "session_id": str(uuid.uuid4())},
        )

    assert result.structured_content is not None
    additional_context = result.structured_content["hookSpecificOutput"]["additionalContext"]
    # Top-1-per-query: the single survivor is Kylee's message, not Sage's.
    assert "Kylee said" in additional_context
    assert "Sage said" not in additional_context


async def test_recall_excludes_tool_speaker_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`tool` rows (searchable=false, null embedding) never surface."""
    _install_llm(monkeypatch, ["anything at all"])
    conv = await _seed_conversation("Tool noise", "conv-1")
    _ = await _seed_message(
        conv,
        "tool",
        "<function_call>do_thing()</function_call>",
        0,
        searchable=False,
        embedding=None,
    )

    async with Client(mcp) as client:
        result = await client.call_tool(
            "recall",
            {"prompt": "do the thing", "session_id": str(uuid.uuid4())},
        )

    assert result.is_error is False
    assert result.content == []
    assert result.structured_content is None
