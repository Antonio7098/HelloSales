"""Semantic catalog facade."""

from __future__ import annotations

from hello_sales_backend.modules.semantic_catalog.use_cases.ports import SemanticCatalogStorePort
from hello_sales_backend.modules.semantic_catalog.use_cases.views import (
    SemanticCatalogView,
    SemanticEntityView,
)
from hello_sales_backend.shared.errors import app_error


class SemanticCatalogService:
    """Expose the canonical semantic catalog through a small stable facade."""

    def __init__(self, *, catalogs: SemanticCatalogStorePort) -> None:
        self._catalogs = catalogs

    def get_catalog(self, catalog_id: str) -> SemanticCatalogView:
        return self._catalogs.get_catalog(catalog_id)

    def get_entity(self, *, catalog_id: str, entity_type: str) -> SemanticEntityView:
        catalog = self.get_catalog(catalog_id)
        entity = catalog.entities.get(entity_type)
        if entity is None:
            raise app_error(
                "Requested semantic entity is not registered",
                code="semantic_catalog.entity.not_found",
                category="validation",
                status_code=404,
                details={"catalog_id": catalog_id, "entity_type": entity_type},
                operation="semantic_catalog.get_entity",
                component="semantic_catalog",
            )
        return entity
