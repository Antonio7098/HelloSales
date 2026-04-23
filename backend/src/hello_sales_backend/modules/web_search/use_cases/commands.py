"""Web-search use-case commands."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SearchWebCommand(BaseModel):
    """Validated command for one public web-search request."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=500)
    reason: str = Field(min_length=3, max_length=500)
    max_results: int | None = Field(default=None, ge=1, le=20)
    search_depth: str = Field(default="basic", pattern="^(basic|advanced)$")
    topic: str = Field(default="general", pattern="^(general|news)$")
    time_range: str | None = Field(default=None, pattern="^(day|week|month|year|d|w|m|y)$")
    include_domains: tuple[str, ...] = Field(default=(), max_length=10)
    exclude_domains: tuple[str, ...] = Field(default=(), max_length=10)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    include_raw_content: bool = False

    @field_validator("query", "reason", "search_depth", "topic", "time_range", "country", mode="before")
    @classmethod
    def strip_strings(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("include_domains", "exclude_domains", mode="before")
    @classmethod
    def normalize_domains(cls, value: object) -> object:
        if value is None:
            return ()
        if isinstance(value, str):
            return (value.strip(),)
        if isinstance(value, list | tuple):
            return tuple(str(item).strip().lower() for item in value if str(item).strip())
        return value
