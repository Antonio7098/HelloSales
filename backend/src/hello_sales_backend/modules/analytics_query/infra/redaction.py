"""Semantics-aware result shaping and redaction."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from hello_sales_backend.modules.analytics_query.use_cases.ports import (
    AnalyticsCatalog,
    ExecutedAnalyticsQuery,
    QueryProjection,
    ValidatedAnalyticsQuery,
)
from hello_sales_backend.shared.errors import app_error


class AnalyticsResultRedactor:
    """Shape bounded results and redact restricted columns."""

    def __init__(self, *, max_cell_length: int) -> None:
        self._max_cell_length = max_cell_length

    def redact(
        self,
        *,
        catalog: AnalyticsCatalog,
        query: ValidatedAnalyticsQuery,
        execution: ExecutedAnalyticsQuery,
        execution_time_ms: int,
    ) -> tuple[list[dict[str, object]], list[dict[str, object | None]]]:
        del catalog, execution_time_ms
        try:
            projection_index = {projection.output_name: projection for projection in query.projections}
            columns: list[dict[str, object]] = []
            redacted_columns: dict[str, bool] = {}
            for output_name in execution.columns:
                projection = projection_index.get(output_name)
                if projection is None:
                    projection = QueryProjection(
                        output_name=output_name,
                        data_type="derived",
                        semantic_type="derived",
                        description=None,
                        sensitivity="restricted",
                    )
                is_redacted = projection.sensitivity == "restricted"
                redacted_columns[output_name] = is_redacted
                columns.append(
                    {
                        "name": output_name,
                        "data_type": projection.data_type,
                        "semantic_type": projection.semantic_type,
                        "sensitivity": projection.sensitivity,
                        "redacted": is_redacted,
                        "description": projection.description,
                    }
                )
            rows: list[dict[str, object | None]] = []
            for row in execution.rows:
                shaped_row: dict[str, object | None] = {}
                for output_name in execution.columns:
                    shaped_row[output_name] = (
                        "***REDACTED***"
                        if redacted_columns.get(output_name, False)
                        else self._normalize_value(row.get(output_name))
                    )
                rows.append(shaped_row)
            return columns, rows
        except Exception as exc:
            raise app_error(
                "Analytics query results could not be redacted safely",
                code="analytics_query.redaction.failed",
                category="internal",
                status_code=500,
                details={"query_fingerprint": query.query_fingerprint},
                operation="analytics_query.redactor.redact",
                component="analytics_query",
                exc=exc,
            ) from exc

    def _normalize_value(self, value: Any) -> object | None:
        if value is None or isinstance(value, (bool, int, float)):
            return value
        if isinstance(value, str):
            if len(value) <= self._max_cell_length:
                return value
            return f"{value[: self._max_cell_length - 3]}..."
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, (datetime, date, time)):
            return value.isoformat()
        if isinstance(value, (bytes, bytearray)):
            return "<binary>"
        return str(value)
