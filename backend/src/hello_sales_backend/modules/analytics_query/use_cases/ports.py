"""Ports and internal models for analytics-query use cases."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from hello_sales_backend.shared.errors import AppError


@dataclass(frozen=True, slots=True)
class AnalyticsCatalogColumn:
    """One approved column in a semantic analytics relation."""

    name: str
    data_type: str
    description: str | None
    semantic_type: str
    sensitivity: str


@dataclass(frozen=True, slots=True)
class AnalyticsCatalogRelation:
    """One approved analytics relation."""

    name: str
    description: str
    columns: dict[str, AnalyticsCatalogColumn]


@dataclass(frozen=True, slots=True)
class AnalyticsCatalog:
    """Loaded semantic analytics catalog."""

    catalog_id: str
    catalog_version: str
    dialect: str
    description: str
    relations: dict[str, AnalyticsCatalogRelation]


@dataclass(frozen=True, slots=True)
class QueryProjection:
    """Resolved output projection metadata."""

    output_name: str
    data_type: str
    semantic_type: str
    description: str | None
    sensitivity: str
    source_columns: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ValidatedAnalyticsQuery:
    """Governed query after AST validation."""

    catalog_id: str
    catalog_version: str
    dialect: str
    normalized_sql: str
    query_fingerprint: str
    relations: tuple[str, ...]
    projections: tuple[QueryProjection, ...]
    risk_flags: tuple[str, ...]
    max_rows: int


@dataclass(frozen=True, slots=True)
class ExecutedAnalyticsQuery:
    """Raw bounded query execution result."""

    columns: tuple[str, ...]
    rows: tuple[Mapping[str, object | None], ...]
    truncated: bool


class AnalyticsCatalogPort(Protocol):
    """Load one catalog by identifier."""

    def get_catalog(self, catalog_id: str) -> AnalyticsCatalog: ...


class AnalyticsQueryValidatorPort(Protocol):
    """Validate one SQL statement against a semantic catalog."""

    def validate(
        self,
        *,
        catalog: AnalyticsCatalog,
        sql: str,
        max_rows: int,
    ) -> ValidatedAnalyticsQuery: ...


class AnalyticsQueryExecutorPort(Protocol):
    """Execute one validated analytics query with bounded runtime constraints."""

    async def execute(
        self,
        *,
        catalog: AnalyticsCatalog,
        query: ValidatedAnalyticsQuery,
    ) -> ExecutedAnalyticsQuery: ...


class AnalyticsResultRedactorPort(Protocol):
    """Shape and redact query results safely."""

    def redact(
        self,
        *,
        catalog: AnalyticsCatalog,
        query: ValidatedAnalyticsQuery,
        execution: ExecutedAnalyticsQuery,
        execution_time_ms: int,
    ) -> tuple[Sequence[object], Sequence[dict[str, object | None]]]: ...


class AnalyticsQueryDiagnosticsPort(Protocol):
    """Emit analytics query success and failure metadata."""

    async def query_succeeded(
        self,
        *,
        request_id: str | None,
        trace_id: str | None,
        catalog: AnalyticsCatalog,
        query: ValidatedAnalyticsQuery,
        truncated: bool,
        row_count: int,
        execution_time_ms: int,
    ) -> None: ...

    async def query_failed(
        self,
        *,
        request_id: str | None,
        trace_id: str | None,
        catalog_id: str,
        sql: str,
        error: AppError,
    ) -> None: ...
