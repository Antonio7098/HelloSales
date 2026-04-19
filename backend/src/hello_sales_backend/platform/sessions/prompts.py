"""Versioned session summary prompts."""

from __future__ import annotations

from hello_sales_backend.platform.llm.prompts import (
    EffectivePromptRef,
    PromptMetadata,
    effective_prompt_ref,
)

SESSION_SUMMARY_PROMPT = PromptMetadata(
    prompt_id="session.summary.compaction",
    version="v1",
    owner_kind="session",
    owner_id="session-substrate",
    purpose="summary_generation",
)


def session_summary_prompt_ref() -> EffectivePromptRef:
    """Return the effective prompt reference for session summaries."""

    return effective_prompt_ref(SESSION_SUMMARY_PROMPT)
