from __future__ import annotations

from pathlib import Path

import pytest

from hello_sales_backend.modules.analytics_query.infra.catalogs import (
    SemanticAnalyticsCatalogStore,
)
from hello_sales_backend.modules.semantic_catalog.infra.catalogs import (
    YamlSemanticCatalogStore,
)
from hello_sales_backend.modules.semantic_catalog.use_cases.semantic_catalog_service import (
    SemanticCatalogService,
)
from hello_sales_backend.shared.errors import AppError


def test_scaffold_semantic_catalog_projects_existing_analytics_relations() -> None:
    catalog_dir = Path(__file__).resolve().parents[2] / "catalogs" / "semantic"
    store = YamlSemanticCatalogStore(catalog_dir)
    catalog = SemanticAnalyticsCatalogStore(
        SemanticCatalogService(catalogs=store)
    ).get_catalog("scaffold_stage")

    assert catalog.catalog_id == "scaffold_stage"
    assert catalog.catalog_version == "2026-04-23"
    assert {"company_profiles", "products", "analytics_daily_pipeline", "analytics_rep_performance"} == set(
        catalog.relations
    )
    assert catalog.relations["company_profiles"].columns["company_name"].semantic_type == "text"
    assert catalog.relations["products"].columns["revenue_share"].sensitivity == "internal"


def test_semantic_catalog_rejects_unsupported_field_policy(tmp_path: Path) -> None:
    catalog_dir = tmp_path / "catalogs"
    catalog_dir.mkdir()
    (catalog_dir / "catalog.yaml").write_text(
        """
catalog_id: bad_catalog
catalog_version: 1
dialect: postgres
description: Bad catalog
entities:
  - entity_type: product
    description: Product
    display:
      singular: Product
      plural: Products
      label_field: product_name
    storage:
      relation_name: products
      primary_key_field: product_id
      entity_kind: record
    analytics:
      enabled: true
    fields:
      - name: product_id
        data_type: text
        semantic_type: identifier
        sensitivity: public
        nullable: false
        description: Product id
        mutations:
          write_policy: system_managed
      - name: product_name
        data_type: text
        semantic_type: text
        sensitivity: public
        nullable: false
        description: Product name
        mutations:
          write_policy: unsupported_policy
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(AppError) as exc_info:
        YamlSemanticCatalogStore(catalog_dir).get_catalog("bad_catalog")

    assert exc_info.value.code == "semantic_catalog.catalog.unsupported_field_policy"
