"""Semantic catalog module assembly."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hello_sales_backend.modules.semantic_catalog.infra.catalogs import (
    YamlSemanticCatalogStore,
)
from hello_sales_backend.modules.semantic_catalog.use_cases.semantic_catalog_service import (
    SemanticCatalogService,
)
from hello_sales_backend.platform.config.settings import Settings


@dataclass(slots=True)
class SemanticCatalogModule:
    """Resolved semantic-catalog module bundle."""

    service: SemanticCatalogService


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


def build_semantic_catalog_module(*, settings: Settings) -> SemanticCatalogModule:
    """Build the semantic catalog module."""

    catalog_store = YamlSemanticCatalogStore(_resolve_catalog_dir(settings.semantic_catalog_dir))
    return SemanticCatalogModule(service=SemanticCatalogService(catalogs=catalog_store))
