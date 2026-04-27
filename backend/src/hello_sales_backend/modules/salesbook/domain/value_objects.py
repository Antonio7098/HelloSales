"""Salesbook value objects — enums and constants. /Oliviercontribution."""

from __future__ import annotations

from enum import StrEnum


class ClientStatus(StrEnum):
    """Lifecycle state for a client (extension-side; auth lives in modules/auth)."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    CHURNED = "churned"
    PENDING = "pending"


class PipelineStage(StrEnum):
    """Deal stage in the sales pipeline. Transitions auto-stamp stage_entered_at."""

    NEW_LEAD = "new_lead"
    CONTACTED = "contacted"
    ENGAGED = "engaged"
    BOOKED = "booked"
    QUALIFIED = "qualified"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


CLOSED_STAGES: frozenset[PipelineStage] = frozenset(
    {PipelineStage.CLOSED_WON, PipelineStage.CLOSED_LOST}
)


class RoleLevel(StrEnum):
    """Per-org team membership role."""

    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class ActionType(StrEnum):
    """Engagement action — captured in every sales-log entry."""

    EMAIL_SENT = "email_sent"
    EMAIL_OPENED = "email_opened"
    SMS_SENT = "sms_sent"
    CALL_MADE = "call_made"
    MEETING_BOOKED = "meeting_booked"
    FORM_SUBMITTED = "form_submitted"


# Phase totals — drive completion-percentage math across the service layer.
# These match the canonical onboarding spreadsheet (1HGSlYMtxE9...).
PHASE_1_TOTAL_QUESTIONS = 57
PHASE_2_TOTAL_QUESTIONS = 22
PHASE_3_TOTAL_QUESTIONS = 35
TOTAL_ONBOARDING_QUESTIONS = (
    PHASE_1_TOTAL_QUESTIONS + PHASE_2_TOTAL_QUESTIONS + PHASE_3_TOTAL_QUESTIONS
)
assert TOTAL_ONBOARDING_QUESTIONS == 114

__all__ = [
    "ClientStatus",
    "PipelineStage",
    "CLOSED_STAGES",
    "RoleLevel",
    "ActionType",
    "PHASE_1_TOTAL_QUESTIONS",
    "PHASE_2_TOTAL_QUESTIONS",
    "PHASE_3_TOTAL_QUESTIONS",
    "TOTAL_ONBOARDING_QUESTIONS",
]
