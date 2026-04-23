"""Web-search use-case views."""

from __future__ import annotations

from pydantic import BaseModel, Field


class WebSearchSourceView(BaseModel):
    """One normalized source returned to callers."""

    title: str
    url: str
    snippet: str | None = None
    content: str | None = None
    published_at: str | None = None
    score: float | None = None
    source_provider: str
    provider_request_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class WebSearchResultView(BaseModel):
    """Search service result view."""

    provider: str
    query: str
    sources: list[WebSearchSourceView]
    provider_request_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
