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

Your job:
- extract durable, cross-session facts only
- prefer recent info; compress older
- keep the memory bounded (hard caps below)

Hard caps:
- preferences: max 20
- recurring_strengths: max 20
- recurring_issues: max 25
- exercise_archetypes: max 50
- milestones: max 30
- processed_session_summary_ids: keep max 200 (append new ID)

Output format (STRICT):
Return ONLY a single JSON object with the keys:
{
  "memory": { ... },
  "summary_text": "..."
}

Rules:
- summary_text must be short (<= 180 words), focused on what matters for coaching continuity.
- Always keep schema_version.
- Do not invent personal details.
- Do not include any extra keys beyond the schema.
"""


class MetaSummaryService:
    def __init__(
        self,
        db: AsyncSession,
        llm_provider: LLMProvider | None = None,
        model_id: str | None = None,
    ) -> None:
        self.db = db

        from app.config import get_settings

        settings = get_settings()
        self.llm = llm_provider or get_llm_provider(settings.meta_summary_llm_provider)
        configured_model = (settings.meta_summary_llm_model_id or "").strip()
        self._default_model_id = model_id or configured_model or self._get_default_model_id()
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

        meta.memory = updated_memory.model_dump(mode="json")
        meta.summary_text = (parsed.summary_text or "").strip()
        meta.last_merged_summary_id = session_summary.id
        meta.last_merged_summary_at = session_summary.created_at
        meta.updated_at = datetime.utcnow()

        cost_cents = estimate_llm_cost_cents(
            provider=self.llm.name,
            model=response.model,
            tokens_in=response.tokens_in,
            tokens_out=response.tokens_out,
        )

        call_row.output_parsed = parsed.model_dump(mode="json")
        call_row.cost_cents = cost_cents

        return meta

    async def maybe_merge_latest_session_summary(
        self,
        *,
        user_id: UUID,
        previous_session_id: UUID | None,
        request_id: UUID | None = None,
    ) -> UserMetaSummary | None:
        if previous_session_id is None:
            return None

        summary = await self._get_latest_session_summary(previous_session_id)
        if summary is None:
            return None

        # If we've already processed this session summary, treat as a no-op.
        # This helps callers decide whether to emit meta_summary.updated.
        meta = await self.get_or_create(user_id=user_id)
        existing_memory = self._safe_load_memory(meta.memory)
        processed = {UUID(str(x)) for x in existing_memory.processed_session_summary_ids}
        if summary.id in processed:
            return None

        return await self.merge_session_summary(
            user_id=user_id,
            session_summary=summary,
            request_id=request_id,
        )

    async def merge_session_summary(
        self,
        *,
        user_id: UUID,
        session_summary: SessionSummary,
        request_id: UUID | None = None,
    ) -> UserMetaSummary:
        meta = await self.get_or_create(user_id=user_id)

        existing_memory = self._safe_load_memory(meta.memory)
        processed = [UUID(str(x)) for x in existing_memory.processed_session_summary_ids]
        if session_summary.id in set(processed):
            logger.info(
                "Meta summary merge skipped (already processed)",
                extra={
                    "service": "meta_summary",
                    "user_id": str(user_id),
                    "session_summary_id": str(session_summary.id),
                },
            )
            return meta

        prompt_messages = self._build_messages(
            existing_memory=existing_memory,
            existing_summary_text=meta.summary_text,
            session_summary=session_summary,
        )

        prompt_payload = [{"role": m.role, "content": m.content} for m in prompt_messages]

        llm_start = time.time()
        model_to_use = self._default_model_id

        response, call_row = await self.call_logger.call_llm_generate(
            service="meta_summary",
            provider=self.llm.name,
            model_id=model_to_use,
            prompt_messages=prompt_payload,
            call=lambda: self.llm.generate(
                prompt_messages,
                model=model_to_use,
                temperature=0.2,
                max_tokens=900,
            ),
            session_id=session_summary.session_id,
            user_id=user_id,
            interaction_id=None,
            request_id=request_id,
        )
        latency_ms = call_row.latency_ms or int((time.time() - llm_start) * 1000)

        parsed = self._parse_llm_output(response.content)

        updated_memory = parsed.memory
        updated_memory.processed_session_summary_ids = _append_bounded_uuids(
            existing=list(existing_memory.processed_session_summary_ids),
            new=session_summary.id,
            max_len=200,
        )
        updated_memory = _enforce_caps(updated_memory)

        meta.memory = updated_memory.model_dump(mode="json")
        meta.summary_text = (parsed.summary_text or "").strip()
        meta.last_merged_summary_id = session_summary.id
        meta.last_merged_summary_at = session_summary.created_at
        meta.updated_at = datetime.utcnow()

        tokens_used = response.tokens_in + response.tokens_out
        cost_cents = estimate_llm_cost_cents(
            provider=self.llm.name,
            model=response.model,
            tokens_in=response.tokens_in,
            tokens_out=response.tokens_out,
        )

        call_row.output_parsed = parsed.model_dump(mode="json")
        call_row.cost_cents = cost_cents

        await self.db.commit()

        logger.info(
            "Meta summary merged",
            extra={
                "service": "meta_summary",
                "user_id": str(user_id),
                "session_id": str(session_summary.session_id),
                "session_summary_id": str(session_summary.id),
                "latency_ms": latency_ms,
                "tokens_used": tokens_used,
                "cost_cents": cost_cents,
            },
        )

        return meta

    async def _get_latest_session_summary(self, session_id: UUID) -> SessionSummary | None:
        result = await self.db.execute(
            select(SessionSummary)
            .where(SessionSummary.session_id == session_id)
            .order_by(SessionSummary.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _safe_load_memory(raw: object) -> MetaSummaryMemory:
        try:
            return MetaSummaryMemory.model_validate(raw or {})
        except Exception:
            return MetaSummaryMemory()

    @staticmethod
    def _build_messages(
        *,
        existing_memory: MetaSummaryMemory,
        existing_summary_text: str | None,
        session_summary: SessionSummary,
    ) -> list[LLMMessage]:
        payload = {
            "existing_memory": existing_memory.model_dump(mode="json"),
            "existing_summary_text": (existing_summary_text or "").strip(),
            "session_summary_id": str(session_summary.id),
            "session_summary_text": session_summary.text,
        }

        return [
            LLMMessage(role="system", content=META_SUMMARY_SYSTEM_PROMPT),
            LLMMessage(
                role="user",
                content=(
                    "Update the meta summary using the inputs below. "
                    "Return ONLY valid JSON for MetaSummaryLLMOutput.\n\n"
                    f"INPUTS:\n{json.dumps(payload, ensure_ascii=False)}"
                ),
            ),
        ]

    @staticmethod
    def _parse_llm_output(raw: str) -> MetaSummaryLLMOutput:
        text = (raw or "").strip()

        if "```" in text:
            fence_start = text.find("```")
            fence_end = text.rfind("```")
            inner = (
                text[fence_start + 3 : fence_end]
                if fence_end > fence_start
                else text[fence_start + 3 :]
            )
            inner = inner.lstrip()
            if inner.lower().startswith("json"):
                inner = inner[4:].lstrip()
            text = inner

        if "{" in text and "}" in text:
            start = text.index("{")
            end = text.rfind("}") + 1
            text = text[start:end]

        data = json.loads(text)

        if isinstance(data, dict):
            memory = data.get("memory")
            if isinstance(memory, dict):

                def _coerce_meta_items(value: object, *, kind: str) -> list[dict[str, object]]:
                    if not isinstance(value, list):
                        return []

                    out: list[dict[str, object]] = []
                    for item in value:
                        label: str | None = None
                        payload: dict[str, object] = {}

                        if isinstance(item, str):
                            label = item.strip()
                        elif isinstance(item, dict):
                            for key in (
                                "label",
                                "text",
                                "value",
                                "name",
                                "preference",
                                "pattern",
                            ):
                                v = item.get(key)
                                if isinstance(v, str) and v.strip():
                                    label = v.strip()
                                    break
                            payload = dict(item)

                        if not label:
                            continue

                        payload["label"] = label

                        if kind == "preference":
                            conf = payload.get("confidence")
                            if conf is not None and not isinstance(conf, (int, float)):
                                payload.pop("confidence", None)
                        else:
                            sev = payload.get("severity")
                            if sev is not None and not isinstance(sev, (int, float)):
                                payload.pop("severity", None)

                        out.append(payload)

                    return out

                memory["preferences"] = _coerce_meta_items(
                    memory.get("preferences"),
                    kind="preference",
                )
                memory["recurring_strengths"] = _coerce_meta_items(
                    memory.get("recurring_strengths"),
                    kind="pattern",
                )
                memory["recurring_issues"] = _coerce_meta_items(
                    memory.get("recurring_issues"),
                    kind="pattern",
                )

                data["memory"] = memory

        return MetaSummaryLLMOutput.model_validate(data)


def _append_bounded_uuids(*, existing: list[UUID], new: UUID, max_len: int) -> list[UUID]:
    out: list[UUID] = []
    seen: set[UUID] = set()

    for item in existing:
        try:
            u = UUID(str(item))
        except Exception:
            continue
        if u in seen:
            continue
        out.append(u)
        seen.add(u)

    if new not in seen:
        out.append(new)

    if len(out) > max_len:
        out = out[-max_len:]

    return out


def _enforce_caps(mem: MetaSummaryMemory) -> MetaSummaryMemory:
    mem.preferences = mem.preferences[:20]
    mem.recurring_strengths = mem.recurring_strengths[:20]
    mem.recurring_issues = mem.recurring_issues[:25]
    mem.exercise_archetypes = mem.exercise_archetypes[:50]
    mem.milestones = mem.milestones[:30]
    mem.processed_session_summary_ids = mem.processed_session_summary_ids[-200:]
    return mem
