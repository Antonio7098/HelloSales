from __future__ import annotations

from decimal import Decimal

import pytest

from hello_sales_backend.modules.salesbook.infra.memory import (
    InMemorySalesbookClientContactRepository,
    InMemorySalesbookCommentRepository,
    InMemorySalesbookEngagementRepository,
    InMemorySalesbookOnboardingRepository,
    InMemorySalesbookPipelineRepository,
    InMemorySalesbookPinRepository,
    InMemorySalesbookTeamMembershipRepository,
    NullProductReadPort,
)
from hello_sales_backend.modules.salesbook.domain.onboarding_registry import get_phase_questions
from hello_sales_backend.modules.salesbook.use_cases.salesbook_service import SalesbookService
from hello_sales_backend.modules.salesbook.use_cases.views import (
    ClientContactUpsertRequest,
    EngagementLogCreateRequest,
    OnboardingBatchSubmit,
    OnboardingResponseSubmit,
    PipelineDealCreateRequest,
    PipelineDealUpdateRequest,
    SalesbookCommentApproveRequest,
    SalesbookCommentCreateRequest,
    SalesbookPinRequest,
    TeamMembershipCreateRequest,
)


def _build_service() -> SalesbookService:
    return SalesbookService(
        contact_repo=InMemorySalesbookClientContactRepository(),
        onboarding_repo=InMemorySalesbookOnboardingRepository(),
        pipeline_repo=InMemorySalesbookPipelineRepository(),
        engagement_repo=InMemorySalesbookEngagementRepository(),
        team_repo=InMemorySalesbookTeamMembershipRepository(),
        product_read=NullProductReadPort(),
        comment_repo=InMemorySalesbookCommentRepository(),
        pin_repo=InMemorySalesbookPinRepository(),
    )


@pytest.mark.asyncio
async def test_upsert_client_contact_round_trips_latest_values() -> None:
    service = _build_service()

    created = await service.upsert_client_contact(
        "profile-1",
        ClientContactUpsertRequest(
            primary_email="first@example.com",
            contact_name="First Contact",
            contact_role="CEO",
            phone="+15550001",
            company_size="1-10",
            geography="US",
            status="active",
        ),
    )
    updated = await service.upsert_client_contact(
        "profile-1",
        ClientContactUpsertRequest(
            primary_email="second@example.com",
            contact_name="Second Contact",
            contact_role="Founder",
            phone="+15550002",
            company_size="11-50",
            geography="CA",
            status="pending",
        ),
    )

    assert updated.extension_id == created.extension_id
    assert updated.created_at == created.created_at
    assert updated.primary_email == "second@example.com"
    assert updated.contact_name == "Second Contact"
    assert updated.status == "pending"


@pytest.mark.asyncio
async def test_submit_response_recomputes_progress_percentages() -> None:
    service = _build_service()

    await service.submit_response(
        "profile-1",
        OnboardingResponseSubmit(
            phase=1,
            question_key="q1",
            question_text="Question 1",
            response_value="Answer 1",
            response_type="text",
        ),
    )

    progress = await service.get_onboarding_progress("profile-1")
    responses = await service.list_responses("profile-1", phase=1)

    assert len(responses) == 1
    assert progress.current_phase == 1
    assert progress.phase1_pct == Decimal("1.75")
    assert progress.phase2_pct == Decimal("0.0")
    assert progress.phase3_pct == Decimal("0.0")
    assert progress.total_completion_pct == Decimal("0.88")


@pytest.mark.asyncio
async def test_submit_batch_stores_multiple_responses_and_filters_by_phase() -> None:
    service = _build_service()

    stored = await service.submit_batch(
        "profile-1",
        OnboardingBatchSubmit(
            phase=2,
            responses=[
                OnboardingResponseSubmit(
                    phase=2,
                    question_key="phase2-q1",
                    question_text="P2 Q1",
                    response_value="yes",
                    response_type="boolean",
                ),
                OnboardingResponseSubmit(
                    phase=2,
                    question_key="phase2-q2",
                    question_text="P2 Q2",
                    response_value="42",
                    response_type="number",
                ),
            ],
        ),
    )

    phase2 = await service.list_responses("profile-1", phase=2)
    all_rows = await service.list_responses("profile-1")
    progress = await service.get_onboarding_progress("profile-1")

    assert len(stored) == 2
    assert [row.question_key for row in phase2] == ["phase2-q1", "phase2-q2"]
    assert len(all_rows) == 2
    assert progress.phase2_pct == Decimal("9.09")
    assert progress.total_completion_pct == Decimal("1.75")


@pytest.mark.asyncio
async def test_update_deal_changes_stage_timestamp_and_sets_closed_at() -> None:
    service = _build_service()

    deal = await service.create_deal(
        "profile-1",
        PipelineDealCreateRequest(
            stage="new_lead",
            lead_score=20,
            deal_value=Decimal("250.00"),
            deal_probability=Decimal("0.10"),
        ),
    )
    updated = await service.update_deal(
        deal.deal_id,
        PipelineDealUpdateRequest(stage="closed_won", close_reason="signed"),
    )

    assert updated.stage == "closed_won"
    assert updated.close_reason == "signed"
    assert updated.closed_at is not None
    assert updated.stage_entered_at >= deal.stage_entered_at


@pytest.mark.asyncio
async def test_exhaustive_view_aggregates_contact_pipeline_comments_pins_and_team() -> None:
    service = _build_service()
    question_key, question_meta = next(iter(get_phase_questions(1).items()))

    await service.upsert_client_contact(
        "profile-1",
        ClientContactUpsertRequest(
            primary_email="owner@example.com",
            contact_name="Owner",
            contact_role="CEO",
            phone=None,
            company_size=None,
            geography=None,
            status="active",
        ),
    )
    response = await service.submit_response(
        "profile-1",
        OnboardingResponseSubmit(
            phase=1,
            question_key=question_key,
            question_text=str(question_meta.get("question") or question_meta.get("question_text") or question_key),
            response_value="Answer 1",
            response_type="text",
        ),
    )
    deal = await service.create_deal(
        "profile-1",
        PipelineDealCreateRequest(
            stage="qualified",
            lead_score=80,
            deal_value=Decimal("1000.00"),
            deal_probability=Decimal("0.65"),
        ),
    )
    await service.log_engagement(
        EngagementLogCreateRequest(
            profile_id="profile-1",
            deal_id=deal.deal_id,
            action_type="email_sent",
            action_detail="Intro sent",
            channel="email",
        )
    )
    member = await service.add_team_member(
        "profile-1",
        TeamMembershipCreateRequest(
            user_email="teammate@example.com",
            role_level="admin",
            can_invite=True,
            can_export=True,
            can_edit_onboarding=True,
        ),
    )
    pending = await service.add_comment(
        "profile-1",
        SalesbookCommentCreateRequest(
            target_type="onboarding_response",
            target_id=response.response_id,
            author_email="rep@example.com",
            body="Looks promising",
        ),
    )
    await service.review_comment(
        pending.comment_id,
        SalesbookCommentApproveRequest(
            approved_by="admin@example.com",
            decision="approved",
        ),
    )
    await service.pin_entry(
        "profile-1",
        SalesbookPinRequest(
            target_type="deal",
            target_id=deal.deal_id,
            pinned_by="admin@example.com",
        ),
    )

    view = await service.get_exhaustive_view("profile-1")

    assert view.contact is not None
    assert view.contact.primary_email == "owner@example.com"
    assert view.progress is not None
    assert view.progress.phase1_pct == Decimal("1.75")
    assert any(entry.question_key == question_key and entry.response_value == "Answer 1" for entry in view.onboarding)
    assert len(view.pipeline) == 1
    assert len(view.engagement) == 1
    assert len(view.team) == 1
    assert view.team[0].membership_id == member.membership_id
    assert len(view.comments) == 1
    assert view.comments[0].status == "approved"
    assert len(view.pinned) == 1


@pytest.mark.asyncio
async def test_remove_team_member_and_unpin_entry_remove_rows_from_lists() -> None:
    service = _build_service()

    member = await service.add_team_member(
        "profile-1",
        TeamMembershipCreateRequest(user_email="teammate@example.com"),
    )
    await service.pin_entry(
        "profile-1",
        SalesbookPinRequest(
            target_type="deal",
            target_id="deal-1",
            pinned_by="admin@example.com",
        ),
    )

    await service.remove_team_member(member.membership_id)
    await service.unpin_entry("profile-1", "deal", "deal-1")

    assert await service.list_team("profile-1") == []
    assert await service.list_pins("profile-1") == []
