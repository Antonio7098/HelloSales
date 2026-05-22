"""YAML-backed semantic catalog loading."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from hello_sales_backend.modules.semantic_catalog.use_cases.views import (
    SemanticAnalyticsProjectionView,
    SemanticCatalogView,
    SemanticDisplayView,
    SemanticEntityView,
    SemanticFieldAnalyticsView,
    SemanticFieldMutationView,
    SemanticFieldView,
    SemanticMutationProjectionView,
    SemanticRelationshipView,
    SemanticStorageView,
)
from hello_sales_backend.shared.errors import app_error

_SUPPORTED_FIELD_POLICIES = {"editable", "create_only", "system_managed", "read_only"}


class FieldAnalyticsManifest(BaseModel):
    """Analytics manifest metadata for one field."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    column_name: str | None = None


class FieldMutationsManifest(BaseModel):
    """Mutation manifest metadata for one field."""

    model_config = ConfigDict(extra="forbid")

    write_policy: str = "editable"
    required_on_create: bool = False


class FieldManifest(BaseModel):
    """One semantic field definition."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    data_type: str = Field(min_length=1)
    description: str | None = None
    semantic_type: str = Field(min_length=1)
    sensitivity: str = Field(pattern="^(public|internal|restricted)$")
    nullable: bool = True
    analytics: FieldAnalyticsManifest = Field(default_factory=FieldAnalyticsManifest)
    mutations: FieldMutationsManifest = Field(default_factory=FieldMutationsManifest)


class RelationshipManifest(BaseModel):
    """One semantic relationship definition."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    target_entity_type: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    source_field: str | None = None
    description: str | None = None


class DisplayManifest(BaseModel):
    """Display metadata for one semantic entity."""

    model_config = ConfigDict(extra="forbid")

    singular: str = Field(min_length=1)
    plural: str = Field(min_length=1)
    label_field: str = Field(min_length=1)


class StorageManifest(BaseModel):
    """Storage hints for one semantic entity."""

    model_config = ConfigDict(extra="forbid")

    relation_name: str = Field(min_length=1)
    primary_key_field: str = Field(min_length=1)
    entity_kind: str = Field(pattern="^(singleton|record|aggregate)$")


class AnalyticsProjectionManifest(BaseModel):
    """Analytics projection for one entity surface."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    relation_name: str | None = None
    description: str | None = None


class MutationProjectionManifest(BaseModel):
    """Mutation projection for one entity surface."""

    model_config = ConfigDict(extra="forbid")

    create_allowed: bool = False
    edit_allowed: bool = False
    ref_ttl_seconds: int = Field(default=86_400, ge=60)
    create_requires_absence: bool = False


class EntityManifest(BaseModel):
    """One semantic entity definition."""

    model_config = ConfigDict(extra="forbid")

    entity_type: str = Field(min_length=1)
    description: str = Field(min_length=1)
    display: DisplayManifest
    storage: StorageManifest
    fields: list[FieldManifest] = Field(min_length=1)
    relationships: list[RelationshipManifest] = Field(default_factory=list)
    analytics: AnalyticsProjectionManifest | None = None
    mutations: MutationProjectionManifest | None = None


class SemanticCatalogManifest(BaseModel):
    """Top-level semantic catalog manifest."""

    model_config = ConfigDict(extra="forbid")

    catalog_id: str = Field(min_length=1)
    catalog_version: str = Field(min_length=1)
    dialect: str = Field(min_length=1)
    description: str = Field(min_length=1)
    entities: list[EntityManifest] = Field(min_length=1)

    @field_validator("catalog_version", mode="before")
    @classmethod
    def normalize_catalog_version(cls, value: object) -> object:
        if isinstance(value, str):
            return value
        return str(value)


class YamlSemanticCatalogStore:
    """Load one or more semantic catalogs from hand-authored YAML manifests."""

    def __init__(self, catalog_dir: Path) -> None:
        self._catalog_dir = catalog_dir
        self._catalogs = self._load_catalogs()

    def get_catalog(self, catalog_id: str) -> SemanticCatalogView:
        catalog = self._catalogs.get(catalog_id)
        if catalog is None:
            raise app_error(
                "Requested semantic catalog is not registered",
                code="semantic_catalog.catalog.not_found",
                category="validation",
                status_code=404,
                details={"catalog_id": catalog_id, "catalog_dir": str(self._catalog_dir)},
                operation="semantic_catalog.catalogs.get_catalog",
                component="semantic_catalog",
            )
        return catalog

    def _load_catalogs(self) -> dict[str, SemanticCatalogView]:
        if not self._catalog_dir.exists():
            raise app_error(
                "Semantic catalog directory does not exist",
                code="semantic_catalog.catalog.missing_directory",
                category="config",
                status_code=500,
                details={"catalog_dir": str(self._catalog_dir)},
                operation="semantic_catalog.catalogs.load_catalogs",
                component="semantic_catalog",
            )
        catalogs: dict[str, SemanticCatalogView] = {}
        for manifest_path in sorted(self._catalog_dir.glob("*.y*ml")):
            manifest = self._load_manifest(manifest_path)
            if manifest.catalog_id in catalogs:
                raise app_error(
                    "Duplicate semantic catalog identifier",
                    code="semantic_catalog.catalog.duplicate_catalog_id",
                    category="config",
                    status_code=500,
                    details={
                        "catalog_id": manifest.catalog_id,
                        "catalog_dir": str(self._catalog_dir),
                        "manifest_path": str(manifest_path),
                    },
                    operation="semantic_catalog.catalogs.load_catalogs",
                    component="semantic_catalog",
                )
            catalogs[manifest.catalog_id] = self._to_catalog(manifest)
        if not catalogs:
            raise app_error(
                "No semantic catalog manifests were found",
                code="semantic_catalog.catalog.empty_directory",
                category="config",
                status_code=500,
                details={"catalog_dir": str(self._catalog_dir)},
                operation="semantic_catalog.catalogs.load_catalogs",
                component="semantic_catalog",
            )
        return catalogs

    def _load_manifest(self, manifest_path: Path) -> SemanticCatalogManifest:
        try:
            raw_payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
            return SemanticCatalogManifest.model_validate(raw_payload)
        except (OSError, yaml.YAMLError, ValidationError) as exc:
            raise app_error(
                "Semantic catalog manifest could not be loaded",
                code="semantic_catalog.catalog.invalid_manifest",
                category="config",
                status_code=500,
                details={"manifest_path": str(manifest_path)},
                operation="semantic_catalog.catalogs.load_manifest",
                component="semantic_catalog",
                exc=exc,
            ) from exc

    def _to_catalog(self, manifest: SemanticCatalogManifest) -> SemanticCatalogView:
        entities: dict[str, SemanticEntityView] = {}
        analytics_relations: dict[str, str] = {}
        for entity_manifest in manifest.entities:
            if entity_manifest.entity_type in entities:
                raise app_error(
                    "Semantic entity types must be unique",
                    code="semantic_catalog.catalog.duplicate_entity_id",
                    category="config",
                    status_code=500,
                    details={"catalog_id": manifest.catalog_id, "entity_type": entity_manifest.entity_type},
                    operation="semantic_catalog.catalogs.to_catalog",
                    component="semantic_catalog",
                )
            fields: dict[str, SemanticFieldView] = {}
            for field_manifest in entity_manifest.fields:
                if field_manifest.name in fields:
                    raise app_error(
                        "Semantic entity field names must be unique",
                        code="semantic_catalog.catalog.duplicate_field_id",
                        category="config",
                        status_code=500,
                        details={
                            "catalog_id": manifest.catalog_id,
                            "entity_type": entity_manifest.entity_type,
                            "field_name": field_manifest.name,
                        },
                        operation="semantic_catalog.catalogs.to_catalog",
                        component="semantic_catalog",
                    )
                write_policy = field_manifest.mutations.write_policy
                if write_policy not in _SUPPORTED_FIELD_POLICIES:
                    raise app_error(
                        "Semantic field write policy is not supported",
                        code="semantic_catalog.catalog.unsupported_field_policy",
                        category="config",
                        status_code=500,
                        details={
                            "catalog_id": manifest.catalog_id,
                            "entity_type": entity_manifest.entity_type,
                            "field_name": field_manifest.name,
                            "write_policy": write_policy,
                        },
                        operation="semantic_catalog.catalogs.to_catalog",
                        component="semantic_catalog",
                    )
                fields[field_manifest.name] = SemanticFieldView(
                    name=field_manifest.name,
                    data_type=field_manifest.data_type,
                    description=field_manifest.description,
                    semantic_type=field_manifest.semantic_type,
                    sensitivity=field_manifest.sensitivity,
                    nullable=field_manifest.nullable,
                    analytics=SemanticFieldAnalyticsView(
                        enabled=field_manifest.analytics.enabled,
                        column_name=field_manifest.analytics.column_name,
                    ),
                    mutations=SemanticFieldMutationView(
                        write_policy=write_policy,
                        required_on_create=field_manifest.mutations.required_on_create,
                    ),
                )
            if entity_manifest.display.label_field not in fields:
                raise app_error(
                    "Semantic entity label field must reference a declared field",
                    code="semantic_catalog.catalog.invalid_projection",
                    category="config",
                    status_code=500,
                    details={
                        "catalog_id": manifest.catalog_id,
                        "entity_type": entity_manifest.entity_type,
                        "label_field": entity_manifest.display.label_field,
                    },
                    operation="semantic_catalog.catalogs.to_catalog",
                    component="semantic_catalog",
                )
            if entity_manifest.storage.primary_key_field not in fields:
                raise app_error(
                    "Semantic entity primary key field must reference a declared field",
                    code="semantic_catalog.catalog.invalid_projection",
                    category="config",
                    status_code=500,
                    details={
                        "catalog_id": manifest.catalog_id,
                        "entity_type": entity_manifest.entity_type,
                        "primary_key_field": entity_manifest.storage.primary_key_field,
                    },
                    operation="semantic_catalog.catalogs.to_catalog",
                    component="semantic_catalog",
                )
            relationships = tuple(
                SemanticRelationshipView(
                    name=item.name,
                    target_entity_type=item.target_entity_type,
                    kind=item.kind,
                    source_field=item.source_field,
                    description=item.description,
                )
                for item in entity_manifest.relationships
            )
            analytics = None
            if entity_manifest.analytics is not None and entity_manifest.analytics.enabled:
                relation_name = (
                    entity_manifest.analytics.relation_name or entity_manifest.storage.relation_name
                )
                if not relation_name:
                    raise app_error(
                        "Semantic analytics projection requires a relation name",
                        code="semantic_catalog.catalog.invalid_projection",
                        category="config",
                        status_code=500,
                        details={
                            "catalog_id": manifest.catalog_id,
                            "entity_type": entity_manifest.entity_type,
                        },
                        operation="semantic_catalog.catalogs.to_catalog",
                        component="semantic_catalog",
                    )
                owner = analytics_relations.get(relation_name)
                if owner is not None:
                    raise app_error(
                        "Semantic analytics relation names must be unique",
                        code="semantic_catalog.catalog.invalid_projection",
                        category="config",
                        status_code=500,
                        details={
                            "catalog_id": manifest.catalog_id,
                            "relation_name": relation_name,
                            "entity_type": entity_manifest.entity_type,
                            "owner_entity_type": owner,
                        },
                        operation="semantic_catalog.catalogs.to_catalog",
                        component="semantic_catalog",
                    )
                analytics_relations[relation_name] = entity_manifest.entity_type
                analytics = SemanticAnalyticsProjectionView(
                    enabled=True,
                    relation_name=relation_name,
                    description=entity_manifest.analytics.description,
                )
            mutations = None
            if entity_manifest.mutations is not None:
                mutations = SemanticMutationProjectionView(
                    create_allowed=entity_manifest.mutations.create_allowed,
                    edit_allowed=entity_manifest.mutations.edit_allowed,
                    ref_ttl_seconds=entity_manifest.mutations.ref_ttl_seconds,
                    create_requires_absence=entity_manifest.mutations.create_requires_absence,
                )
            entities[entity_manifest.entity_type] = SemanticEntityView(
                entity_type=entity_manifest.entity_type,
                description=entity_manifest.description,
                display=SemanticDisplayView(
                    singular=entity_manifest.display.singular,
                    plural=entity_manifest.display.plural,
                    label_field=entity_manifest.display.label_field,
                ),
                storage=SemanticStorageView(
                    relation_name=entity_manifest.storage.relation_name,
                    primary_key_field=entity_manifest.storage.primary_key_field,
                    entity_kind=entity_manifest.storage.entity_kind,
                ),
                fields=fields,
                relationships=relationships,
                analytics=analytics,
                mutations=mutations,
            )
        return SemanticCatalogView(
            catalog_id=manifest.catalog_id,
            catalog_version=manifest.catalog_version,
            dialect=manifest.dialect,
            description=manifest.description,
            entities=entities,
        )
