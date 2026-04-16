"""System module public API."""

from hello_sales_backend.modules.system.bootstrap import SystemModule, build_system_module
from hello_sales_backend.modules.system.use_cases.system_service import SystemService
from hello_sales_backend.modules.system.use_cases.views import (
    SystemDiagnosticsView,
    SystemStatusView,
)

__all__ = [
    "SystemModule",
    "SystemDiagnosticsView",
    "SystemService",
    "SystemStatusView",
    "build_system_module",
]
