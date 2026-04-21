"""Bounded SQL execution for governed analytics queries."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from hello_sales_backend.modules.analytics_query.use_cases.ports import (
    AnalyticsCatalog,
    ExecutedAnalyticsQuery,
    ValidatedAnalyticsQuery,
)
from hello_sales_backend.shared.errors import app_error


class SqlAlchemyAnalyticsQueryExecutor:
    """Execute validated SQL through SQLAlchemy with bounded runtime controls."""

    def __init__(
        self,
        *,
        engine: AsyncEngine,
        statement_timeout_ms: int,
        max_cell_length: int,
    ) -> None:
        del max_cell_length
        self._engine = engine
        self._statement_timeout_ms = statement_timeout_ms

    async def execute(
        self,
        *,
        catalog: AnalyticsCatalog,
        query: ValidatedAnalyticsQuery,
    ) -> ExecutedAnalyticsQuery:
        bounded_sql = (
            "SELECT * FROM ("
            f"{query.normalized_sql}"
            f") AS governed_query LIMIT {query.max_rows + 1}"
        )
        try:
            async with self._engine.connect() as connection:
                dialect_name = connection.dialect.name
                async with connection.begin():
                    if dialect_name == "postgresql":
                        await connection.execute(text("SET TRANSACTION READ ONLY"))
                        await connection.execute(
                            text(f"SET LOCAL statement_timeout = {self._statement_timeout_ms}")
                        )
                    result = await connection.execute(text(bounded_sql))
                    mappings = tuple(dict(row) for row in result.mappings().all())
                    truncated = len(mappings) > query.max_rows
                    rows = mappings[: query.max_rows]
                    return ExecutedAnalyticsQuery(
                        columns=tuple(result.keys()),
                        rows=tuple(rows),
                        truncated=truncated,
                    )
        except SQLAlchemyError as exc:
            message = str(exc).lower()
            error_code = (
                "analytics_query.execution.timeout"
                if "statement timeout" in message or "timeout" in message
                else "analytics_query.data_store.failed"
            )
            status_code = 504 if error_code.endswith("timeout") else 502
            failure_message = (
                "Analytics query exceeded the bounded execution timeout"
                if error_code.endswith("timeout")
                else "Analytics query failed against the data store"
            )
            raise app_error(
                failure_message,
                code=error_code,
                category="data",
                status_code=status_code,
                details={
                    "catalog_id": catalog.catalog_id,
                    "dialect": catalog.dialect,
                    "query_fingerprint": query.query_fingerprint,
                },
                operation="analytics_query.executor.execute",
                component="analytics_query",
                exc=exc,
            ) from exc
