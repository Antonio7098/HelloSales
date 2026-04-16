"""Application startup and shutdown helpers."""

from __future__ import annotations

from hello_sales_backend.platform.composition.app_container import AppContainer
from hello_sales_backend.platform.db.session import ping_database
from hello_sales_backend.platform.observability.events import OperationalEvent
from hello_sales_backend.platform.observability.logging import get_logger
from hello_sales_backend.shared.errors import app_error


def _validate_settings(container: AppContainer) -> None:
    settings = container.settings
    if settings.environment not in {"development", "test", "staging", "production"}:
        raise app_error(
            "Invalid runtime environment",
            code="config.invalid_environment",
            category="config",
            status_code=500,
            severity="critical",
            details={"environment": settings.environment},
            operation="startup.validate_settings",
            component="config",
        )

    supported_providers = set(type(settings).PROVIDER_BASE_URLS)
    using_generic_provider = bool(settings.generic_agent_provider)
    if using_generic_provider and settings.generic_agent_provider not in supported_providers:
        raise app_error(
            "Generic-agent provider is not supported",
            code="config.llm_provider.unsupported",
            category="config",
            status_code=500,
            severity="critical",
            details={
                "provider": settings.generic_agent_provider,
                "supported_providers": sorted(supported_providers),
            },
            operation="startup.validate_settings",
            component="config",
        )

    llm_api_key_present = bool(settings.resolved_generic_agent_api_key.strip())
    llm_base_url_present = bool(settings.resolved_generic_agent_base_url.strip())
    llm_model_present = bool(settings.resolved_generic_agent_model.strip())
    generic_shape_without_key = using_generic_provider and (
        settings.generic_agent_model or settings.generic_agent_provider or settings.generic_agent_base_url
    )
    custom_provider_shape_without_key = not llm_api_key_present and generic_shape_without_key
    partial_llm_config = (llm_api_key_present and not all((llm_base_url_present, llm_model_present))) or custom_provider_shape_without_key
    if partial_llm_config:
        raise app_error(
            "LLM provider configuration is partial",
            code="config.llm_provider.partial",
            category="config",
            status_code=500,
            severity="critical",
            details={
                "provider": settings.resolved_generic_agent_provider,
                "llm_api_key_present": llm_api_key_present,
                "llm_base_url_present": llm_base_url_present,
                "llm_model_present": llm_model_present,
            },
            operation="startup.validate_settings",
            component="config",
        )


async def bootstrap_container(container: AppContainer) -> None:
    """Run startup hooks."""

    logger = get_logger("hello_sales_backend.startup")
    try:
        _validate_settings(container)
        if not container.settings.database_url.startswith("sqlite+aiosqlite"):
            await ping_database(container.db.session_factory)
        logger.info(
            "application.startup.completed",
            environment=container.settings.environment,
            workflow_engine=container.workflow_runtime.engine_name,
            workflow_installed=container.workflow_runtime.installed,
            llm_provider=container.providers.llm.provider_name,
            llm_available=container.providers.llm.is_configured(),
        )
        await container.observability.emit(
            OperationalEvent(
                event_type="startup.completed",
                severity="info",
                component="startup",
                operation="bootstrap_container",
                code="startup.completed",
                payload={
                    "message": "Application startup completed",
                    "severity": "info",
                    "environment": container.settings.environment,
                    "workflow_engine": container.workflow_runtime.engine_name,
                    "workflow_installed": container.workflow_runtime.installed,
                    "llm_provider": container.providers.llm.provider_name,
                    "llm_available": container.providers.llm.is_configured(),
                },
            )
        )
    except Exception as exc:
        startup_error = exc if isinstance(exc, Exception) else Exception("unknown startup failure")
        logger.critical(
            "application.startup.failed",
            environment=container.settings.environment,
            workflow_engine=container.workflow_runtime.engine_name,
            workflow_installed=container.workflow_runtime.installed,
            error_type=startup_error.__class__.__name__,
            error_message=str(startup_error),
        )
        await container.observability.emit(
            OperationalEvent(
                event_type="startup.failed",
                severity="critical",
                component="startup",
                operation="bootstrap_container",
                code=getattr(startup_error, "code", "startup.failed"),
                payload={
                    "message": str(startup_error),
                    "severity": "critical",
                    "error_type": startup_error.__class__.__name__,
                    "code": getattr(startup_error, "code", "startup.failed"),
                    "details": getattr(startup_error, "details", {}),
                },
            )
        )
        raise


async def shutdown_container(container: AppContainer) -> None:
    """Run shutdown hooks."""

    logger = get_logger("hello_sales_backend.startup")
    await container.tasks.shutdown()
    await container.providers.aclose()
    await container.db.engine.dispose()
    logger.info("application.shutdown.completed", environment=container.settings.environment)
