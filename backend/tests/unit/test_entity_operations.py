from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from hello_sales_backend.modules.entity_operations.infra.context_refs import (
    SignedContextEntityRefResolver,
)
from hello_sales_backend.modules.entity_operations.infra.mutation_store import (
    InMemoryMutationRecordStore,
)
from hello_sales_backend.modules.entity_operations.use_cases.commands import (
    CreateEntityCommand,
    EditEntityCommand,
    UndoEntityMutationCommand,
)
from hello_sales_backend.modules.entity_operations.use_cases.entity_operations_service import (
    EntityOperationsService,
)
from hello_sales_backend.modules.entity_operations.use_cases.ports import (
    EntitySnapshot,
)
from hello_sales_backend.modules.entity_operations.use_cases.views import (
    EntityOperationContext,
)
from hello_sales_backend.modules.semantic_catalog.infra.catalogs import (
    YamlSemanticCatalogStore,
)
from hello_sales_backend.modules.semantic_catalog.use_cases.semantic_catalog_service import (
    SemanticCatalogService,
)
from hello_sales_backend.shared.errors import AppError


def _catalog_service() -> SemanticCatalogService:
    catalog_dir = Path(__file__).resolve().parents[2] / "catalogs" / "semantic"
    return SemanticCatalogService(catalogs=YamlSemanticCatalogStore(catalog_dir))


class FakeExecutor:
    def __init__(self) -> None:
        self.snapshots: dict[tuple[str, str], EntitySnapshot] = {
            (
                "company_profile",
                "profile-1",
            ): EntitySnapshot(
                entity_type="company_profile",
                entity_id="profile-1",
                version="v1",
                display_label="HelloSales",
                values={
                    "company_name": "HelloSales",
                    "industry": "B2B SaaS",
                    "target_customer": "SMB teams",
                    "pricing_model": "Subscription",
                    "sales_team_size": 5,
                    "crm_tool": "HubSpot",
                    "average_deal_size": "$3k-$10k",
                    "average_sales_cycle": "30-45 days",
                    "primary_sales_constraint": "Messaging",
                    "quarterly_sales_focus": "Close rate",
                },
            )
        }
        self.counter = 2

    async def get_entity(self, *, entity_type: str, entity_id: str) -> EntitySnapshot | None:
        return self.snapshots.get((entity_type, entity_id))

    async def create_entity(self, *, entity, values):  # noqa: ANN001
        entity_id = f"{entity.entity_type}-{self.counter}"
        snapshot = EntitySnapshot(
            entity_type=entity.entity_type,
            entity_id=entity_id,
            version=f"v{self.counter}",
            display_label=str(values.get(entity.display.label_field, entity_id)),
            values=dict(values),
        )
        self.snapshots[(entity.entity_type, entity_id)] = snapshot
        self.counter += 1
        return snapshot

    async def edit_entity(self, *, entity, entity_id: str, changes):  # noqa: ANN001
        current = self.snapshots[(entity.entity_type, entity_id)]
        snapshot = EntitySnapshot(
            entity_type=current.entity_type,
            entity_id=current.entity_id,
            version=f"v{self.counter}",
            display_label=str(changes.get(entity.display.label_field, current.display_label)),
            values={**current.values, **changes},
        )
        self.snapshots[(entity.entity_type, entity_id)] = snapshot
        self.counter += 1
        return snapshot


class NoopDiagnostics:
    async def mutation_created(self, **kwargs):  # noqa: ANN003
        del kwargs

    async def mutation_updated(self, **kwargs):  # noqa: ANN003
        del kwargs

    async def mutation_rejected(self, **kwargs):  # noqa: ANN003
        del kwargs

    async def stale_version(self, **kwargs):  # noqa: ANN003
        del kwargs

    async def mutation_failed(self, **kwargs):  # noqa: ANN003
        del kwargs

    async def undo_applied(self, **kwargs):  # noqa: ANN003
        del kwargs

    async def undo_conflicted(self, **kwargs):  # noqa: ANN003
        del kwargs

    async def undo_unavailable(self, **kwargs):  # noqa: ANN003
        del kwargs


def _context(session_id: str = "session-1") -> EntityOperationContext:
    return EntityOperationContext(
        request_id="req-1",
        trace_id="trace-1",
        actor_id="actor-1",
        session_id=session_id,
        run_id="run-1",
        turn_id="turn-1",
        tool_call_id="tool-1",
    )


def _service(executor: FakeExecutor, store: InMemoryMutationRecordStore) -> EntityOperationsService:
    catalogs = _catalog_service()
    return EntityOperationsService(
        catalog_id="scaffold_stage",
        catalogs=catalogs,
        refs=SignedContextEntityRefResolver(executor=executor, signing_secret="test-secret"),
        executor=executor,
        records=store,
        diagnostics=NoopDiagnostics(),
    )


@pytest.mark.asyncio
async def test_create_entity_rejects_missing_required_fields() -> None:
    store = InMemoryMutationRecordStore()
    service = _service(FakeExecutor(), store)

    with pytest.raises(AppError) as exc_info:
        await service.create_entity(
            context=_context(),
            command=CreateEntityCommand(
                entity_type="company_profile",
                values={"industry": "B2B SaaS"},
                reason="Create the company profile",
            ),
        )

    assert exc_info.value.code == "entity_operations.create.missing_required_fields"


@pytest.mark.asyncio
async def test_context_entity_ref_rejects_wrong_session_and_stale_versions() -> None:
    executor = FakeExecutor()
    resolver = SignedContextEntityRefResolver(executor=executor, signing_secret="test-secret")
    snapshot = executor.snapshots[("company_profile", "profile-1")]
    issued = resolver.issue_ref(
        snapshot=snapshot,
        allowed_operations=("edit",),
        ttl_seconds=3600,
        context=_context("session-1"),
    )

    with pytest.raises(AppError) as wrong_session:
        await resolver.resolve_ref(
            entity_ref=issued.entity_ref,
            required_operation="edit",
            context=_context("session-2"),
        )
    assert wrong_session.value.code == "entity_ref.wrong_session"

    executor.snapshots[("company_profile", "profile-1")] = replace(snapshot, version="v2")

    with pytest.raises(AppError) as stale:
        await resolver.resolve_ref(
            entity_ref=issued.entity_ref,
            required_operation="edit",
            context=_context("session-1"),
        )
    assert stale.value.code == "entity_ref.stale"


@pytest.mark.asyncio
async def test_edit_entity_returns_undo_available_and_undo_conflicts_when_version_moves() -> None:
    executor = FakeExecutor()
    store = InMemoryMutationRecordStore()
    service = _service(executor, store)
    issued = service._refs.issue_ref(  # noqa: SLF001
        snapshot=executor.snapshots[("company_profile", "profile-1")],
        allowed_operations=("edit",),
        ttl_seconds=3600,
        context=_context(),
    )

    result = await service.edit_entity(
        context=_context(),
        command=EditEntityCommand(
            entity_ref=issued.entity_ref,
            changes={"quarterly_sales_focus": "Pipeline quality"},
            expected_version="v1",
            reason="Update the current focus",
        ),
    )

    assert result.undo_status == "available"
    assert result.changed_fields == ["quarterly_sales_focus"]

    current = executor.snapshots[("company_profile", "profile-1")]
    executor.snapshots[("company_profile", "profile-1")] = replace(current, version="v99")

    with pytest.raises(AppError) as exc_info:
        await service.undo_mutation(
            context=_context(),
            command=UndoEntityMutationCommand(operation_id=result.operation_id),
        )

    assert exc_info.value.code == "entity_operations.undo.conflict"
