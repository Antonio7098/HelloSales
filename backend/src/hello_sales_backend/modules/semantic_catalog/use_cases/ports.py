"""Ports for semantic catalog use cases."""

from __future__ import annotations

from typing import Protocol

from hello_sales_backend.modules.semantic_catalog.use_cases.views import SemanticCatalogView


class SemanticCatalogStorePort(Protocol):
    """Load one semantic catalog by identifier."""

    def get_catalog(self, catalog_id: str) -> SemanticCatalogView: ...
