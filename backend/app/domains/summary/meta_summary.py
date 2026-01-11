"""Meta summary service for cross-session memory management."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers.base import LLMMessage, LLMProvider
from app.ai.providers.factory import get_llm_provider
from app.ai.substrate import ProviderCallLogger
from app.infrastructure.pricing import estimate_llm_cost_cents
from app.models import Session, SessionSummary
from app.schemas.meta_summary import MetaSummaryLLMOutput, MetaSummaryMemory

logger = logging.getLogger("meta_summary")


META_SUMMARY_SYSTEM_PROMPT = """You are updating a user's long-term coaching meta summary.

Inputs:
- existing meta summary memory (structured JSON)
- existing meta summary text (short)
- the latest session summary text for the session that just ended/was left

Tasks:
1. Update the memory JSON with any new insights, patterns, or themes
2. Write a concise meta summary text (2-3 sentences max) capturing the user's progress

Return ONLY valid JSON for MetaSummaryLLMOutput.
"""


def _append_bounded_uuids(existing: list[UUID], new: UUID, max_len: int = 200) -> list[UUID]:
    """Append a UUID to a list, keeping it bounded to max_len."""
    updated = existing + [new]
    return updated[-max_len:] if len(updated) > max_len else updated


def _enforce_caps(memory: MetaSummaryMemory) -> MetaSummaryMemory:
    """Enforce reasonable caps on memory structure sizes."""
    # Cap skill tracking
    if memory.skill_progress and len(memory.skill_progress) > 50:
        memory.skill_progress = memory.skill_progress[-50:]
    
    # Cap recent themes
    if memory.recent_themes and len(memory.recent_themes) > 20:
        memory.recent_themes = memory.recent_themes[-20:]
    
    # Cap coaching notes
    if memory.coaching_notes and len(memory.coaching_notes) > 30:
        memory.coaching_notes = memory.coaching_notes[-30:]
    
    return memory


class MetaSummaryService:
    """Service for managing user meta summaries across sessions."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.llm = get_llm_provider()
        self.call_logger = ProviderCallLogger(db)

    @staticmethod
    def _get_default_model_id() -> str:
        from app.config import get_settings

        settings = get_settings()
        choice = settings.llm_model_choice
        return settings.llm_model1_id if choice == "model1" else settings.llm_model2_id

    # Note: MetaSummaryService disabled as UserMetaSummary feature is removed
    async def get_or_create(self, *, user_id: UUID):
        return None

    async def merge_latest_unprocessed_summaries(
        self,
        *,
        user_id: UUID,
        max_sessions: int = 1,
        request_id: UUID | None = None,
    ):
        return None

    # Note: Remaining methods disabled as UserMetaSummary feature is removed
