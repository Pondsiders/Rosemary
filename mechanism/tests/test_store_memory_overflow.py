"""Integration test: what happens when content exceeds the embedding context?

This test sends a known-too-large memory through store_memory and asserts that
the failure surface is "tool error returned cleanly," not "tool crashes."

Preconditions for this test to do what it says:
  - The embedding service (Bifrost → Ember + fallbacks) cannot embed the input.
  - On May 19 2026 Ember's n_ctx was 2048 and the fallback (Jeffery's MacBook
    LM Studio) was OFF, so a 2786-token input bounced off both legs and Bifrost
    returned an HTTP error. If you re-run this test in a future where Ember's
    n_ctx has been raised, the test will fail because the embedding succeeded —
    that failure is informative, not broken.

The 2786-token reference content comes from the longest memory ever stored
in cortex.memories at the time of writing (memory #16554, the April 4 2026
chronicle). Reproducing it byte-for-byte here would be wasteful; we generate
a synthetic string of the same approximate token count instead.
"""

from __future__ import annotations

from fastmcp import Client
from mcp.types import TextContent

from mechanism.cortex import mcp

# ~3000 tokens of synthetic content. Qwen's tokenizer hits ~4 chars/token on
# English prose, so 12_000 characters comfortably exceeds n_ctx=2048.
_LONG_CONTENT = "[TEST OVERFLOW] " + ("The quick brown duck jumps over the lazy substrate. " * 240)


async def test_store_memory_overflow_returns_tool_error() -> None:
    """An input too large to embed should surface as an MCP tool error.

    We intentionally don't catch the embedding exception inside store_memory;
    FastMCP catches uncaught exceptions from tool handlers and converts them
    to a tool-result with isError=True and the exception class+message in
    the content text. That's what the consumer (me-in-Claude-Code) sees.
    """
    async with Client(mcp) as client:
        result = await client.call_tool(
            "store_memory", {"content": _LONG_CONTENT}, raise_on_error=False
        )

    assert result.is_error, (
        "Expected store_memory to surface a tool error for over-context content; "
        "instead it appeared to succeed. Has Ember's n_ctx been raised?"
    )
    assert result.content, "Tool error result had no content"
    # The error text from the embedding service should travel through verbatim.
    # We don't assert on its exact wording — Bifrost may rephrase — but we assert
    # that *some* signal about size or context is in the error message.
    text = " ".join(c.text for c in result.content if isinstance(c, TextContent)).lower()
    assert any(token in text for token in ("context", "token", "size", "length", "too large")), (
        f"Error text didn't mention size/context/tokens; got: {text!r}"
    )
