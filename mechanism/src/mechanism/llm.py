"""Process-singleton LLM clients and embedding-input formatting.

Lazy module-level singletons mirror the shape of `db.py`'s pool: the first
call to a `get_*_client()` constructs the client from Settings; subsequent
calls return the same instance. Both hooks and MCP tools share the same
clients, no lifespan handoff required.

`format_query_for_embedding` lives here too because each embedding model
has its own input-shape convention; centralizing it makes the model
fungible (alongside re-embedding the corpus).
"""

from __future__ import annotations

from openai import AsyncOpenAI

from mechanism.settings import get_settings

_chat_client: AsyncOpenAI | None = None
_embedding_client: AsyncOpenAI | None = None


def get_chat_client() -> AsyncOpenAI:
    """Return the process-singleton chat client, creating it on first call."""
    global _chat_client
    if _chat_client is None:
        settings = get_settings()
        _chat_client = AsyncOpenAI(
            base_url=str(settings.chat_base_url),
            api_key=settings.chat_api_key,
        )
    return _chat_client


def get_chat_model() -> str:
    """Return the configured chat model name."""
    return get_settings().chat_model


def get_embedding_client() -> AsyncOpenAI:
    """Return the process-singleton embedding client, creating it on first call."""
    global _embedding_client
    if _embedding_client is None:
        settings = get_settings()
        _embedding_client = AsyncOpenAI(
            base_url=str(settings.embedding_base_url),
            api_key=settings.embedding_api_key,
        )
    return _embedding_client


def get_embedding_model() -> str:
    """Return the configured embedding model name."""
    return get_settings().embedding_model


async def close_llm_clients() -> None:
    """Close the singleton chat and embedding clients if they're open.

    Called from the app lifespan. Closes the underlying httpx clients
    held by AsyncOpenAI so warm reloads and test boundaries don't leak
    connections to the Bifrost gateway.
    """
    global _chat_client, _embedding_client
    if _chat_client is not None:
        await _chat_client.close()
        _chat_client = None
    if _embedding_client is not None:
        await _embedding_client.close()
        _embedding_client = None


def format_query_for_embedding(query: str) -> str:
    """Format a query string for nomic-embed-text's input.

    nomic-embed-text v1.5 uses *asymmetric* search prefixes: queries get
    `search_query:` and documents get `search_document:` (see
    `format_document_for_embedding`). The prefix is applied client-side,
    matching how the stored corpus was embedded, so query and document
    vectors share the same space.

    If we swap embedding models, this and `format_document_for_embedding`
    MUST be revisited together (and the corpus re-embedded with the new
    model). The output here is wrong for any other embedding model.

    Args:
        query: The raw user query string.

    Returns:
        The query reshaped for nomic-embed-text's input.
    """
    return f"search_query: {query}"


def format_document_for_embedding(content: str) -> str:
    """Format a document/memory string for nomic-embed-text's input.

    The asymmetric counterpart to `format_query_for_embedding`: stored
    content is prefixed with `search_document:`. Memories embedded for
    storage must use this so they land in the same vector space the
    queries search against.

    Args:
        content: The raw memory/document text.

    Returns:
        The content reshaped for nomic-embed-text's input.
    """
    return f"search_document: {content}"
