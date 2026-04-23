"""Observability adapter for entity operations."""

from __future__ import annotations

from hello_sales_backend.modules.entity_operations.use_cases.ports import MutationRecord
from hello_sales_backend.modules.entity_operations.use_cases.views import EntityOperationContext
from hello_sales_backend.platform.observability.events import OperationalEvent
from hello_sales_backend.platform.observability.runtime import ObservabilityRuntime
from hello_sales_backend.shared.errors import AppError


class EntityOperationsObservabilityAdapter:
    """Emit stable operational metadata for entity mutations."""

    def __init__(self, *, observability: ObservabilityRuntime) -> None:
        self._observability = observability

    async def mutation_created(
        self,
        *,
        context: EntityOperationContext,
        record: MutationRecord,
    ) -> None:
        await self._emit(event_type="entity_operations.mutation.created", context=context, record=record)

    async def mutation_updated(
        self,
        *,
        context: EntityOperationContext,
        record: MutationRecord,
    ) -> None:
        await self._emit(event_type="entity_operations.mutation.updated", context=context, record=record)

    async def mutation_rejected(
        self,
        *,
        context: EntityOperationContext,
        entity_type: str | None,
        entity_ref: str | None,
        changed_fields: tuple[str, ...],
        error: AppError,
    ) -> None:
        await self._emit_error(
            event_type="entity_operations.mutation.rejected",
            context=context,
            entity_type=entity_type,
            entity_ref=entity_ref,
            changed_fields=changed_fields,
            error=error,
        )

    async def stale_version(
        self,
        *,
        context: EntityOperationContext,
        entity_type: str | None,
        entity_ref: str | None,
        changed_fields: tuple[str, ...],
        error: AppError,
    ) -> None:
        await self._emit_error(
            event_type="entity_operations.mutation.stale_version",
            context=context,
            entity_type=entity_type,
            entity_ref=entity_ref,
            changed_fields=changed_fields,
            error=error,
        )

    async def mutation_failed(
        self,
        *,
        context: EntityOperationContext,
        entity_type: str | None,
        entity_ref: str | None,
        changed_fields: tuple[str, ...],
        error: AppError,
    ) -> None:
        await self._emit_error(
            event_type="entity_operations.mutation.failed",
            context=context,
            entity_type=entity_type,
            entity_ref=entity_ref,
            changed_fields=changed_fields,
            error=error,
        )

    async def undo_applied(
        self,
        *,
        context: EntityOperationContext,
        record: MutationRecord,
    ) -> None:
        await self._emit(event_type="entity_operations.undo.applied", context=context, record=record)

    async def undo_conflicted(
        self,
        *,
        context: EntityOperationContext,
        record: MutationRecord,
        error: AppError,
    ) -> None:
        await self._emit_error(
            event_type="entity_operations.undo.conflicted",
            context=context,
            entity_type=record.entity_type,
            entity_ref=record.entity_ref,
            changed_fields=record.changed_fields,
            error=error,
        )

    async def undo_unavailable(
        self,
        *,
        context: EntityOperationContext,
        record: MutationRecord,
        error: AppError,
    ) -> None:
        await self._emit_error(
            event_type="entity_operations.undo.unavailable",
            context=context,
            entity_type=record.entity_type,
            entity_ref=record.entity_ref,
            changed_fields=record.changed_fields,
            error=error,
        )

    async def _emit(
        self,
        *,
        event_type: str,
        context: EntityOperationContext,
        record: MutationRecord,
    ) -> None:
        await self._observability.emit(
            OperationalEvent(
                event_type=event_type,
                severity="info",
                component="entity_operations",
                operation=f"entity_operations.{record.operation}",
                correlation_id=context.request_id,
                trace_id=context.trace_id,
                code=event_type,
                payload={
                    **context.model_dump(mode="json"),
                    "operation_id": record.operation_id,
                    "entity_type": record.entity_type,
                    "entity_ref": record.entity_ref,
                    "changed_fields": list(record.changed_fields),
                    "version_before": record.version_before,
                    "version_after": record.version_after,
                    "undo_status": record.undo_status,
                    "catalog_id": record.catalog_id,
                    "catalog_version": record.catalog_version,
                },
            )
        )

    async def _emit_error(
        self,
        *,
        event_type: str,
        context: EntityOperationContext,
        entity_type: str | None,
        entity_ref: str | None,
        changed_fields: tuple[str, ...],
        error: AppError,
    ) -> None:
        await self._observability.emit(
            OperationalEvent(
                event_type=event_type,
                severity=error.severity,
                component="entity_operations",
                operation="entity_operations",
                correlation_id=context.request_id,
                trace_id=context.trace_id,
                code=error.code,
                payload={
                    **context.model_dump(mode="json"),
                    "entity_type": entity_type,
                    "entity_ref": entity_ref,
                    "changed_fields": list(changed_fields),
                    "error": error.to_dict(),
                },
            )
        )
