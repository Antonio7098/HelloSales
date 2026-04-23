"""Analytics-query orchestration service."""

from __future__ import annotations

from time import perf_counter

from hello_sales_backend.modules.analytics_query.use_cases.commands import (
    QueryAnalyticsDataCommand,
)
from hello_sales_backend.modules.analytics_query.use_cases.ports import (
    AnalyticsCatalogPort,
    AnalyticsQueryDiagnosticsPort,
    AnalyticsQueryExecutorPort,
    AnalyticsQueryValidatorPort,
    AnalyticsResultRedactorPort,
)
from hello_sales_backend.modules.analytics_query.use_cases.views import (
    AnalyticsQueryColumnView,
    AnalyticsQueryResultView,
)
from hello_sales_backend.shared.errors import AppError, internal_error


class AnalyticsQueryService:
    """Execute governed analytics queries through narrow replaceable seams."""

    def __init__(
        self,
        *,
        catalogs: AnalyticsCatalogPort,
        validator: AnalyticsQueryValidatorPort,
        executor: AnalyticsQueryExecutorPort,
        redactor: AnalyticsResultRedactorPort,
        diagnostics: AnalyticsQueryDiagnosticsPort,
    ) -> None:
        self._catalogs = catalogs
        self._validator = validator
        self._executor = executor
        self._redactor = redactor
        self._diagnostics = diagnostics

    async def query_data(
        self,
        *,
        request_id: str | None,
        trace_id: str | None,
        actor_id: str | None,
        command: QueryAnalyticsDataCommand,
    ) -> AnalyticsQueryResultView:
        del actor_id
        started = perf_counter()
        catalog = None
        try:
            catalog = self._catalogs.get_catalog(command.catalog_id)
            validated = self._validator.validate(
                catalog=catalog,
                sql=command.sql,
                max_rows=command.max_rows or 0,
            )
            execution = await self._executor.execute(catalog=catalog, query=validated)
            raw_columns, raw_rows = self._redactor.redact(
                catalog=catalog,
                query=validated,
                execution=execution,
                execution_time_ms=int((perf_counter() - started) * 1000),
            )
            result = AnalyticsQueryResultView(
                catalog_id=catalog.catalog_id,
                catalog_version=catalog.catalog_version,
                dialect=catalog.dialect,
                query_fingerprint=validated.query_fingerprint,
                relations=list(validated.relations),
                risk_flags=sorted(set(validated.risk_flags)),
                requested_max_rows=validated.max_rows,
                row_count=len(raw_rows),
                truncated=execution.truncated,
                execution_time_ms=int((perf_counter() - started) * 1000),
                columns=[AnalyticsQueryColumnView.model_validate(item) for item in raw_columns],
                rows=[dict(item) for item in raw_rows],
            )
            await self._diagnostics.query_succeeded(
                request_id=request_id,
                trace_id=trace_id,
                catalog=catalog,
                query=validated,
                truncated=execution.truncated,
                row_count=result.row_count,
                execution_time_ms=result.execution_time_ms,
            )
            return result
        except AppError as exc:
            exc.details.setdefault("catalog_id", command.catalog_id)
            if catalog is not None:
                exc.details.setdefault("catalog_version", catalog.catalog_version)
            enriched = exc.with_context(correlation_id=request_id, trace_id=trace_id)
            await self._diagnostics.query_failed(
                request_id=request_id,
                trace_id=trace_id,
                catalog_id=command.catalog_id,
                sql=command.sql,
                error=enriched,
            )
            raise enriched from exc
        except Exception as exc:
            unexpected = internal_error(
                "Analytics query execution failed unexpectedly",
                code="analytics_query.unhandled_exception",
                details={
                    "catalog_id": command.catalog_id,
                    "catalog_version": None if catalog is None else catalog.catalog_version,
                },
                operation="analytics_query.service.query_data",
                component="analytics_query",
                exc=exc,
            ).with_context(correlation_id=request_id, trace_id=trace_id)
            await self._diagnostics.query_failed(
                request_id=request_id,
                trace_id=trace_id,
                catalog_id=command.catalog_id,
                sql=command.sql,
                error=unexpected,
            )
            raise unexpected from exc
