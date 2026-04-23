"""Company-profile-backed generic entity executor."""

from __future__ import annotations

from hello_sales_backend.modules.company_profile import (
    CompanyProfileService,
    CompanyProfileUpsertRequest,
    CompanyProfileView,
    ProductCreateRequest,
    ProductUpdateRequest,
    ProductView,
)
from hello_sales_backend.modules.entity_operations.use_cases.commands import ScalarValue
from hello_sales_backend.modules.entity_operations.use_cases.ports import (
    EntityMutationExecutorPort,
    EntitySnapshot,
)
from hello_sales_backend.modules.semantic_catalog.use_cases.views import SemanticEntityView
from hello_sales_backend.shared.errors import AppError, app_error


def _company_profile_snapshot(view: CompanyProfileView) -> EntitySnapshot:
    payload = view.model_dump(mode="json")
    entity_id = str(payload.pop("profile_id"))
    payload.pop("created_at", None)
    updated_at = str(payload.pop("updated_at"))
    return EntitySnapshot(
        entity_type="company_profile",
        entity_id=entity_id,
        version=updated_at,
        display_label=view.company_name,
        values=payload,
    )


def _product_snapshot(view: ProductView) -> EntitySnapshot:
    payload = view.model_dump(mode="json")
    entity_id = str(payload.pop("product_id"))
    payload.pop("created_at", None)
    updated_at = str(payload.pop("updated_at"))
    return EntitySnapshot(
        entity_type="product",
        entity_id=entity_id,
        version=updated_at,
        display_label=view.product_name,
        values=payload,
    )


class CompanyProfileEntityMutationExecutor(EntityMutationExecutorPort):
    """Persist generic entity operations through the company-profile module."""

    def __init__(self, *, company_profiles: CompanyProfileService) -> None:
        self._company_profiles = company_profiles

    async def get_entity(self, *, entity_type: str, entity_id: str) -> EntitySnapshot | None:
        if entity_type == "company_profile":
            profile = await self._company_profiles.get_company_profile()
            if profile is None or profile.profile_id != entity_id:
                return None
            return _company_profile_snapshot(profile)
        if entity_type == "product":
            try:
                product = await self._company_profiles.get_product(entity_id)
            except AppError as exc:
                if exc.code == "product.not_found":
                    return None
                raise
            return _product_snapshot(product)
        return None

    async def create_entity(
        self,
        *,
        entity: SemanticEntityView,
        values: dict[str, ScalarValue],
    ) -> EntitySnapshot:
        if entity.entity_type == "company_profile":
            existing = await self._company_profiles.get_company_profile()
            if existing is not None and entity.mutations is not None and entity.mutations.create_requires_absence:
                raise app_error(
                    "Company profile already exists and cannot be created again",
                    code="entity_operations.create.already_exists",
                    category="validation",
                    status_code=409,
                    severity="warning",
                    details={"entity_type": entity.entity_type},
                    operation="entity_operations.executor.create_entity",
                    component="entity_operations",
                )
            request = CompanyProfileUpsertRequest.model_validate(values)
            return _company_profile_snapshot(await self._company_profiles.upsert_company_profile(request))
        if entity.entity_type == "product":
            request = ProductCreateRequest.model_validate(values)
            return _product_snapshot(await self._company_profiles.create_product(request))
        raise app_error(
            "Entity type is not supported by the current mutation executor",
            code="entity_operations.executor.unsupported_entity",
            category="validation",
            status_code=400,
            severity="warning",
            details={"entity_type": entity.entity_type},
            operation="entity_operations.executor.create_entity",
            component="entity_operations",
        )

    async def edit_entity(
        self,
        *,
        entity: SemanticEntityView,
        entity_id: str,
        changes: dict[str, ScalarValue],
    ) -> EntitySnapshot:
        if entity.entity_type == "company_profile":
            current = await self._company_profiles.get_company_profile()
            if current is None or current.profile_id != entity_id:
                raise app_error(
                    "Company profile was not found for edit",
                    code="entity_operations.edit.not_found",
                    category="not_found",
                    status_code=404,
                    severity="warning",
                    details={"entity_type": entity.entity_type, "entity_id": entity_id},
                    operation="entity_operations.executor.edit_entity",
                    component="entity_operations",
                )
            current_values = current.model_dump(mode="json")
            current_values.pop("profile_id", None)
            current_values.pop("created_at", None)
            current_values.pop("updated_at", None)
            merged = {**current_values, **changes}
            request = CompanyProfileUpsertRequest.model_validate(merged)
            return _company_profile_snapshot(await self._company_profiles.upsert_company_profile(request))
        if entity.entity_type == "product":
            request = ProductUpdateRequest.model_validate(changes)
            return _product_snapshot(await self._company_profiles.update_product(entity_id, request))
        raise app_error(
            "Entity type is not supported by the current mutation executor",
            code="entity_operations.executor.unsupported_entity",
            category="validation",
            status_code=400,
            severity="warning",
            details={"entity_type": entity.entity_type},
            operation="entity_operations.executor.edit_entity",
            component="entity_operations",
        )
