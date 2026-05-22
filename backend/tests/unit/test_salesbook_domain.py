from __future__ import annotations

from decimal import Decimal
import sys
from pathlib import Path
from datetime import UTC, datetime, date

import pytest

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from hello_sales_backend.modules.salesbook.domain.value_objects import (
    ClientStatus,
    PipelineStage,
    CLOSED_STAGES,
    RoleLevel,
    ActionType,
    PHASE_1_TOTAL_QUESTIONS,
    PHASE_2_TOTAL_QUESTIONS,
    PHASE_3_TOTAL_QUESTIONS,
    TOTAL_ONBOARDING_QUESTIONS,
)
from hello_sales_backend.modules.salesbook.domain.entities import (
    ClientContact,
    OnboardingProgress,
    OnboardingResponse,
    PipelineDeal,
    EngagementEntry,
    TeamMember,
)
from hello_sales_backend.modules.salesbook.domain.exceptions import (
    SalesbookError,
    UnknownProfileError,
    UnknownDealError,
    UnknownMembershipError,
    UnknownQuestionKeyError,
    InvalidPhaseError,
)


class TestValueObjects:
    def test_client_status_values(self) -> None:
        assert ClientStatus.ACTIVE == "active"
        assert ClientStatus.SUSPENDED == "suspended"
        assert ClientStatus.CHURNED == "churned"
        assert ClientStatus.PENDING == "pending"

    def test_pipeline_stage_values(self) -> None:
        assert PipelineStage.NEW_LEAD == "new_lead"
        assert PipelineStage.CONTACTED == "contacted"
        assert PipelineStage.ENGAGED == "engaged"
        assert PipelineStage.BOOKED == "booked"
        assert PipelineStage.QUALIFIED == "qualified"
        assert PipelineStage.CLOSED_WON == "closed_won"
        assert PipelineStage.CLOSED_LOST == "closed_lost"

    def test_closed_stages_contains_only_closed(self) -> None:
        assert PipelineStage.CLOSED_WON in CLOSED_STAGES
        assert PipelineStage.CLOSED_LOST in CLOSED_STAGES
        assert len(CLOSED_STAGES) == 2

    def test_role_level_values(self) -> None:
        assert RoleLevel.ADMIN == "admin"
        assert RoleLevel.USER == "user"
        assert RoleLevel.VIEWER == "viewer"

    def test_action_type_values(self) -> None:
        assert ActionType.EMAIL_SENT == "email_sent"
        assert ActionType.EMAIL_OPENED == "email_opened"
        assert ActionType.SMS_SENT == "sms_sent"
        assert ActionType.CALL_MADE == "call_made"
        assert ActionType.MEETING_BOOKED == "meeting_booked"
        assert ActionType.FORM_SUBMITTED == "form_submitted"

    def test_phase_question_counts(self) -> None:
        assert PHASE_1_TOTAL_QUESTIONS == 57
        assert PHASE_2_TOTAL_QUESTIONS == 22
        assert PHASE_3_TOTAL_QUESTIONS == 35
        assert TOTAL_ONBOARDING_QUESTIONS == 114


class TestEntities:
    def _now(self) -> datetime:
        return datetime.now(UTC)

    def _make_client_contact(self, **overrides) -> ClientContact:
        defaults = dict(
            extension_id="ext_1",
            profile_id="prof_1",
            primary_email="test@example.com",
            contact_name="Test User",
            contact_role="CEO",
            phone="+1234567890",
            company_size="50-100",
            geography="US",
            status=ClientStatus.ACTIVE,
            created_at=self._now(),
            updated_at=self._now(),
        )
        defaults.update(overrides)
        return ClientContact(**defaults)

    def test_client_contact_is_frozen(self) -> None:
        contact = self._make_client_contact()
        with pytest.raises(Exception):  # frozen dataclass
            contact.contact_name = "Changed"

    def test_client_contact_str_enum_status(self) -> None:
        contact = self._make_client_contact(status=ClientStatus.SUSPENDED)
        assert contact.status == "suspended"

    def test_pipeline_deal_fields(self) -> None:
        deal = PipelineDeal(
            deal_id="deal_1",
            profile_id="prof_1",
            stage=PipelineStage.NEW_LEAD,
            lead_source="referral",
            lead_score=75,
            assigned_agent="agent_1",
            deal_value=Decimal("10000.00"),
            deal_probability=Decimal("0.25"),
            next_action="Follow up",
            next_action_date=date(2026, 6, 1),
            stage_entered_at=self._now(),
            created_at=self._now(),
            closed_at=None,
            close_reason=None,
        )
        assert deal.stage == "new_lead"
        assert deal.lead_score == 75
        assert deal.deal_value == Decimal("10000.00")

    def test_onboarding_progress_defaults(self) -> None:
        progress = OnboardingProgress(
            progress_id="prog_1",
            profile_id="prof_1",
            current_phase=1,
            phase1_pct=Decimal("0.00"),
            phase2_pct=Decimal("0.00"),
            phase3_pct=Decimal("0.00"),
            phase1_completed_at=None,
            phase2_completed_at=None,
            phase3_completed_at=None,
            total_completion_pct=Decimal("0.00"),
            updated_at=self._now(),
        )
        assert progress.current_phase == 1
        assert progress.phase1_completed_at is None

    def test_engagement_entry_action_type(self) -> None:
        entry = EngagementEntry(
            log_id="log_1",
            profile_id="prof_1",
            deal_id="deal_1",
            action_type=ActionType.EMAIL_SENT,
            action_detail="Sent intro email",
            action_reason="Initial outreach",
            action_result=None,
            next_step="Follow up in 3 days",
            channel="email",
            agent_id="agent_1",
            process_version="v1",
            timestamp=self._now(),
        )
        assert entry.action_type == "email_sent"

    def test_team_member_permissions(self) -> None:
        member = TeamMember(
            membership_id="mem_1",
            profile_id="prof_1",
            user_email="user@example.com",
            role_level=RoleLevel.ADMIN,
            can_invite=True,
            can_export=True,
            can_edit_onboarding=True,
            created_at=self._now(),
        )
        assert member.role_level == "admin"
        assert member.can_invite is True


class TestExceptions:
    def test_unknown_profile_error(self) -> None:
        err = UnknownProfileError("prof_missing")
        assert "prof_missing" in str(err)
        assert isinstance(err, SalesbookError)

    def test_unknown_deal_error(self) -> None:
        err = UnknownDealError("deal_999")
        assert "deal_999" in str(err)
        assert isinstance(err, SalesbookError)

    def test_unknown_membership_error(self) -> None:
        err = UnknownMembershipError("mem_999")
        assert "mem_999" in str(err)
        assert isinstance(err, SalesbookError)

    def test_unknown_question_key_error(self) -> None:
        err = UnknownQuestionKeyError("invalid_key")
        assert "invalid_key" in str(err)
        assert isinstance(err, SalesbookError)

    def test_invalid_phase_error(self) -> None:
        err = InvalidPhaseError("5")
        assert "5" in str(err)
        assert isinstance(err, SalesbookError)

    def test_salesbook_error_is_base(self) -> None:
        err = SalesbookError("base", code="salesbook.test")
        assert isinstance(err, Exception)
        assert err.code == "salesbook.test"
