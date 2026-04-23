"""Provider-neutral public web-search contracts."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field, field_validator


class WebSearchCallContext(BaseModel):
    """Request-scoped metadata for one web-search invocation."""

    request_id: str | None = None
    trace_id: str | None = None
    actor_id: str | None = None
    operation: str | None = None
    timeout_seconds: float | None = Field(default=None, gt=0)


class WebSearchRequest(BaseModel):
    """Provider-neutral search request."""

    query: str = Field(min_length=1, max_length=500)
    reason: str = Field(min_length=3, max_length=500)
    max_results: int = Field(default=5, ge=1, le=20)
    search_depth: str = "basic"
    topic: str = "general"
    time_range: str | None = None
    include_domains: tuple[str, ...] = ()
    exclude_domains: tuple[str, ...] = ()
    country: str | None = None
    include_raw_content: bool = False

    @field_validator("query", "reason", "search_depth", "topic", "time_range", "country", mode="before")
    @classmethod
    def strip_optional_strings(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class WebSearchResult(BaseModel):
    """One normalized source result returned by a search provider."""

    title: str
    url: str
    snippet: str | None = None
    content: str | None = None
    published_at: str | None = None
    score: float | None = None
    source_provider: str
    provider_request_id: str | None = None
    raw_metadata: dict[str, object] = Field(default_factory=dict)


class WebSearchResponse(BaseModel):
    """Normalized search provider response."""

    provider: str
    query: str
    results: list[WebSearchResult]
    provider_request_id: str | None = None
    answer: str | None = None
    raw_metadata: dict[str, object] = Field(default_factory=dict)


class WebSearchProviderPort(Protocol):
    """Neutral async provider contract for public web search."""

    provider_name: str

    async def search(
        self,
        request: WebSearchRequest,
        *,
        context: WebSearchCallContext | None = None,
    ) -> WebSearchResponse: ...

    def is_configured(self) -> bool: ...
