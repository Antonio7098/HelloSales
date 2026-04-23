from __future__ import annotations

from hello_sales_backend.platform.composition.app_container import build_app_container
from hello_sales_backend.platform.config.settings import Settings


def test_container_builds_runtime_graph(test_settings: Settings) -> None:
    container = build_app_container(test_settings)

    assert container.settings.environment == "test"
    assert container.modules.analytics_query.service is not None
    assert container.modules.company_profile.service is not None
    assert container.modules.system.service is not None
    assert container.health_service is not None
    assert container.tasks.pop_failures() == []
