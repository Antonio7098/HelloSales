"""Analytics query module assembly."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine

from hello_sales_backend.modules.analytics_query.infra.catalogs import YamlAnalyticsCatalogStore
from hello_sales_backend.modules.analytics_query.infra.executor import (
    SqlAlchemyAnalyticsQueryExecutor,
)
from hello_sales_backend.modules.analytics_query.infra.observability import (
    AnalyticsQueryObservabilityAdapter,
)
from hello_sales_backend.modules.analytics_query.infra.redaction import AnalyticsResultRedactor
from hello_sales_backend.modules.analytics_query.infra.validator import (
    SqlglotAnalyticsQueryValidator,
)
from hello_sales_backend.modules.analytics_query.use_cases.analytics_query_service import (
    AnalyticsQueryService,
)
from hello_sales_backend.platform.config.settings import Settings
from hello_sales_backend.platform.observability.runtime import ObservabilityRuntime


@dataclass(slots=True)
class AnalyticsQueryModule:
    """Resolved analytics-query module bundle."""

    service: AnalyticsQueryService


def _resolve_catalog_dir(configured_path: str) -> Path:
    path = Path(configured_path)
    if path.is_absolute():
        return path
    backend_root = Path(__file__).resolve().parents[4]
    repo_root = Path(__file__).resolve().parents[5]
    candidates = (
        Path.cwd() / path,
        backend_root / path,
        repo_root / path,
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return repo_root / path


def build_analytics_query_module(
    *,
    settings: Settings,
    engine: AsyncEngine,
    observability: ObservabilityRuntime,
) -> AnalyticsQueryModule:
    """Build the analytics-query module."""

    catalog_store = YamlAnalyticsCatalogStore(_resolve_catalog_dir(settings.analytics_query_catalog_dir))
    return AnalyticsQueryModule(
        service=AnalyticsQueryService(
            catalogs=catalog_store,
            validator=SqlglotAnalyticsQueryValidator(default_max_rows=settings.analytics_query_default_max_rows),
            executor=SqlAlchemyAnalyticsQueryExecutor(
                engine=engine,
                statement_timeout_ms=settings.analytics_query_statement_timeout_ms,
                max_cell_length=settings.analytics_query_max_cell_length,
            ),
            redactor=AnalyticsResultRedactor(max_cell_length=settings.analytics_query_max_cell_length),
            diagnostics=AnalyticsQueryObservabilityAdapter(observability=observability),
        )
    )
