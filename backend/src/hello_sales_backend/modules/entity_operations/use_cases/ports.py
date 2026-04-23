"""Ports and internal models for generic entity operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from hello_sales_backend.modules.entity_operations.use_cases.commands import ScalarValue
from hello_sales_backend.modules.entity_operations.use_cases.views import EntityOperationContext
from hello_sales_backend.modules.semantic_catalog.use_cases.views import (
    SemanticCatalogView,
    SemanticEntityView,
)
from hello_sales_backend.shared.errors import AppError


@dataclass(frozen=True, slots=True)
class EntitySnapshot:
    """Canonical snapshot of one persisted entity."""

    entity_type: str
    entity_id: str
    version: str
    display_label: str
    values: dict[str, ScalarValue]


@dataclass(frozen=True, slots=True)
class IssuedEntityRef:
    """Opaque context entity ref emitted to the caller."""

    entity_ref: str
    entity_type: str
    entity_id: str
    display_label: str
    version: str
    allowed_operations: tuple[str, ...]
    expires_at: datetime | None


@dataclass(frozen=True, slots=True)
class MutationRecord:
    """Internal record for one successful entity mutation."""

    operation_id: str
    operation: str
    catalog_id: str
    catalog_version: str
    entity_type: str
    entity_id: str
    entity_ref: str
    display_label: str
    version_before: str | None
    version_after: str
    changed_fields: tuple[str, ...]
    before_snapshot: dict[str, ScalarValue] | None
    after_snapshot: dict[str, ScalarValue]
    undo_status: str
    warnings: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    audit: dict[str, str | None] = field(default_factory=dict)


class EntityCatalogPort(Protocol):
    """Resolve semantic catalog projections for entity operations."""

    def get_catalog(self, catalog_id: str) -> SemanticCatalogView: ...

    def get_entity(self, *, catalog_id: str, entity_type: str) -> SemanticEntityView: ...


class ContextEntityRefResolverPort(Protocol):
    """Issue and resolve session-scoped context refs."""

    def issue_ref(
        self,
        *,
        snapshot: EntitySnapshot,
        allowed_operations: tuple[str, ...],
        ttl_seconds: int,
        context: EntityOperationContext,
    ) -> IssuedEntityRef: ...

    async def resolve_ref(
        self,
        *,
        entity_ref: str,
        required_operation: str,
        context: EntityOperationContext,
    ) -> IssuedEntityRef: ...


class EntityMutationExecutorPort(Protocol):
    """Persist semantic entity changes through module-owned adapters."""

    async def get_entity(self, *, entity_type: str, entity_id: str) -> EntitySnapshot | None: ...

    async def create_entity(
        self, *, entity: SemanticEntityView, values: dict[str, ScalarValue]
    ) -> EntitySnapshot: ...

    async def edit_entity(
        self,
        *,
        entity: SemanticEntityView,
        entity_id: str,
        changes: dict[str, ScalarValue],
    ) -> EntitySnapshot: ...


class MutationRecordStorePort(Protocol):
    """Persist successful mutation records for later inspection or undo."""

    async def save(self, record: MutationRecord) -> None: ...

    async def get(self, operation_id: str) -> MutationRecord | None: ...


class EntityOperationsDiagnosticsPort(Protocol):
    """Emit correlated diagnostics for mutations and undo attempts."""

    async def mutation_created(
        self,
        *,
        context: EntityOperationContext,
        record: MutationRecord,
    ) -> None: ...

    async def mutation_updated(
        self,
        *,
        context: EntityOperationContext,
        record: MutationRecord,
    ) -> None: ...

    async def mutation_rejected(
        self,
        *,
        context: EntityOperationContext,
        entity_type: str | None,
        entity_ref: str | None,
        changed_fields: tuple[str, ...],
        error: AppError,
    ) -> None: ...

    async def stale_version(
        self,
        *,
        context: EntityOperationContext,
        entity_type: str | None,
        entity_ref: str | None,
        changed_fields: tuple[str, ...],
        error: AppError,
    ) -> None: ...

    async def mutation_failed(
        self,
        *,
        context: EntityOperationContext,
        entity_type: str | None,
        entity_ref: str | None,
        changed_fields: tuple[str, ...],
        error: AppError,
    ) -> None: ...

    async def undo_applied(
        self,
        *,
        context: EntityOperationContext,
        record: MutationRecord,
    ) -> None: ...

    async def undo_conflicted(
        self,
        *,
        context: EntityOperationContext,
        record: MutationRecord,
        error: AppError,
    ) -> None: ...

    async def undo_unavailable(
        self,
        *,
        context: EntityOperationContext,
        record: MutationRecord,
        error: AppError,
    ) -> None: ...
