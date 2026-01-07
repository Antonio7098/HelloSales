"""Pydantic schemas for API request/response validation."""

from app.schemas.agent_output import (  # noqa: F401
    AgentAction,
    AgentArtifact,
    AgentOutput,
)
from app.schemas.assessment import (  # noqa: F401
    AssessmentMetrics,
    AssessmentRequest,
    AssessmentResponse,
    ChatMessage,
    FeedbackExampleQuote,
    LevelChangeEvent,
    SkillAssessmentResponse,
    SkillFeedback,
    TriageDecision,
    TriageRequest,
    TriageResponse,
)
from app.schemas.feedback import (  # noqa: F401
    FeedbackCategory,
    FeedbackEventRead,
    FeedbackMessageFlagCreate,
    FeedbackReportCreate,
    TimeBucket,
)
from app.schemas.legal import (  # noqa: F401
    LegalAcceptRequest,
    LegalConfigResponse,
    LegalPublicConfig,
)
from app.schemas.organization import (  # noqa: F401
    OrganizationMembershipMeResponse,
    OrganizationMeResponse,
)
from app.schemas.profile import (  # noqa: F401
    GoalInfo,
    UserProfileResponse,
    UserProfileUpdate,
)
from app.schemas.progress import (  # noqa: F401
    SessionHistoryItem,
    SkillLevelPoint,
    SkillProgressResponse,
)
from app.schemas.skill import (  # noqa: F401
    SkillDetailResponse,
    SkillResponse,
    TrackedSkillResponse,
    UserSkillProgress,
)

__all__ = [
    # Skills
    "SkillResponse",
    "SkillDetailResponse",
    "TrackedSkillResponse",
    "UserSkillProgress",
    # Progress
    "SkillLevelPoint",
    "SkillProgressResponse",
    "SessionHistoryItem",
    # Profile
    "GoalInfo",
    "UserProfileResponse",
    "UserProfileUpdate",
    # Assessment / triage
    "ChatMessage",
    "TriageDecision",
    "TriageRequest",
    "TriageResponse",
    "FeedbackExampleQuote",
    "SkillFeedback",
    "SkillAssessmentResponse",
    "AssessmentMetrics",
    "AssessmentRequest",
    "AssessmentResponse",
    "LevelChangeEvent",
    "FeedbackCategory",
    "TimeBucket",
    "FeedbackMessageFlagCreate",
    "FeedbackReportCreate",
    "FeedbackEventRead",
    "AgentAction",
    "AgentArtifact",
    "AgentOutput",
    "LegalPublicConfig",
    "LegalConfigResponse",
    "LegalAcceptRequest",
    "OrganizationMeResponse",
    "OrganizationMembershipMeResponse",
]
