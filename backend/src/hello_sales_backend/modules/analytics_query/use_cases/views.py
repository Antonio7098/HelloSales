"""Views for governed analytics queries."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AnalyticsQueryColumnView(BaseModel):
    """One returned analytics column."""

    model_config = ConfigDict(extra="forbid")

    name: str
    data_type: str
    semantic_type: str
    sensitivity: str
    redacted: bool = False
    description: str | None = None


class AnalyticsQueryResultView(BaseModel):
    """Bounded agent-facing analytics query result."""

    model_config = ConfigDict(extra="forbid")

    catalog_id: str
    catalog_version: str
    dialect: str
    query_fingerprint: str
    relations: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    requested_max_rows: int
    row_count: int
    truncated: bool = False
    execution_time_ms: int
    columns: list[AnalyticsQueryColumnView] = Field(default_factory=list)
    rows: list[dict[str, object | None]] = Field(default_factory=list)
