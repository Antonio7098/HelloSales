"""Generic entity operations bounded context."""

from .bootstrap import EntityOperationsModule, build_entity_operations_module
from .use_cases.entity_operations_service import EntityOperationsService

__all__ = [
    "EntityOperationsModule",
    "EntityOperationsService",
    "build_entity_operations_module",
]
