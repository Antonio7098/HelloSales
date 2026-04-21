"""Commands for analytics-query operations."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class QueryAnalyticsDataCommand(BaseModel):
    """Request to execute one governed analytics query."""

    model_config = ConfigDict(extra="forbid")

    catalog_id: str = Field(min_length=1)
    sql: str = Field(min_length=1)
    reason: str = Field(min_length=3)
    max_rows: int | None = Field(default=None, ge=1, le=200)
