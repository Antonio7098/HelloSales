"""Analytics query module assembly."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine

from hello_sales_backend.modules.analytics_query.infra.catalogs import (
    SemanticAnalyticsCatalogStore,
)
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
from hello_sales_backend.modules.semantic_catalog import SemanticCatalogService
from hello_sales_backend.platform.config.settings import Settings
from hello_sales_backend.platform.observability.runtime import ObservabilityRuntime


@dataclass(slots=True)
class AnalyticsQueryModule:
    """Resolved analytics-query module bundle."""

    service: AnalyticsQueryService

def build_analytics_query_module(
    *,
    settings: Settings,
    engine: AsyncEngine,
    observability: ObservabilityRuntime,
    semantic_catalogs: SemanticCatalogService,
) -> AnalyticsQueryModule:
    """Build the analytics-query module."""

    return AnalyticsQueryModule(
        service=AnalyticsQueryService(
            catalogs=SemanticAnalyticsCatalogStore(semantic_catalogs),
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
