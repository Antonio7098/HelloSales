"""SQLAlchemy repository for company profile data."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hello_sales_backend.modules.company_profile.use_cases.ports import CompanyProfileRepositoryPort
from hello_sales_backend.modules.company_profile.use_cases.views import (
    CompanyProfileUpsertRequest,
    CompanyProfileView,
    ProductCreateRequest,
    ProductUpdateRequest,
    ProductView,
)
from hello_sales_backend.platform.db.models import CompanyProfileRecord, ProductRecord


def _now() -> datetime:
    return datetime.now(UTC)


def _profile_view(record: CompanyProfileRecord) -> CompanyProfileView:
    return CompanyProfileView(
        profile_id=record.profile_id,
        company_name=record.company_name,
        industry=record.industry,
        target_customer=record.target_customer,
        pricing_model=record.pricing_model,
        sales_team_size=record.sales_team_size,
        crm_tool=record.crm_tool,
        average_deal_size=record.average_deal_size,
        average_sales_cycle=record.average_sales_cycle,
        primary_sales_constraint=record.primary_sales_constraint,
        quarterly_sales_focus=record.quarterly_sales_focus,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _product_view(record: ProductRecord) -> ProductView:
    return ProductView(
        product_id=record.product_id,
        company_profile_id=record.company_profile_id,
        product_name=record.product_name,
        product_description=record.product_description,
        target_customer=record.target_customer,
        primary_use_case=record.primary_use_case,
        pricing_model=record.pricing_model,
        list_price=record.list_price,
        sales_cycle=record.sales_cycle,
        deal_size=record.deal_size,
        revenue_share=record.revenue_share,
        is_primary=record.is_primary,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


class SqlAlchemyCompanyProfileRepository(CompanyProfileRepositoryPort):
    """Persist and read company profile data."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_company_profile(self) -> CompanyProfileView | None:
        async with self._session_factory() as session:
            record = await self._get_profile_record(session)
            return _profile_view(record) if record else None

    async def upsert_company_profile(self, request: CompanyProfileUpsertRequest) -> CompanyProfileView:
        async with self._session_factory() as session:
            timestamp = _now()
            record = await self._get_profile_record(session)
            if record is None:
                record = CompanyProfileRecord(
                    profile_id=uuid4().hex,
                    created_at=timestamp,
                    updated_at=timestamp,
                    **request.model_dump(),
                )
                session.add(record)
            else:
                for field, value in request.model_dump().items():
                    setattr(record, field, value)
                record.updated_at = timestamp
            await session.commit()
            await session.refresh(record)
            return _profile_view(record)

    async def list_products(self) -> list[ProductView]:
        async with self._session_factory() as session:
            records = list(await session.scalars(select(ProductRecord).order_by(ProductRecord.created_at)))
            return [_product_view(record) for record in records]

    async def get_product(self, product_id: str) -> ProductView | None:
        async with self._session_factory() as session:
            record = await session.get(ProductRecord, product_id)
            return _product_view(record) if record else None

    async def create_product(self, request: ProductCreateRequest) -> ProductView:
        async with self._session_factory() as session:
            profile = await self._get_profile_record(session)
            if profile is None:
                raise RuntimeError("company profile is required before products can be created")
            timestamp = _now()
            record = ProductRecord(
                product_id=uuid4().hex,
                company_profile_id=profile.profile_id,
                created_at=timestamp,
                updated_at=timestamp,
                **request.model_dump(),
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return _product_view(record)

    async def update_product(self, product_id: str, request: ProductUpdateRequest) -> ProductView | None:
        async with self._session_factory() as session:
            record = await session.get(ProductRecord, product_id)
            if record is None:
                return None
            for field, value in request.model_dump(exclude_unset=True).items():
                setattr(record, field, value)
            record.updated_at = _now()
            await session.commit()
            await session.refresh(record)
            return _product_view(record)

    async def delete_product(self, product_id: str) -> bool:
        async with self._session_factory() as session:
            record = await session.get(ProductRecord, product_id)
            if record is None:
                return False
            await session.execute(delete(ProductRecord).where(ProductRecord.product_id == product_id))
            await session.commit()
            return True

    @staticmethod
    async def _get_profile_record(session: AsyncSession) -> CompanyProfileRecord | None:
        record: CompanyProfileRecord | None = await session.scalar(
            select(CompanyProfileRecord).order_by(CompanyProfileRecord.created_at).limit(1)
        )
        return record
