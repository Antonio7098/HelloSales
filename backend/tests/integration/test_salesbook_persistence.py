from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from hello_sales_backend.modules.salesbook.domain.exceptions import UnknownCommentError, UnknownDealError
from hello_sales_backend.modules.salesbook.infra.repository import (
    SqlAlchemySalesbookClientContactRepository,
    SqlAlchemySalesbookCommentRepository,
    SqlAlchemySalesbookEngagementRepository,
    SqlAlchemySalesbookOnboardingRepository,
    SqlAlchemySalesbookPinRepository,
    SqlAlchemySalesbookPipelineRepository,
    SqlAlchemySalesbookTeamMembershipRepository,
)
from hello_sales_backend.modules.salesbook.use_cases.views import (
    ClientContactUpsertRequest,
    EngagementLogCreateRequest,
    OnboardingResponseSubmit,
    PipelineDealCreateRequest,
    PipelineDealUpdateRequest,
    SalesbookCommentCreateRequest,
    SalesbookPinRequest,
    TeamMembershipCreateRequest,
)
from hello_sales_backend.platform.db.base import Base
from hello_sales_backend.platform.db.models import CompanyProfileRecord


@pytest_asyncio.fixture()
async def session_factory(tmp_path) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'salesbook-persistence.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        session.add(
            CompanyProfileRecord(
                profile_id="profile-1",
                company_name="Acme Inc.",
                industry="Software",
                target_customer="SMB",
                pricing_model="Subscription",
                sales_team_size=5,
                crm_tool="HubSpot",
                average_deal_size="5000",
                average_sales_cycle="30 days",
                primary_sales_constraint="Pipeline",
                quarterly_sales_focus="Expansion",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        await session.commit()

    try:
        yield session_factory
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_sqlalchemy_salesbook_repositories_persist_core_records(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    contact_repo = SqlAlchemySalesbookClientContactRepository(session_factory)
    onboarding_repo = SqlAlchemySalesbookOnboardingRepository(session_factory)
    pipeline_repo = SqlAlchemySalesbookPipelineRepository(session_factory)
    engagement_repo = SqlAlchemySalesbookEngagementRepository(session_factory)
    team_repo = SqlAlchemySalesbookTeamMembershipRepository(session_factory)

    contact = await contact_repo.upsert(
        "profile-1",
        ClientContactUpsertRequest(
            primary_email="owner@example.com",
            contact_name="Owner",
            contact_role="CEO",
            phone="+15550001",
            company_size="11-50",
            geography="US",
            status="active",
        ),
    )
    response = await onboarding_repo.upsert_response(
        "profile-1",
        OnboardingResponseSubmit(
            phase=1,
            question_key="mission_statement",
            question_text="Mission statement?",
            response_value="Grow revenue",
            response_type="text",
        ),
    )
    counts = await onboarding_repo.count_answered_by_phase("profile-1")
    progress = await onboarding_repo.upsert_progress(
        "profile-1",
        current_phase=1,
        phase1_pct=1.75,
        phase2_pct=0.0,
        phase3_pct=0.0,
        total_pct=0.88,
        phase1_completed_at_iso=None,
        phase2_completed_at_iso=None,
        phase3_completed_at_iso=None,
    )
    deal = await pipeline_repo.create_deal(
        "profile-1",
        PipelineDealCreateRequest(
            stage="new_lead",
            lead_score=40,
            deal_value=Decimal("1200.00"),
            deal_probability=Decimal("0.30"),
            assigned_agent="rep-1",
        ),
    )
    updated = await pipeline_repo.update_deal(
        deal.deal_id,
        PipelineDealUpdateRequest(stage="closed_won", close_reason="signed"),
    )
    log = await engagement_repo.create(
        EngagementLogCreateRequest(
            profile_id="profile-1",
            deal_id=deal.deal_id,
            action_type="email_sent",
            action_detail="Sent pricing",
            channel="email",
        )
    )
    member = await team_repo.add(
        "profile-1",
        TeamMembershipCreateRequest(
            user_email="seller@example.com",
            role_level="admin",
            can_invite=True,
            can_export=True,
            can_edit_onboarding=True,
        ),
    )

    assert contact.primary_email == "owner@example.com"
    assert response.question_key == "mission_statement"
    assert counts == {1: 1, 2: 0, 3: 0}
    assert progress.phase1_pct == Decimal("1.75")
    assert updated.stage == "closed_won"
    assert updated.closed_at is not None
    assert log.deal_id == deal.deal_id
    assert member.user_email == "seller@example.com"
    assert len(await pipeline_repo.list_deals("profile-1")) == 1
    assert len(await engagement_repo.list_for_profile("profile-1")) == 1
    assert len(await team_repo.list_team("profile-1")) == 1


@pytest.mark.asyncio
async def test_sqlalchemy_salesbook_comment_and_pin_repositories_support_review_and_upsert(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    comment_repo = SqlAlchemySalesbookCommentRepository(session_factory)
    pin_repo = SqlAlchemySalesbookPinRepository(session_factory)

    comment = await comment_repo.create(
        "profile-1",
        SalesbookCommentCreateRequest(
            target_type="onboarding_response",
            target_id="response-1",
            author_email="rep@example.com",
            body="This looks good",
        ),
    )
    approved = await comment_repo.update_status(
        comment.comment_id,
        status="approved",
        approved_by="admin@example.com",
    )
    first_pin = await pin_repo.upsert(
        "profile-1",
        SalesbookPinRequest(
            target_type="deal",
            target_id="deal-1",
            pinned_by="admin@example.com",
        ),
    )
    second_pin = await pin_repo.upsert(
        "profile-1",
        SalesbookPinRequest(
            target_type="deal",
            target_id="deal-1",
            pinned_by="lead@example.com",
        ),
    )

    approved_rows = await comment_repo.list_for_profile("profile-1", status="approved")
    pins = await pin_repo.list_for_profile("profile-1")

    assert approved.status == "approved"
    assert approved.approved_at is not None
    assert len(approved_rows) == 1
    assert first_pin.pin_id == second_pin.pin_id
    assert second_pin.pinned_by == "lead@example.com"
    assert len(pins) == 1

    await pin_repo.remove("profile-1", "deal", "deal-1")

    assert await pin_repo.list_for_profile("profile-1") == []


@pytest.mark.asyncio
async def test_sqlalchemy_salesbook_repositories_raise_structured_not_found_errors(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    pipeline_repo = SqlAlchemySalesbookPipelineRepository(session_factory)
    comment_repo = SqlAlchemySalesbookCommentRepository(session_factory)

    with pytest.raises(UnknownDealError) as deal_error:
        await pipeline_repo.update_deal("missing-deal", PipelineDealUpdateRequest(stage="qualified"))

    with pytest.raises(UnknownCommentError) as comment_error:
        await comment_repo.update_status("missing-comment", status="approved", approved_by="admin@example.com")

    assert deal_error.value.code == "salesbook.deal.not_found"
    assert comment_error.value.code == "salesbook.comment.not_found"
