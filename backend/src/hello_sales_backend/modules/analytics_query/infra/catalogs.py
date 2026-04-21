"""YAML-backed semantic catalog loading."""

from __future__ import annotations

from pathlib import Path

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from hello_sales_backend.modules.analytics_query.use_cases.ports import (
    AnalyticsCatalog,
    AnalyticsCatalogColumn,
    AnalyticsCatalogRelation,
)
from hello_sales_backend.shared.errors import app_error


class CatalogColumnManifest(BaseModel):
    """Column definition in the semantic catalog manifest."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    data_type: str = Field(min_length=1)
    description: str | None = None
    semantic_type: str = Field(min_length=1)
    sensitivity: str = Field(pattern="^(public|internal|restricted)$")


class CatalogRelationManifest(BaseModel):
    """Relation definition in the semantic catalog manifest."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    columns: list[CatalogColumnManifest] = Field(min_length=1)


class AnalyticsCatalogManifest(BaseModel):
    """Top-level semantic catalog manifest."""

    model_config = ConfigDict(extra="forbid")

    catalog_id: str = Field(min_length=1)
    catalog_version: str = Field(min_length=1)
    dialect: str = Field(min_length=1)
    description: str = Field(min_length=1)
    relations: list[CatalogRelationManifest] = Field(min_length=1)

    @field_validator("catalog_version", mode="before")
    @classmethod
    def normalize_catalog_version(cls, value: object) -> object:
        if isinstance(value, str):
            return value
        return str(value)


class YamlAnalyticsCatalogStore:
    """Load one or more analytics catalogs from hand-authored YAML manifests."""

    def __init__(self, catalog_dir: Path) -> None:
        self._catalog_dir = catalog_dir
        self._catalogs = self._load_catalogs()

    def get_catalog(self, catalog_id: str) -> AnalyticsCatalog:
        catalog = self._catalogs.get(catalog_id)
        if catalog is None:
            raise app_error(
                "Requested analytics catalog is not registered",
                code="analytics_query.catalog.not_found",
                category="validation",
                status_code=404,
                details={"catalog_id": catalog_id, "catalog_dir": str(self._catalog_dir)},
                operation="analytics_query.catalogs.get_catalog",
                component="analytics_query",
            )
        return catalog

    def _load_catalogs(self) -> dict[str, AnalyticsCatalog]:
        if not self._catalog_dir.exists():
            raise app_error(
                "Analytics catalog directory does not exist",
                code="analytics_query.catalog.missing_directory",
                category="config",
                status_code=500,
                details={"catalog_dir": str(self._catalog_dir)},
                operation="analytics_query.catalogs.load_catalogs",
                component="analytics_query",
            )
        catalogs: dict[str, AnalyticsCatalog] = {}
        for manifest_path in sorted(self._catalog_dir.glob("*.y*ml")):
            manifest = self._load_manifest(manifest_path)
            if manifest.catalog_id in catalogs:
                raise app_error(
                    "Duplicate analytics catalog identifier",
                    code="analytics_query.catalog.duplicate_catalog_id",
                    category="config",
                    status_code=500,
                    details={
                        "catalog_id": manifest.catalog_id,
                        "catalog_dir": str(self._catalog_dir),
                        "manifest_path": str(manifest_path),
                    },
                    operation="analytics_query.catalogs.load_catalogs",
                    component="analytics_query",
                )
            catalogs[manifest.catalog_id] = self._to_catalog(manifest)
        if not catalogs:
            raise app_error(
                "No analytics catalog manifests were found",
                code="analytics_query.catalog.empty_directory",
                category="config",
                status_code=500,
                details={"catalog_dir": str(self._catalog_dir)},
                operation="analytics_query.catalogs.load_catalogs",
                component="analytics_query",
            )
        return catalogs

    def _load_manifest(self, manifest_path: Path) -> AnalyticsCatalogManifest:
        try:
            raw_payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
            return AnalyticsCatalogManifest.model_validate(raw_payload)
        except (OSError, yaml.YAMLError, ValidationError) as exc:
            raise app_error(
                "Analytics catalog manifest could not be loaded",
                code="analytics_query.catalog.invalid_manifest",
                category="config",
                status_code=500,
                details={"manifest_path": str(manifest_path)},
                operation="analytics_query.catalogs.load_manifest",
                component="analytics_query",
                exc=exc,
            ) from exc

    @staticmethod
    def _to_catalog(manifest: AnalyticsCatalogManifest) -> AnalyticsCatalog:
        relations: dict[str, AnalyticsCatalogRelation] = {}
        for relation_manifest in manifest.relations:
            if relation_manifest.name in relations:
                raise app_error(
                    "Analytics catalog relation names must be unique",
                    code="analytics_query.catalog.duplicate_relation",
                    category="config",
                    status_code=500,
                    details={"catalog_id": manifest.catalog_id, "relation": relation_manifest.name},
                    operation="analytics_query.catalogs.to_catalog",
                    component="analytics_query",
                )
            columns: dict[str, AnalyticsCatalogColumn] = {}
            for column_manifest in relation_manifest.columns:
                if column_manifest.name in columns:
                    raise app_error(
                        "Analytics relation column names must be unique",
                        code="analytics_query.catalog.duplicate_column",
                        category="config",
                        status_code=500,
                        details={
                            "catalog_id": manifest.catalog_id,
                            "relation": relation_manifest.name,
                            "column": column_manifest.name,
                        },
                        operation="analytics_query.catalogs.to_catalog",
                        component="analytics_query",
                    )
                columns[column_manifest.name] = AnalyticsCatalogColumn(
                    name=column_manifest.name,
                    data_type=column_manifest.data_type,
                    description=column_manifest.description,
                    semantic_type=column_manifest.semantic_type,
                    sensitivity=column_manifest.sensitivity,
                )
            relations[relation_manifest.name] = AnalyticsCatalogRelation(
                name=relation_manifest.name,
                description=relation_manifest.description,
                columns=columns,
            )
        return AnalyticsCatalog(
            catalog_id=manifest.catalog_id,
            catalog_version=manifest.catalog_version,
            dialect=manifest.dialect,
            description=manifest.description,
            relations=relations,
        )
