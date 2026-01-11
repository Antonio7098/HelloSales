from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.http.dependencies import EnterpriseOrgContext, get_enterprise_org_context
from app.database import get_session
from app.domains.sailwind.playbook import (
    PlaybookConflictError,
    PlaybookNotFoundError,
    PlaybookService,
    PlaybookValidationError,
)
from app.domains.sailwind.practice import (
    PracticeConflictError,
    PracticeNotFoundError,
    PracticeSessionService,
    PracticeValidationError,
    TerritoryService,
)
from app.schemas.sailwind_playbook import (
    ClientArchetypeCreate,
    ClientArchetypeResponse,
    ClientArchetypeUpdate,
    ClientCreate,
    ClientResponse,
    ClientUpdate,
    ProductArchetypeCreate,
    ProductArchetypeResponse,
    ProductArchetypeUpdate,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
    StrategyResponse,
    StrategyUpdate,
    StrategyUpsert,
)
from app.schemas.sailwind_practice import (
    PracticeSessionCreate,
    PracticeSessionResponse,
    RepAssignmentCreate,
    RepAssignmentResponse,
)

logger = logging.getLogger("sailwind")

router = APIRouter(prefix="/api/v1/sailwind", tags=["sailwind"])


def _require_admin(org_context: EnterpriseOrgContext) -> None:
    membership = org_context.membership
    if membership.role != "admin":
        logger.info(
            "Sailwind playbook mutation denied (admin required)",
            extra={
                "service": "sailwind",
                "operation": "authz.playbook.mutate",
                "status": "denied",
                "user_id": str(membership.user_id),
                "organization_id": str(membership.organization_id),
                "role": membership.role,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Admin role required"},
        )


@router.get("/admin/placeholder")
async def sailwind_admin_placeholder(
    org_context: EnterpriseOrgContext = Depends(get_enterprise_org_context),
) -> dict[str, str]:
    membership = org_context.membership
    if membership.role != "admin":
        logger.info(
            "Sailwind admin placeholder denied",
            extra={
                "service": "sailwind",
                "operation": "authz.admin_placeholder",
                "status": "denied",
                "user_id": str(membership.user_id),
                "organization_id": str(membership.organization_id),
                "role": membership.role,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Admin role required"},
        )

    logger.info(
        "Sailwind admin placeholder allowed",
        extra={
            "service": "sailwind",
            "operation": "authz.admin_placeholder",
            "status": "allowed",
            "user_id": str(membership.user_id),
            "organization_id": str(membership.organization_id),
            "role": membership.role,
        },
    )
    return {"status": "ok"}


@router.get("/product-archetypes", response_model=list[ProductArchetypeResponse])
async def list_product_archetypes(
    include_archived: bool = False,
    org_context: EnterpriseOrgContext = Depends(get_enterprise_org_context),
    session: AsyncSession = Depends(get_session),
) -> list[ProductArchetypeResponse]:
    service = PlaybookService(session)
    archetypes = await service.list_product_archetypes(
        organization_id=org_context.organization.id,
        include_archived=include_archived,
    )
    return [ProductArchetypeResponse.model_validate(a) for a in archetypes]


@router.post("/product-archetypes", response_model=ProductArchetypeResponse)
async def create_product_archetype(
    payload: ProductArchetypeCreate,
    org_context: EnterpriseOrgContext = Depends(get_enterprise_org_context),
    session: AsyncSession = Depends(get_session),
) -> ProductArchetypeResponse:
    _require_admin(org_context)
    service = PlaybookService(session)
    try:
        created = await service.create_product_archetype(
            organization_id=org_context.organization.id,
            name=payload.name,
            user_id=org_context.membership.user_id,
        )
    except PlaybookConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT", "message": str(exc)},
        ) from exc
    return ProductArchetypeResponse.model_validate(created)


@router.patch("/product-archetypes/{archetype_id}", response_model=ProductArchetypeResponse)
async def update_product_archetype(
    archetype_id: str,
    payload: ProductArchetypeUpdate,
    org_context: EnterpriseOrgContext = Depends(get_enterprise_org_context),
    session: AsyncSession = Depends(get_session),
) -> ProductArchetypeResponse:
    _require_admin(org_context)
    service = PlaybookService(session)
    try:
        updated = await service.update_product_archetype(
            organization_id=org_context.organization.id,
            archetype_id=_parse_uuid(archetype_id),
            user_id=org_context.membership.user_id,
            name=payload.name,
            archived=payload.archived,
        )
    except PlaybookNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": str(exc)},
        ) from exc
    except PlaybookConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT", "message": str(exc)},
        ) from exc
    return ProductArchetypeResponse.model_validate(updated)


@router.get("/client-archetypes", response_model=list[ClientArchetypeResponse])
async def list_client_archetypes(
    include_archived: bool = False,
    org_context: EnterpriseOrgContext = Depends(get_enterprise_org_context),
    session: AsyncSession = Depends(get_session),
) -> list[ClientArchetypeResponse]:
    service = PlaybookService(session)
    archetypes = await service.list_client_archetypes(
        organization_id=org_context.organization.id,
        include_archived=include_archived,
    )
    return [ClientArchetypeResponse.model_validate(a) for a in archetypes]


@router.post("/client-archetypes", response_model=ClientArchetypeResponse)
async def create_client_archetype(
    payload: ClientArchetypeCreate,
    org_context: EnterpriseOrgContext = Depends(get_enterprise_org_context),
    session: AsyncSession = Depends(get_session),
) -> ClientArchetypeResponse:
    _require_admin(org_context)
    service = PlaybookService(session)
    try:
        created = await service.create_client_archetype(
            organization_id=org_context.organization.id,
            name=payload.name,
            industry=payload.industry,
            user_id=org_context.membership.user_id,
        )
    except PlaybookConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT", "message": str(exc)},
        ) from exc
    return ClientArchetypeResponse.model_validate(created)


@router.patch("/client-archetypes/{archetype_id}", response_model=ClientArchetypeResponse)
async def update_client_archetype(
    archetype_id: str,
    payload: ClientArchetypeUpdate,
    org_context: EnterpriseOrgContext = Depends(get_enterprise_org_context),
    session: AsyncSession = Depends(get_session),
) -> ClientArchetypeResponse:
    _require_admin(org_context)
    service = PlaybookService(session)
    try:
        updated = await service.update_client_archetype(
            organization_id=org_context.organization.id,
            archetype_id=_parse_uuid(archetype_id),
            user_id=org_context.membership.user_id,
            name=payload.name,
            industry=payload.industry,
            archived=payload.archived,
        )
    except PlaybookNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": str(exc)},
        ) from exc
    except PlaybookConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT", "message": str(exc)},
        ) from exc
    return ClientArchetypeResponse.model_validate(updated)


@router.get("/products", response_model=list[ProductResponse])
async def list_products(
    include_archived: bool = False,
    org_context: EnterpriseOrgContext = Depends(get_enterprise_org_context),
    session: AsyncSession = Depends(get_session),
) -> list[ProductResponse]:
    service = PlaybookService(session)
    products = await service.list_products(
        organization_id=org_context.organization.id,
        include_archived=include_archived,
    )
    return [ProductResponse.model_validate(p) for p in products]


@router.post("/products", response_model=ProductResponse)
async def create_product(
    payload: ProductCreate,
    org_context: EnterpriseOrgContext = Depends(get_enterprise_org_context),
    session: AsyncSession = Depends(get_session),
) -> ProductResponse:
    _require_admin(org_context)
    service = PlaybookService(session)
    try:
        created = await service.create_product(
            organization_id=org_context.organization.id,
            name=payload.name,
            product_archetype_id=payload.product_archetype_id,
            category=payload.category,
            price=payload.price,
            stock=payload.stock,
            status=payload.status,
            user_id=org_context.membership.user_id,
        )
    except PlaybookNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": str(exc)},
        ) from exc
    except PlaybookValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "BAD_REQUEST", "message": str(exc)},
        ) from exc
    return ProductResponse.model_validate(created)


@router.patch("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    payload: ProductUpdate,
    org_context: EnterpriseOrgContext = Depends(get_enterprise_org_context),
    session: AsyncSession = Depends(get_session),
) -> ProductResponse:
    _require_admin(org_context)
    service = PlaybookService(session)
    try:
        updated = await service.update_product(
            organization_id=org_context.organization.id,
            product_id=_parse_uuid(product_id),
            user_id=org_context.membership.user_id,
            name=payload.name,
            product_archetype_id=payload.product_archetype_id,
            product_archetype_id_provided=("product_archetype_id" in payload.model_fields_set),
            category=payload.category,
            price=payload.price,
            stock=payload.stock,
            status=payload.status,
            archived=payload.archived,
        )
    except PlaybookNotFoundError as exc:
        logger.info(
            "Playbook product not found",
            extra={
                "service": "sailwind",
                "operation": "playbook.product.update",
                "status": "not_found",
                "user_id": str(org_context.membership.user_id),
                "organization_id": str(org_context.organization.id),
                "entity_id": product_id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": str(exc)},
        ) from exc
    except PlaybookValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "BAD_REQUEST", "message": str(exc)},
        ) from exc
    return ProductResponse.model_validate(updated)


@router.get("/clients", response_model=list[ClientResponse])
async def list_clients(
    include_archived: bool = False,
    org_context: EnterpriseOrgContext = Depends(get_enterprise_org_context),
    session: AsyncSession = Depends(get_session),
) -> list[ClientResponse]:
    service = PlaybookService(session)
    clients = await service.list_clients(
        organization_id=org_context.organization.id,
        include_archived=include_archived,
    )
    return [ClientResponse.model_validate(c) for c in clients]


@router.post("/clients", response_model=ClientResponse)
async def create_client(
    payload: ClientCreate,
    org_context: EnterpriseOrgContext = Depends(get_enterprise_org_context),
    session: AsyncSession = Depends(get_session),
) -> ClientResponse:
    _require_admin(org_context)
    service = PlaybookService(session)
    try:
        created = await service.create_client(
            organization_id=org_context.organization.id,
            name=payload.name,
            industry=payload.industry,
            client_archetype_id=payload.client_archetype_id,
            user_id=org_context.membership.user_id,
        )
    except PlaybookNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": str(exc)},
        ) from exc
    except PlaybookValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "BAD_REQUEST", "message": str(exc)},
        ) from exc
    return ClientResponse.model_validate(created)


@router.patch("/clients/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: str,
    payload: ClientUpdate,
    org_context: EnterpriseOrgContext = Depends(get_enterprise_org_context),
    session: AsyncSession = Depends(get_session),
) -> ClientResponse:
    _require_admin(org_context)
    service = PlaybookService(session)
    try:
        updated = await service.update_client(
            organization_id=org_context.organization.id,
            client_id=_parse_uuid(client_id),
            user_id=org_context.membership.user_id,
            name=payload.name,
            industry=payload.industry,
            client_archetype_id=payload.client_archetype_id,
            client_archetype_id_provided=("client_archetype_id" in payload.model_fields_set),
            email=payload.email,
            phone=payload.phone,
            company=payload.company,
            status=payload.status,
            total_revenue=payload.total_revenue,
            archived=payload.archived,
        )
    except PlaybookNotFoundError as exc:
        logger.info(
            "Playbook client not found",
            extra={
                "service": "sailwind",
                "operation": "playbook.client.update",
                "status": "not_found",
                "user_id": str(org_context.membership.user_id),
                "organization_id": str(org_context.organization.id),
                "entity_id": client_id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": str(exc)},
        ) from exc
    except PlaybookValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "BAD_REQUEST", "message": str(exc)},
        ) from exc
    return ClientResponse.model_validate(updated)


@router.get("/strategies", response_model=list[StrategyResponse])
async def list_strategies(
    include_archived: bool = False,
    org_context: EnterpriseOrgContext = Depends(get_enterprise_org_context),
    session: AsyncSession = Depends(get_session),
) -> list[StrategyResponse]:
    service = PlaybookService(session)
    strategies = await service.list_strategies(
        organization_id=org_context.organization.id,
        include_archived=include_archived,
    )
    return [StrategyResponse.model_validate(s) for s in strategies]


@router.post("/strategies", response_model=StrategyResponse)
async def create_strategy(
    payload: StrategyUpsert,
    org_context: EnterpriseOrgContext = Depends(get_enterprise_org_context),
    session: AsyncSession = Depends(get_session),
) -> StrategyResponse:
    _require_admin(org_context)
    service = PlaybookService(session)
    try:
        created = await service.create_strategy(
            organization_id=org_context.organization.id,
            product_id=payload.product_id,
            client_id=payload.client_id,
            strategy_text=payload.strategy_text,
            status=payload.status,
            user_id=org_context.membership.user_id,
        )
    except PlaybookNotFoundError as exc:
        logger.info(
            "Playbook strategy create referenced missing entity",
            extra={
                "service": "sailwind",
                "operation": "playbook.strategy.create",
                "status": "not_found",
                "user_id": str(org_context.membership.user_id),
                "organization_id": str(org_context.organization.id),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": str(exc)},
        ) from exc
    except PlaybookConflictError as exc:
        logger.info(
            "Playbook strategy create conflict",
            extra={
                "service": "sailwind",
                "operation": "playbook.strategy.create",
                "status": "conflict",
                "user_id": str(org_context.membership.user_id),
                "organization_id": str(org_context.organization.id),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT", "message": str(exc)},
        ) from exc
    except PlaybookValidationError as exc:
        logger.info(
            "Playbook strategy create validation error",
            extra={
                "service": "sailwind",
                "operation": "playbook.strategy.create",
                "status": "bad_request",
                "user_id": str(org_context.membership.user_id),
                "organization_id": str(org_context.organization.id),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "BAD_REQUEST", "message": str(exc)},
        ) from exc
    return StrategyResponse.model_validate(created)


@router.patch("/strategies/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: str,
    payload: StrategyUpdate,
    org_context: EnterpriseOrgContext = Depends(get_enterprise_org_context),
    session: AsyncSession = Depends(get_session),
) -> StrategyResponse:
    _require_admin(org_context)
    service = PlaybookService(session)
    try:
        updated = await service.update_strategy(
            organization_id=org_context.organization.id,
            strategy_id=_parse_uuid(strategy_id),
            user_id=org_context.membership.user_id,
            strategy_text=payload.strategy_text,
            status=payload.status,
        )
    except PlaybookNotFoundError as exc:
        logger.info(
            "Playbook strategy not found",
            extra={
                "service": "sailwind",
                "operation": "playbook.strategy.update",
                "status": "not_found",
                "user_id": str(org_context.membership.user_id),
                "organization_id": str(org_context.organization.id),
                "entity_id": strategy_id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": str(exc)},
        ) from exc
    except PlaybookValidationError as exc:
        logger.info(
            "Playbook strategy validation error",
            extra={
                "service": "sailwind",
                "operation": "playbook.strategy.update",
                "status": "bad_request",
                "user_id": str(org_context.membership.user_id),
                "organization_id": str(org_context.organization.id),
                "entity_id": strategy_id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "BAD_REQUEST", "message": str(exc)},
        ) from exc
    return StrategyResponse.model_validate(updated)


@router.get("/rep-assignments", response_model=list[RepAssignmentResponse])
async def list_rep_assignments(
    org_context: EnterpriseOrgContext = Depends(get_enterprise_org_context),
    session: AsyncSession = Depends(get_session),
) -> list[RepAssignmentResponse]:
    _require_admin(org_context)
    service = TerritoryService(session)
    assignments = await service.list_rep_assignments(organization_id=org_context.organization.id)
    return [RepAssignmentResponse.model_validate(a) for a in assignments]


@router.post("/rep-assignments", response_model=RepAssignmentResponse)
async def create_rep_assignment(
    payload: RepAssignmentCreate,
    org_context: EnterpriseOrgContext = Depends(get_enterprise_org_context),
    session: AsyncSession = Depends(get_session),
) -> RepAssignmentResponse:
    _require_admin(org_context)
    service = TerritoryService(session)
    try:
        created = await service.create_rep_assignment(
            organization_id=org_context.organization.id,
            user_id=payload.user_id,
            product_id=payload.product_id,
            client_id=payload.client_id,
            strategy_id=payload.strategy_id,
            min_practice_minutes=payload.min_practice_minutes,
            actor_user_id=org_context.membership.user_id,
        )
    except PracticeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": str(exc)},
        ) from exc
    except PracticeConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT", "message": str(exc)},
        ) from exc
    except PracticeValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "BAD_REQUEST", "message": str(exc)},
        ) from exc
    return RepAssignmentResponse.model_validate(created)


@router.get("/my/rep-assignments", response_model=list[RepAssignmentResponse])
async def list_my_rep_assignments(
    org_context: EnterpriseOrgContext = Depends(get_enterprise_org_context),
    session: AsyncSession = Depends(get_session),
) -> list[RepAssignmentResponse]:
    service = TerritoryService(session)
    assignments = await service.list_rep_assignments_for_user(
        organization_id=org_context.organization.id,
        user_id=org_context.membership.user_id,
    )
    return [RepAssignmentResponse.model_validate(a) for a in assignments]


@router.post("/practice-sessions", response_model=PracticeSessionResponse)
async def start_practice_session(
    payload: PracticeSessionCreate,
    org_context: EnterpriseOrgContext = Depends(get_enterprise_org_context),
    session: AsyncSession = Depends(get_session),
) -> PracticeSessionResponse:
    service = PracticeSessionService(session)
    try:
        created = await service.start_practice_session(
            organization_id=org_context.organization.id,
            user_id=org_context.membership.user_id,
            strategy_id=payload.strategy_id,
            rep_assignment_id=payload.rep_assignment_id,
            actor_user_id=org_context.membership.user_id,
        )
    except PracticeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": str(exc)},
        ) from exc
    except PracticeValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "BAD_REQUEST", "message": str(exc)},
        ) from exc
    return PracticeSessionResponse.model_validate(created)


@router.get("/my/practice-sessions", response_model=list[PracticeSessionResponse])
async def list_my_practice_sessions(
    limit: int = 50,
    org_context: EnterpriseOrgContext = Depends(get_enterprise_org_context),
    session: AsyncSession = Depends(get_session),
) -> list[PracticeSessionResponse]:
    service = PracticeSessionService(session)
    sessions = await service.list_practice_sessions_for_user(
        organization_id=org_context.organization.id,
        user_id=org_context.membership.user_id,
        limit=limit,
    )
    return [PracticeSessionResponse.model_validate(s) for s in sessions]


def _parse_uuid(value: str):
    from uuid import UUID

    try:
        return UUID(value)
    except ValueError as exc:
        logger.info(
            "Playbook invalid id",
            extra={
                "service": "sailwind",
                "operation": "playbook.parse_id",
                "status": "bad_request",
                "entity_id": value,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "BAD_REQUEST", "message": "Invalid id"},
        ) from exc
