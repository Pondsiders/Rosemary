"""Pydantic models for the utils MCP tool inputs and outputs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class FetchResult(BaseModel):
    """The result of `fetch` — the extracted content and metadata about how we got it."""

    content: str = Field(description="The fetched content, as Markdown.")
    final_url: str = Field(
        description="The URL the content was actually retrieved from (after redirects)."
    )
    tier_used: Literal["accept-markdown", "url-variant", "trafilatura"] = Field(
        description=(
            "Which fetch tier produced the content. 'accept-markdown' = the server "
            "honored the Accept: text/markdown request. 'url-variant' = a sibling .md "
            "URL existed. 'trafilatura' = we fetched HTML and extracted markdown from it."
        )
    )
