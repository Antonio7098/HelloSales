"""Typed module registry."""

from __future__ import annotations

from dataclasses import dataclass

from hello_sales_backend.modules.agent_runs.bootstrap import AgentRunsModule
from hello_sales_backend.modules.analytics_query.bootstrap import AnalyticsQueryModule
from hello_sales_backend.modules.auth.bootstrap import AuthModule
from hello_sales_backend.modules.company_profile.bootstrap import CompanyProfileModule
from hello_sales_backend.modules.entity_operations.bootstrap import EntityOperationsModule
from hello_sales_backend.modules.jobs.bootstrap import JobsModule
from hello_sales_backend.modules.semantic_catalog.bootstrap import SemanticCatalogModule
from hello_sales_backend.modules.sessions.bootstrap import SessionsModule
from hello_sales_backend.modules.system.bootstrap import SystemModule
from hello_sales_backend.modules.voice.bootstrap import VoiceModule
from hello_sales_backend.modules.web_search.bootstrap import WebSearchModule
from hello_sales_backend.modules.worker_runs.bootstrap import WorkerRunsModule


@dataclass(slots=True)
class ModuleRegistry:
    """Resolved module bundles."""

    analytics_query: AnalyticsQueryModule
    agent_runs: AgentRunsModule
    auth: AuthModule
    company_profile: CompanyProfileModule
    entity_operations: EntityOperationsModule
    jobs: JobsModule
    semantic_catalog: SemanticCatalogModule
    sessions: SessionsModule
    system: SystemModule
    voice: VoiceModule
    web_search: WebSearchModule
    worker_runs: WorkerRunsModule
