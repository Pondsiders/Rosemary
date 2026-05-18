"""Pydantic models for Cortex MCP tool inputs and outputs.

These are the wire shapes the MCP server returns to clients. FastMCP
auto-generates JSON Schema from these so the LLM sees properly-shaped
tool descriptions and the inspector renders structured output.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class DiaryEntry(BaseModel):
    """A single diary entry row from cortex.diary."""

    id: int = Field(description="Diary entry id.")
    content: str = Field(description="The diary entry text.")
    created_at: str = Field(description="When the entry was stored (PSO-8601, local time).")
    age: str = Field(description="How long ago the entry was stored.")
