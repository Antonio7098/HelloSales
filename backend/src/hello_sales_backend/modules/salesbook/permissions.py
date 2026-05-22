"""Salesbook permission constants. /Oliviercontribution.

Module-local permission constants for routes that read or write salesbook
state. shared/auth.py is intentionally NOT touched so the salesbook module
remains self-contained.
"""

from __future__ import annotations

# Salesbook — added on feature/Oliviercontribution
SALESBOOK_READ_PERMISSION = "salesbook.read"
SALESBOOK_WRITE_PERMISSION = "salesbook.write"
ONBOARDING_READ_PERMISSION = "onboarding.read"
ONBOARDING_WRITE_PERMISSION = "onboarding.write"
PIPELINE_READ_PERMISSION = "pipeline.read"
PIPELINE_WRITE_PERMISSION = "pipeline.write"
ENGAGEMENT_READ_PERMISSION = "engagement.read"
ENGAGEMENT_WRITE_PERMISSION = "engagement.write"
TEAM_READ_PERMISSION = "team.read"
TEAM_WRITE_PERMISSION = "team.write"
# Moderation — comments + pins (admin moderates rep contributions)
COMMENT_WRITE_PERMISSION = "comment.write"
COMMENT_APPROVE_PERMISSION = "comment.approve"
PIN_WRITE_PERMISSION = "pin.write"
PIN_READ_PERMISSION = "pin.read"

__all__ = [
    "SALESBOOK_READ_PERMISSION",
    "SALESBOOK_WRITE_PERMISSION",
    "ONBOARDING_READ_PERMISSION",
    "ONBOARDING_WRITE_PERMISSION",
    "PIPELINE_READ_PERMISSION",
    "PIPELINE_WRITE_PERMISSION",
    "ENGAGEMENT_READ_PERMISSION",
    "ENGAGEMENT_WRITE_PERMISSION",
    "TEAM_READ_PERMISSION",
    "TEAM_WRITE_PERMISSION",
    "COMMENT_WRITE_PERMISSION",
    "COMMENT_APPROVE_PERMISSION",
    "PIN_WRITE_PERMISSION",
    "PIN_READ_PERMISSION",
]
