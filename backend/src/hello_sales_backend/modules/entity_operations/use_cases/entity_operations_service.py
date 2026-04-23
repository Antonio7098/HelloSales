"""Generic entity create/edit orchestration."""

from __future__ import annotations

from hello_sales_backend.modules.entity_operations.use_cases.commands import (
    CreateEntityCommand,
    EditEntityCommand,
    ScalarValue,
    UndoEntityMutationCommand,
)
from hello_sales_backend.modules.entity_operations.use_cases.ports import (
    ContextEntityRefResolverPort,
    EntityCatalogPort,
    EntityMutationExecutorPort,
    EntityOperationsDiagnosticsPort,
    EntitySnapshot,
    MutationRecord,
    MutationRecordStorePort,
)
from hello_sales_backend.modules.entity_operations.use_cases.views import (
    EntityMutationAuditView,
    EntityMutationResultView,
    EntityOperationContext,
)
from hello_sales_backend.modules.semantic_catalog.use_cases.views import (
    SemanticCatalogView,
    SemanticEntityView,
    SemanticFieldView,
)
from hello_sales_backend.shared.errors import AppError, app_error, internal_error
from hello_sales_backend.shared.ids import new_id


class EntityOperationsService:
    """Expose strict generic create/edit entity operations."""

    def __init__(
        self,
        *,
        catalog_id: str,
        catalogs: EntityCatalogPort,
        refs: ContextEntityRefResolverPort,
        executor: EntityMutationExecutorPort,
        records: MutationRecordStorePort,
        diagnostics: EntityOperationsDiagnosticsPort,
    ) -> None:
        self._catalog_id = catalog_id
        self._catalogs = catalogs
        self._refs = refs
        self._executor = executor
        self._records = records
        self._diagnostics = diagnostics

    async def create_entity(
        self,
        *,
        context: EntityOperationContext,
        command: CreateEntityCommand,
    ) -> EntityMutationResultView:
        changed_fields = tuple(sorted(command.values))
        catalog: SemanticCatalogView | None = None
        try:
            catalog = self._catalogs.get_catalog(self._catalog_id)
            entity = self._catalogs.get_entity(catalog_id=self._catalog_id, entity_type=command.entity_type)
            self._require_create_allowed(entity=entity)
            validated = self._validate_create_values(entity=entity, values=command.values)
            snapshot = await self._executor.create_entity(entity=entity, values=validated)
            issued_ref = self._refs.issue_ref(
                snapshot=snapshot,
                allowed_operations=self._allowed_operations(entity),
                ttl_seconds=entity.mutations.ref_ttl_seconds if entity.mutations is not None else 86_400,
                context=context,
            )
            warnings = (
                "Undo for create operations is unavailable in Sprint 7 because delete/archive semantics are deferred.",
            )
            record = MutationRecord(
                operation_id=new_id(),
                operation="create",
                catalog_id=catalog.catalog_id,
                catalog_version=catalog.catalog_version,
                entity_type=snapshot.entity_type,
                entity_id=snapshot.entity_id,
                entity_ref=issued_ref.entity_ref,
                display_label=snapshot.display_label,
                version_before=None,
                version_after=snapshot.version,
                changed_fields=changed_fields,
                before_snapshot=None,
                after_snapshot=dict(snapshot.values),
                undo_status="unavailable",
                warnings=warnings,
                audit=self._audit_payload(context),
            )
            await self._records.save(record)
            await self._diagnostics.mutation_created(context=context, record=record)
            return self._to_result(record=record, context=context)
        except AppError as exc:
            self._annotate_error(
                exc,
                catalog_id=self._catalog_id,
                catalog_version=None if catalog is None else catalog.catalog_version,
            )
            await self._emit_failure(
                context=context,
                entity_type=command.entity_type,
                entity_ref=None,
                changed_fields=changed_fields,
                error=exc,
            )
            raise
        except Exception as exc:
            structured = internal_error(
                "Entity create failed unexpectedly",
                code="entity_operations.create.unhandled_exception",
                details={
                    "entity_type": command.entity_type,
                    "catalog_id": self._catalog_id,
                    "catalog_version": None if catalog is None else catalog.catalog_version,
                },
                operation="entity_operations.create_entity",
                component="entity_operations",
                exc=exc,
            )
            await self._emit_failure(
                context=context,
                entity_type=command.entity_type,
                entity_ref=None,
                changed_fields=changed_fields,
                error=structured,
            )
            raise structured from exc

    async def edit_entity(
        self,
        *,
        context: EntityOperationContext,
        command: EditEntityCommand,
    ) -> EntityMutationResultView:
        changed_fields = tuple(sorted(command.changes))
        catalog: SemanticCatalogView | None = None
        try:
            catalog = self._catalogs.get_catalog(self._catalog_id)
            resolved = await self._refs.resolve_ref(
                entity_ref=command.entity_ref,
                required_operation="edit",
                context=context,
            )
            entity = self._catalogs.get_entity(catalog_id=self._catalog_id, entity_type=resolved.entity_type)
            self._require_edit_allowed(entity=entity)
            current = await self._require_current_snapshot(
                entity_type=resolved.entity_type,
                entity_id=resolved.entity_id,
                entity_ref=command.entity_ref,
            )
            if command.expected_version != current.version:
                raise app_error(
                    "Entity version does not match the current persisted version",
                    code="entity_operations.version_conflict",
                    category="validation",
                    status_code=409,
                    severity="warning",
                    details={
                        "entity_type": current.entity_type,
                        "entity_ref": command.entity_ref,
                        "expected_version": command.expected_version,
                        "current_version": current.version,
                    },
                    operation="entity_operations.edit_entity",
                    component="entity_operations",
                )
            validated = self._validate_edit_values(entity=entity, values=command.changes)
            updated = await self._executor.edit_entity(
                entity=entity,
                entity_id=current.entity_id,
                changes=validated,
            )
            issued_ref = self._refs.issue_ref(
                snapshot=updated,
                allowed_operations=self._allowed_operations(entity),
                ttl_seconds=entity.mutations.ref_ttl_seconds if entity.mutations is not None else 86_400,
                context=context,
            )
            record = MutationRecord(
                operation_id=new_id(),
                operation="edit",
                catalog_id=catalog.catalog_id,
                catalog_version=catalog.catalog_version,
                entity_type=updated.entity_type,
                entity_id=updated.entity_id,
                entity_ref=issued_ref.entity_ref,
                display_label=updated.display_label,
                version_before=current.version,
                version_after=updated.version,
                changed_fields=changed_fields,
                before_snapshot=dict(current.values),
                after_snapshot=dict(updated.values),
                undo_status="available",
                audit=self._audit_payload(context),
            )
            await self._records.save(record)
            await self._diagnostics.mutation_updated(context=context, record=record)
            return self._to_result(record=record, context=context)
        except AppError as exc:
            self._annotate_error(
                exc,
                catalog_id=self._catalog_id,
                catalog_version=None if catalog is None else catalog.catalog_version,
            )
            await self._emit_failure(
                context=context,
                entity_type=None,
                entity_ref=command.entity_ref,
                changed_fields=changed_fields,
                error=exc,
            )
            raise
        except Exception as exc:
            structured = internal_error(
                "Entity edit failed unexpectedly",
                code="entity_operations.edit.unhandled_exception",
                details={
                    "entity_ref": command.entity_ref,
                    "catalog_id": self._catalog_id,
                    "catalog_version": None if catalog is None else catalog.catalog_version,
                },
                operation="entity_operations.edit_entity",
                component="entity_operations",
                exc=exc,
            )
            await self._emit_failure(
                context=context,
                entity_type=None,
                entity_ref=command.entity_ref,
                changed_fields=changed_fields,
                error=structured,
            )
            raise structured from exc

    async def undo_mutation(
        self,
        *,
        context: EntityOperationContext,
        command: UndoEntityMutationCommand,
    ) -> EntityMutationResultView:
        record = await self._records.get(command.operation_id)
        if record is None:
            raise app_error(
                "Entity mutation record was not found",
                code="entity_operations.undo.not_found",
                category="validation",
                status_code=404,
                details={"operation_id": command.operation_id, "catalog_id": self._catalog_id},
                operation="entity_operations.undo_mutation",
                component="entity_operations",
            )
        if record.operation != "edit" or record.before_snapshot is None or record.undo_status != "available":
            error = app_error(
                "Undo is not available for this mutation",
                code="entity_operations.undo.unavailable",
                category="validation",
                status_code=409,
                severity="warning",
                details={
                    "operation_id": command.operation_id,
                    "undo_status": record.undo_status,
                    "catalog_id": record.catalog_id,
                    "catalog_version": record.catalog_version,
                },
                operation="entity_operations.undo_mutation",
                component="entity_operations",
            )
            await self._diagnostics.undo_unavailable(context=context, record=record, error=error)
            raise error
        current = await self._require_current_snapshot(
            entity_type=record.entity_type,
            entity_id=record.entity_id,
            entity_ref=record.entity_ref,
        )
        if current.version != record.version_after:
            error = app_error(
                "Undo cannot be applied because the entity has changed since the mutation completed",
                code="entity_operations.undo.conflict",
                category="validation",
                status_code=409,
                severity="warning",
                details={
                    "operation_id": command.operation_id,
                    "entity_type": record.entity_type,
                    "entity_ref": record.entity_ref,
                    "expected_version": record.version_after,
                    "current_version": current.version,
                    "catalog_id": record.catalog_id,
                    "catalog_version": record.catalog_version,
                },
                operation="entity_operations.undo_mutation",
                component="entity_operations",
            )
            await self._diagnostics.undo_conflicted(context=context, record=record, error=error)
            raise error
        entity = self._catalogs.get_entity(catalog_id=self._catalog_id, entity_type=record.entity_type)
        undo_changes = {
            name: value
            for name, value in record.before_snapshot.items()
            if name in entity.fields and entity.fields[name].mutations.write_policy == "editable"
        }
        restored = await self._executor.edit_entity(
            entity=entity,
            entity_id=record.entity_id,
            changes=undo_changes,
        )
        issued_ref = self._refs.issue_ref(
            snapshot=restored,
            allowed_operations=self._allowed_operations(entity),
            ttl_seconds=entity.mutations.ref_ttl_seconds if entity.mutations is not None else 86_400,
            context=context,
        )
        applied = MutationRecord(
            operation_id=new_id(),
            operation="edit",
            catalog_id=record.catalog_id,
            catalog_version=record.catalog_version,
            entity_type=record.entity_type,
            entity_id=record.entity_id,
            entity_ref=issued_ref.entity_ref,
            display_label=restored.display_label,
            version_before=current.version,
            version_after=restored.version,
            changed_fields=tuple(sorted(undo_changes)),
            before_snapshot=dict(current.values),
            after_snapshot=dict(restored.values),
            undo_status="applied",
            warnings=("Undo applied from a prior edit mutation record.",),
            audit=self._audit_payload(context),
        )
        await self._records.save(applied)
        await self._diagnostics.undo_applied(context=context, record=applied)
        return self._to_result(record=applied, context=context)

    def describe_catalog(self) -> SemanticCatalogView:
        return self._catalogs.get_catalog(self._catalog_id)

    def _require_create_allowed(self, *, entity: SemanticEntityView) -> None:
        mutations = entity.mutations
        if mutations is None or not mutations.create_allowed:
            raise app_error(
                "Create is not supported for this entity type",
                code="entity_operations.create.not_allowed",
                category="validation",
                status_code=400,
                severity="warning",
                details={"entity_type": entity.entity_type},
                operation="entity_operations.create_entity",
                component="entity_operations",
            )

    def _require_edit_allowed(self, *, entity: SemanticEntityView) -> None:
        mutations = entity.mutations
        if mutations is None or not mutations.edit_allowed:
            raise app_error(
                "Edit is not supported for this entity type",
                code="entity_operations.edit.not_allowed",
                category="validation",
                status_code=400,
                severity="warning",
                details={"entity_type": entity.entity_type},
                operation="entity_operations.edit_entity",
                component="entity_operations",
            )

    async def _require_current_snapshot(
        self,
        *,
        entity_type: str,
        entity_id: str,
        entity_ref: str,
    ) -> EntitySnapshot:
        current = await self._executor.get_entity(entity_type=entity_type, entity_id=entity_id)
        if current is None:
            raise app_error(
                "Entity referenced by the context ref no longer exists",
                code="entity_ref.unknown",
                category="validation",
                status_code=404,
                severity="warning",
                details={"entity_type": entity_type, "entity_ref": entity_ref},
                operation="entity_operations.require_current_snapshot",
                component="entity_operations",
            )
        return current

    def _validate_create_values(
        self,
        *,
        entity: SemanticEntityView,
        values: dict[str, ScalarValue],
    ) -> dict[str, ScalarValue]:
        validated = self._validate_field_values(
            entity=entity,
            values=values,
            mode="create",
            operation="entity_operations.create_entity",
        )
        missing_required = sorted(
            field.name
            for field in entity.fields.values()
            if field.mutations.required_on_create and (field.name not in validated or validated[field.name] is None)
        )
        if missing_required:
            raise app_error(
                "Create payload is missing required fields",
                code="entity_operations.create.missing_required_fields",
                category="validation",
                status_code=400,
                severity="warning",
                details={"entity_type": entity.entity_type, "missing_fields": missing_required},
                operation="entity_operations.create_entity",
                component="entity_operations",
            )
        return validated

    def _validate_edit_values(
        self,
        *,
        entity: SemanticEntityView,
        values: dict[str, ScalarValue],
    ) -> dict[str, ScalarValue]:
        return self._validate_field_values(
            entity=entity,
            values=values,
            mode="edit",
            operation="entity_operations.edit_entity",
        )

    def _validate_field_values(
        self,
        *,
        entity: SemanticEntityView,
        values: dict[str, ScalarValue],
        mode: str,
        operation: str,
    ) -> dict[str, ScalarValue]:
        validated: dict[str, ScalarValue] = {}
        for name, value in values.items():
            field = entity.fields.get(name)
            if field is None:
                raise app_error(
                    "Entity payload contains an unknown field",
                    code=f"entity_operations.{mode}.unknown_field",
                    category="validation",
                    status_code=400,
                    severity="warning",
                    details={"entity_type": entity.entity_type, "field_name": name},
                    operation=operation,
                    component="entity_operations",
                )
            self._validate_field_policy(entity=entity, field=field, mode=mode, operation=operation)
            if value is None and not field.nullable:
                raise app_error(
                    "Entity payload set a non-nullable field to null",
                    code=f"entity_operations.{mode}.null_not_allowed",
                    category="validation",
                    status_code=400,
                    severity="warning",
                    details={"entity_type": entity.entity_type, "field_name": name},
                    operation=operation,
                    component="entity_operations",
                )
            self._validate_field_type(entity=entity, field=field, value=value, mode=mode, operation=operation)
            validated[name] = value
        return validated

    def _validate_field_policy(
        self,
        *,
        entity: SemanticEntityView,
        field: SemanticFieldView,
        mode: str,
        operation: str,
    ) -> None:
        if field.sensitivity == "restricted":
            raise app_error(
                "Restricted fields cannot be mutated through generic entity tools",
                code=f"entity_operations.{mode}.sensitive_field_denied",
                category="validation",
                status_code=403,
                severity="warning",
                details={"entity_type": entity.entity_type, "field_name": field.name},
                operation=operation,
                component="entity_operations",
            )
        policy = field.mutations.write_policy
        allowed = {"editable"} if mode == "edit" else {"editable", "create_only"}
        if policy not in allowed:
            error_code = (
                f"entity_operations.{mode}.non_editable_field"
                if mode == "edit"
                else "entity_operations.create.field_not_creatable"
            )
            raise app_error(
                "Field is not writable for this operation",
                code=error_code,
                category="validation",
                status_code=400,
                severity="warning",
                details={
                    "entity_type": entity.entity_type,
                    "field_name": field.name,
                    "write_policy": policy,
                },
                operation=operation,
                component="entity_operations",
            )

    def _validate_field_type(
        self,
        *,
        entity: SemanticEntityView,
        field: SemanticFieldView,
        value: ScalarValue,
        mode: str,
        operation: str,
    ) -> None:
        if value is None:
            return
        is_valid = False
        if field.data_type == "text":
            is_valid = isinstance(value, str)
        elif field.data_type == "integer":
            is_valid = isinstance(value, int) and not isinstance(value, bool)
        elif field.data_type == "numeric":
            is_valid = (isinstance(value, int) and not isinstance(value, bool)) or isinstance(value, float)
        elif field.data_type == "boolean":
            is_valid = isinstance(value, bool)
        elif field.data_type in {"date", "datetime"}:
            is_valid = isinstance(value, str)
        else:
            is_valid = isinstance(value, (str, int, float, bool))
        if not is_valid:
            raise app_error(
                "Entity payload field type does not match the semantic schema",
                code=f"entity_operations.{mode}.invalid_field_type",
                category="validation",
                status_code=400,
                severity="warning",
                details={
                    "entity_type": entity.entity_type,
                    "field_name": field.name,
                    "data_type": field.data_type,
                    "value_type": type(value).__name__,
                },
                operation=operation,
                component="entity_operations",
            )

    async def _emit_failure(
        self,
        *,
        context: EntityOperationContext,
        entity_type: str | None,
        entity_ref: str | None,
        changed_fields: tuple[str, ...],
        error: AppError,
    ) -> None:
        if error.code in {"entity_ref.stale", "entity_operations.version_conflict"}:
            await self._diagnostics.stale_version(
                context=context,
                entity_type=entity_type,
                entity_ref=entity_ref,
                changed_fields=changed_fields,
                error=error,
            )
            return
        if error.category == "validation":
            await self._diagnostics.mutation_rejected(
                context=context,
                entity_type=entity_type,
                entity_ref=entity_ref,
                changed_fields=changed_fields,
                error=error,
            )
            return
        await self._diagnostics.mutation_failed(
            context=context,
            entity_type=entity_type,
            entity_ref=entity_ref,
            changed_fields=changed_fields,
            error=error,
        )

    def _to_result(
        self,
        *,
        record: MutationRecord,
        context: EntityOperationContext,
    ) -> EntityMutationResultView:
        return EntityMutationResultView(
            operation_id=record.operation_id,
            operation=record.operation,
            catalog_id=record.catalog_id,
            catalog_version=record.catalog_version,
            entity_ref=record.entity_ref,
            entity_type=record.entity_type,
            display_label=record.display_label,
            version=record.version_after,
            changed_fields=list(record.changed_fields),
            undo_status=record.undo_status,
            warnings=list(record.warnings),
            audit=EntityMutationAuditView.model_validate(context.model_dump(mode="json")),
        )

    @staticmethod
    def _allowed_operations(entity: SemanticEntityView) -> tuple[str, ...]:
        if entity.mutations is not None and entity.mutations.edit_allowed:
            return ("edit",)
        return ()

    @staticmethod
    def _audit_payload(context: EntityOperationContext) -> dict[str, str | None]:
        payload = context.model_dump(mode="json")
        return {key: payload.get(key) for key in sorted(payload)}

    @staticmethod
    def _annotate_error(error: AppError, *, catalog_id: str, catalog_version: str | None) -> None:
        error.details.setdefault("catalog_id", catalog_id)
        if catalog_version is not None:
            error.details.setdefault("catalog_version", catalog_version)
