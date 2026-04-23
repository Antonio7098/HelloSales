"""Semantic-catalog-backed analytics projection adapter."""

from __future__ import annotations

from hello_sales_backend.modules.analytics_query.use_cases.ports import (
    AnalyticsCatalog,
    AnalyticsCatalogColumn,
    AnalyticsCatalogRelation,
)
from hello_sales_backend.modules.semantic_catalog import SemanticCatalogService
from hello_sales_backend.shared.errors import app_error


class SemanticAnalyticsCatalogStore:
    """Project analytics catalogs from the canonical semantic catalog."""

    def __init__(self, semantic_catalogs: SemanticCatalogService) -> None:
        self._semantic_catalogs = semantic_catalogs

    def get_catalog(self, catalog_id: str) -> AnalyticsCatalog:
        catalog = self._semantic_catalogs.get_catalog(catalog_id)
        relations: dict[str, AnalyticsCatalogRelation] = {}
        for entity in catalog.entities.values():
            projection = entity.analytics
            if projection is None or not projection.enabled:
                continue
            relation_name = projection.relation_name or entity.storage.relation_name
            if relation_name in relations:
                raise app_error(
                    "Analytics projection relation names must be unique",
                    code="semantic_catalog.catalog.invalid_projection",
                    category="config",
                    status_code=500,
                    details={
                        "catalog_id": catalog.catalog_id,
                        "relation_name": relation_name,
                        "entity_type": entity.entity_type,
                    },
                    operation="analytics_query.catalogs.get_catalog",
                    component="semantic_catalog",
                )
            columns: dict[str, AnalyticsCatalogColumn] = {}
            for field in entity.fields.values():
                if not field.analytics.enabled:
                    continue
                column_name = field.analytics.column_name or field.name
                if column_name in columns:
                    raise app_error(
                        "Analytics projection column names must be unique",
                        code="semantic_catalog.catalog.invalid_projection",
                        category="config",
                        status_code=500,
                        details={
                            "catalog_id": catalog.catalog_id,
                            "entity_type": entity.entity_type,
                            "relation_name": relation_name,
                            "column_name": column_name,
                        },
                        operation="analytics_query.catalogs.get_catalog",
                        component="semantic_catalog",
                    )
                columns[column_name] = AnalyticsCatalogColumn(
                    name=column_name,
                    data_type=field.data_type,
                    description=field.description,
                    semantic_type=field.semantic_type,
                    sensitivity=field.sensitivity,
                )
            if not columns:
                raise app_error(
                    "Analytics projection must expose at least one column",
                    code="semantic_catalog.catalog.invalid_projection",
                    category="config",
                    status_code=500,
                    details={
                        "catalog_id": catalog.catalog_id,
                        "entity_type": entity.entity_type,
                        "relation_name": relation_name,
                    },
                    operation="analytics_query.catalogs.get_catalog",
                    component="semantic_catalog",
                )
            relations[relation_name] = AnalyticsCatalogRelation(
                name=relation_name,
                description=projection.description or entity.description,
                columns=columns,
            )
        if not relations:
            raise app_error(
                "Semantic catalog does not expose any analytics relations",
                code="semantic_catalog.catalog.invalid_projection",
                category="config",
                status_code=500,
                details={"catalog_id": catalog.catalog_id},
                operation="analytics_query.catalogs.get_catalog",
                component="semantic_catalog",
            )
        return AnalyticsCatalog(
            catalog_id=catalog.catalog_id,
            catalog_version=catalog.catalog_version,
            dialect=catalog.dialect,
            description=catalog.description,
            relations=relations,
        )
