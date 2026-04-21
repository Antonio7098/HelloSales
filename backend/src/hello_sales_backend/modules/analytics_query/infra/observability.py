"""Observability adapter for governed analytics queries."""

from __future__ import annotations

from hello_sales_backend.modules.analytics_query.use_cases.ports import (
    AnalyticsCatalog,
    ValidatedAnalyticsQuery,
)
from hello_sales_backend.platform.observability.events import OperationalEvent
from hello_sales_backend.platform.observability.runtime import ObservabilityRuntime
from hello_sales_backend.shared.errors import AppError


class AnalyticsQueryObservabilityAdapter:
    """Emit stable operational metadata for analytics query execution."""

    def __init__(self, *, observability: ObservabilityRuntime) -> None:
        self._observability = observability

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
    ) -> None:
        await self._observability.emit(
            OperationalEvent(
                event_type="analytics_query.executed",
                severity="info",
                component="analytics_query",
                operation="analytics_query.service.query_data",
                correlation_id=request_id,
                trace_id=trace_id,
                code="analytics_query.executed",
                payload={
                    "catalog_id": catalog.catalog_id,
                    "catalog_version": catalog.catalog_version,
                    "dialect": catalog.dialect,
                    "query_fingerprint": query.query_fingerprint,
                    "relations": list(query.relations),
                    "risk_flags": list(query.risk_flags),
                    "requested_max_rows": query.max_rows,
                    "row_count": row_count,
                    "truncated": truncated,
                    "execution_time_ms": execution_time_ms,
                },
            )
        )

    async def query_failed(
        self,
        *,
        request_id: str | None,
        trace_id: str | None,
        catalog_id: str,
        sql: str,
        error: AppError,
    ) -> None:
        await self._observability.emit(
            OperationalEvent(
                event_type="analytics_query.failed",
                severity=error.severity,
                component="analytics_query",
                operation="analytics_query.service.query_data",
                correlation_id=request_id,
                trace_id=trace_id,
                code=error.code,
                payload={
                    "catalog_id": catalog_id,
                    "sql_present": bool(sql.strip()),
                    "error": error.to_dict(),
                },
            )
        )
