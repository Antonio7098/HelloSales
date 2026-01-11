"""Products API endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.product import Product
from app.infrastructure.auth.context import AuthContext, get_auth
from app.infrastructure.database.connection import get_db
from app.infrastructure.repositories.product_repository import ProductRepositoryImpl
from app.infrastructure.telemetry import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/products", tags=["products"])


# Request/Response models
class CreateProductRequest(BaseModel):
    """Request to create a product."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    category: str | None = None
    key_features: list[str] = Field(default_factory=list)
    target_audience: str | None = None
    pricing_info: str | None = None
    competitors: list[str] = Field(default_factory=list)
    differentiators: list[str] = Field(default_factory=list)


class UpdateProductRequest(BaseModel):
    """Request to update a product."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    category: str | None = None
    key_features: list[str] | None = None
    target_audience: str | None = None
    pricing_info: str | None = None
    competitors: list[str] | None = None
    differentiators: list[str] | None = None


class ProductResponse(BaseModel):
    """Product response."""

    id: UUID
    org_id: UUID
    name: str
    description: str | None
    category: str | None
    key_features: list[str]
    target_audience: str | None
    pricing_info: str | None
    competitors: list[str]
    differentiators: list[str]
    is_active: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


# Endpoints
@router.post("", response_model=ProductResponse)
async def create_product(
    request: CreateProductRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_auth),
) -> ProductResponse:
    """Create a new product."""
    if not auth.org_id:
        raise HTTPException(status_code=400, detail="Organization required")

    from uuid import uuid4

    product = Product(
        id=uuid4(),
        org_id=auth.org_id,
        name=request.name,
        description=request.description,
        category=request.category,
        key_features=request.key_features,
        target_audience=request.target_audience,
        pricing_info=request.pricing_info,
        competitors=request.competitors,
        differentiators=request.differentiators,
    )

    repo = ProductRepositoryImpl(db)
    created = await repo.create(product)

    logger.info(
        "Product created",
        extra={"product_id": str(created.id), "org_id": str(auth.org_id)},
    )

    return _product_to_response(created)


@router.get("", response_model=list[ProductResponse])
async def list_products(
    category: str | None = None,
    active_only: bool = True,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_auth),
) -> list[ProductResponse]:
    """List products for the organization."""
    if not auth.org_id:
        raise HTTPException(status_code=400, detail="Organization required")

    repo = ProductRepositoryImpl(db)
    products = await repo.list_by_org(
        auth.org_id,
        active_only=active_only,
        category=category,
        limit=limit,
        offset=offset,
    )

    return [_product_to_response(p) for p in products]


@router.get("/search", response_model=list[ProductResponse])
async def search_products(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_auth),
) -> list[ProductResponse]:
    """Search products by name or description."""
    if not auth.org_id:
        raise HTTPException(status_code=400, detail="Organization required")

    repo = ProductRepositoryImpl(db)
    products = await repo.search(auth.org_id, q, limit=limit)

    return [_product_to_response(p) for p in products]


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_auth),
) -> ProductResponse:
    """Get a product by ID."""
    if not auth.org_id:
        raise HTTPException(status_code=400, detail="Organization required")

    repo = ProductRepositoryImpl(db)
    product = await repo.get_by_id(product_id, auth.org_id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return _product_to_response(product)


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID,
    request: UpdateProductRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_auth),
) -> ProductResponse:
    """Update a product."""
    if not auth.org_id:
        raise HTTPException(status_code=400, detail="Organization required")

    repo = ProductRepositoryImpl(db)
    product = await repo.get_by_id(product_id, auth.org_id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Update fields
    if request.name is not None:
        product.name = request.name
    if request.description is not None:
        product.description = request.description
    if request.category is not None:
        product.category = request.category
    if request.key_features is not None:
        product.key_features = request.key_features
    if request.target_audience is not None:
        product.target_audience = request.target_audience
    if request.pricing_info is not None:
        product.pricing_info = request.pricing_info
    if request.competitors is not None:
        product.competitors = request.competitors
    if request.differentiators is not None:
        product.differentiators = request.differentiators

    updated = await repo.update(product)

    logger.info(
        "Product updated",
        extra={"product_id": str(product_id), "org_id": str(auth.org_id)},
    )

    return _product_to_response(updated)


@router.delete("/{product_id}")
async def delete_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_auth),
) -> dict[str, bool]:
    """Delete (deactivate) a product."""
    if not auth.org_id:
        raise HTTPException(status_code=400, detail="Organization required")

    repo = ProductRepositoryImpl(db)
    deleted = await repo.delete(product_id, auth.org_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Product not found")

    logger.info(
        "Product deleted",
        extra={"product_id": str(product_id), "org_id": str(auth.org_id)},
    )

    return {"deleted": True}


def _product_to_response(product: Product) -> ProductResponse:
    """Convert product entity to response model."""
    return ProductResponse(
        id=product.id,
        org_id=product.org_id,
        name=product.name,
        description=product.description,
        category=product.category,
        key_features=product.key_features,
        target_audience=product.target_audience,
        pricing_info=product.pricing_info,
        competitors=product.competitors,
        differentiators=product.differentiators,
        is_active=product.is_active,
        created_at=product.created_at.isoformat(),
        updated_at=product.updated_at.isoformat(),
    )
