"""Integration tests for the `anamneses` MCP tool.

Two contracts pinned:

1. **Match path** — when the recall pipeline surfaces at least one memory,
   ``anamneses`` returns the Claude Code UserPromptSubmit hook envelope
   verbatim::

       {
         "hookSpecificOutput": {
           "hookEventName": "UserPromptSubmit",
           "additionalContext": "<string>"
         }
       }

   The envelope must be unwrapped (no ``{"result": ...}`` outer key) so
   Claude Code's hook parser reads the canonical shape per
   code.claude.com/docs/en/hooks#userpromptsubmit.

2. **No-op path** — when chat extracts no queries (the common case), the
   tool returns a true empty MCP response: ``content == []`` and
   ``structured_content is None``. Load-bearing contract for the fix
   tracked at Pondsiders/Alpha#24: anything else (even
   ``{"result": null}``, which is what ``dict | None`` returns produce
   via FastMCP's primitive wrapping) triggers Claude Code's fallback
   "hook success: completed" status-string injection.

The match test stubs chat + embedding wire via ``mock_llm``; zero-vector
cosine against seeded data yields NaN scores that don't trip the
``_MIN_COSINE=0.1`` filter (``nan < 0.1`` is False in Python), so seeded
rows pass through and the envelope carries ``## Memory #...`` formatted
blocks. The no-op test stubs chat to return ``"[]"``, short-circuiting
before any embedding work.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastmcp import Client
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice

from mechanism.mechanism import mcp


async def test_anamneses_match_returns_user_prompt_submit_envelope(
    seeded: None,  # pyright: ignore[reportUnusedParameter]
    mock_llm: dict[str, list[dict[str, Any]]],
) -> None:
    """anamneses() returns a UserPromptSubmit hook envelope with formatted memory blocks."""
    session_id = str(uuid.uuid4())

    async with Client(mcp) as client:
        result = await client.call_tool(
            "anamneses",
            {"prompt": "do you remember the cat café?", "session_id": session_id},
        )

    assert result.is_error is False
    # One chat call (query extraction) followed by one batched embedding call.
    assert len(mock_llm["chat_calls"]) == 1
    assert len(mock_llm["embed_calls"]) == 1

    # The hook envelope contract per code.claude.com/docs/en/hooks#userpromptsubmit:
    # {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "..."}}
    envelope: dict[str, Any] = result.data
    hook_output = envelope["hookSpecificOutput"]
    assert hook_output["hookEventName"] == "UserPromptSubmit"
    additional_context = hook_output["additionalContext"]
    assert isinstance(additional_context, str)
    assert additional_context.startswith("## Memory #")


async def test_anamneses_no_match_returns_empty_mcp_response(
    seeded: None,  # pyright: ignore[reportUnusedParameter]
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """anamneses() returns content=[] and structured_content=None when chat extracts no queries."""
    from mechanism import llm

    async def empty_chat(**_kwargs: Any) -> ChatCompletion:
        return ChatCompletion(
            id="fake-chatcmpl",
            object="chat.completion",
            created=0,
            model="fake-chat-model",
            choices=[
                Choice(
                    index=0,
                    finish_reason="stop",
                    message=ChatCompletionMessage(role="assistant", content="[]"),
                )
            ],
        )

    monkeypatch.setattr(llm.get_chat_client().chat.completions, "create", empty_chat)

    async with Client(mcp) as client:
        result = await client.call_tool(
            "anamneses",
            {"prompt": "no recall cues here", "session_id": str(uuid.uuid4())},
        )

    assert result.is_error is False
    # The load-bearing contract for #24: truly empty MCP response. No content
    # blocks, no structured payload. Anything else (notably {"result": null})
    # triggers Claude Code's fallback "hook success: completed" injection.
    assert result.content == []
    assert result.structured_content is None
