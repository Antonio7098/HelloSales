"""Views for the canonical semantic catalog."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class SemanticFieldAnalyticsView:
    """Analytics projection metadata for one field."""

    enabled: bool = True
    column_name: str | None = None


@dataclass(frozen=True, slots=True)
class SemanticFieldMutationView:
    """Mutation projection metadata for one field."""

    write_policy: str = "editable"
    required_on_create: bool = False


@dataclass(frozen=True, slots=True)
class SemanticFieldView:
    """Canonical semantic field definition."""

    name: str
    data_type: str
    description: str | None
    semantic_type: str
    sensitivity: str
    nullable: bool
    analytics: SemanticFieldAnalyticsView = field(default_factory=SemanticFieldAnalyticsView)
    mutations: SemanticFieldMutationView = field(default_factory=SemanticFieldMutationView)


@dataclass(frozen=True, slots=True)
class SemanticRelationshipView:
    """Relationship metadata between semantic entities."""

    name: str
    target_entity_type: str
    kind: str
    source_field: str | None = None
    description: str | None = None


@dataclass(frozen=True, slots=True)
class SemanticStorageView:
    """Storage hints for one entity surface."""

    relation_name: str
    primary_key_field: str
    entity_kind: str


@dataclass(frozen=True, slots=True)
class SemanticDisplayView:
    """Agent-facing display metadata."""

    singular: str
    plural: str
    label_field: str


@dataclass(frozen=True, slots=True)
class SemanticAnalyticsProjectionView:
    """Analytics metadata for an entity surface."""

    enabled: bool = True
    relation_name: str | None = None
    description: str | None = None


@dataclass(frozen=True, slots=True)
class SemanticMutationProjectionView:
    """Mutation metadata for an entity surface."""

    create_allowed: bool = False
    edit_allowed: bool = False
    ref_ttl_seconds: int = 86_400
    create_requires_absence: bool = False


@dataclass(frozen=True, slots=True)
class SemanticEntityView:
    """Canonical semantic entity definition."""

    entity_type: str
    description: str
    display: SemanticDisplayView
    storage: SemanticStorageView
    fields: dict[str, SemanticFieldView]
    relationships: tuple[SemanticRelationshipView, ...] = ()
    analytics: SemanticAnalyticsProjectionView | None = None
    mutations: SemanticMutationProjectionView | None = None


@dataclass(frozen=True, slots=True)
class SemanticCatalogView:
    """Loaded semantic catalog."""

    catalog_id: str
    catalog_version: str
    dialect: str
    description: str
    entities: dict[str, SemanticEntityView]
