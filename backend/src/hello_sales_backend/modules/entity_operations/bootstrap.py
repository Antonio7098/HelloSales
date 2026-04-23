"""Entity operations module assembly."""

from __future__ import annotations

from dataclasses import dataclass

from hello_sales_backend.modules.company_profile import CompanyProfileService
from hello_sales_backend.modules.entity_operations.infra.company_profile_executor import (
    CompanyProfileEntityMutationExecutor,
)
from hello_sales_backend.modules.entity_operations.infra.context_refs import (
    SignedContextEntityRefResolver,
)
from hello_sales_backend.modules.entity_operations.infra.mutation_store import (
    InMemoryMutationRecordStore,
)
from hello_sales_backend.modules.entity_operations.infra.observability import (
    EntityOperationsObservabilityAdapter,
)
from hello_sales_backend.modules.entity_operations.use_cases.entity_operations_service import (
    EntityOperationsService,
)
from hello_sales_backend.modules.semantic_catalog import SemanticCatalogService
from hello_sales_backend.platform.config.settings import Settings
from hello_sales_backend.platform.observability.runtime import ObservabilityRuntime


@dataclass(slots=True)
class EntityOperationsModule:
    """Resolved entity-operations module bundle."""

    service: EntityOperationsService


def build_entity_operations_module(
    *,
    settings: Settings,
    semantic_catalogs: SemanticCatalogService,
    company_profiles: CompanyProfileService,
    observability: ObservabilityRuntime,
) -> EntityOperationsModule:
    """Build the entity-operations module."""

    executor = CompanyProfileEntityMutationExecutor(company_profiles=company_profiles)
    return EntityOperationsModule(
        service=EntityOperationsService(
            catalog_id=settings.semantic_catalog_default_id,
            catalogs=semantic_catalogs,
            refs=SignedContextEntityRefResolver(
                executor=executor,
                signing_secret=settings.entity_ref_signing_secret,
            ),
            executor=executor,
            records=InMemoryMutationRecordStore(),
            diagnostics=EntityOperationsObservabilityAdapter(observability=observability),
        )
    )
