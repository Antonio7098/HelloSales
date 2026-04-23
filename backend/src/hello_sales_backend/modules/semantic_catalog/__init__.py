"""Semantic catalog bounded context."""

from .bootstrap import SemanticCatalogModule, build_semantic_catalog_module
from .use_cases.semantic_catalog_service import SemanticCatalogService

__all__ = [
    "SemanticCatalogModule",
    "SemanticCatalogService",
    "build_semantic_catalog_module",
]
