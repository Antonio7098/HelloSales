"""Triage service for classifying user responses.

Determines whether a given user response should be assessed against skills
("assess") or treated as general_chatter / meta conversation ("skip").

This service is intentionally lightweight and fast:
- Uses a small LLM model (via the standard LLMProvider abstraction)
- Returns a simple decision + reason
- Logs decisions to the triage_log table for observability
- Emits optional status events via a callback (for Debug Panel / mobile UI)
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers.base import LLMMessage, LLMProvider
from app.ai.providers.factory import get_llm_provider
from app.ai.substrate import ProviderCallLogger
from app.infrastructure.pricing import estimate_llm_cost_cents
from app.schemas.assessment import TriageDecision, TriageRequest, TriageResponse

logger = logging.getLogger("triage")


TRIAGE_SYSTEM_PROMPT = """You are a classifier that decides whether a user's latest response
is actual skill practice or general chatter/meta conversation.

You NEVER coach, ask questions, or continue the conversation.
You ONLY classify. You must use both the latest user response and the preceding
context (especially the coach's last message) to make your decision.

Definitions:
- skill_practice: The user is actively attempting a speaking task, pitch,
  explanation, argument, story, greeting, or other performance in response to
  a coaching or practice prompt. This includes "try again" or "say it this way"
  style re-tries where the user is attempting a new version.
- general_chatter: Greetings, small talk, questions about the app, meta-conversation
  about what to practice, or anything that is not an actual attempt to follow a
  coaching or practice instruction.

Decision rules:
- If the coach's most recent message explicitly asks the user to **try, practice, redo,
  imagine, describe, tell, pose an exercise, or produce an example** (for instance:
  "Here's an exercise for you to try" or "Your turn: describe your weekend"), then you
  **MUST** treat the next user response that looks like a phrase, sentence, or short
  paragraph as skill_practice, even if it sounds like casual small talk.
- If the latest user response clearly contains a substantive attempt at a pitch,
  explanation, argument, story, greeting, or similar performance → decision = "assess"
  and reason = "skill_practice_detected".
- Otherwise → decision = "skip" and reason = "general_chatter".

Output format (STRICT):
Return ONLY a JSON object with keys:
{
  "decision": "assess" | "skip",
  "reason": "skill_practice_detected" | "general_chatter" | string
}

Do NOT add any extra text before or after the JSON.

Examples (for your internal reasoning, not to be repeated back):

1) Coach sets an explicit exercise about the weekend, user attempts it:

Context (previous turns):
Coach: "Here's an exercise for you to try. Imagine you're telling a friend about your weekend... Your turn!"
User: "Weekend, I met up with some friends and played guitar, and it was very fun. And then afterwards, we went to the cinema to see a film."

Expected JSON:
{"decision": "assess", "reason": "skill_practice_detected"}

2) Same user text, but no exercise prompt from the coach (general chatter):

Context (previous turns):
Coach: "How's your day going?"
User: "Weekend, I met up with some friends and played guitar, and it was very fun. And then afterwards, we went to the cinema to see a film."

Expected JSON:
{"decision": "skip", "reason": "general_chatter"}
"""


class TriageService:
    """Service for triaging user responses before assessment.

    This service is used by chat/voice flows and by dev/test endpoints.
    It is intentionally stateless aside from writing to triage_log.
    """

    def __init__(
        self,
        db: AsyncSession,
        llm_provider: LLMProvider | None = None,
        model_id: str | None = None,
        system_prompt: str | None = None,
    ):
        """Initialize triage service.

        Args:
            db: Database session (required)
            llm_provider: LLM provider for classification (required - no factory fallback)
            model_id: Optional model ID override
            system_prompt: Optional custom system prompt
        """
        if llm_provider is None:
            raise ValueError("llm_provider is required. Use explicit injection or get_llm_provider() at the call site.")
        self.db = db
        self.llm = llm_provider
        self._default_model_id = model_id or self._get_default_model_id()
        self._system_prompt = system_prompt or TRIAGE_SYSTEM_PROMPT
        self.call_logger = ProviderCallLogger(db)

    @staticmethod
    def _get_configured_llm_provider() -> LLMProvider:
        """Get LLM provider configured with the default model choice."""
        from app.config import get_settings

        get_settings()
        provider = get_llm_provider()  # Use default provider
        return provider

    @staticmethod
    def _get_default_model_id() -> str:
        """Get the default triage model ID based on env configuration."""
        from app.config import get_settings

        settings = get_settings()
        return settings.triage_model_id

    async def classify_response(
        self,
        request: TriageRequest,
        *,
        interaction_id: UUID | None = None,
        send_status: Callable[[str, str, dict[str, Any] | None], Any] | None = None,
        request_id: UUID | None = None,
        _model_id: str | None = None,
    ) -> TriageResponse:
        """Classify a user response as assessable skill practice or general chatter.

        Args:
            request: TriageRequest payload (includes session_id, context, response).
            interaction_id: Optional interaction ID for logging.
            send_status: Optional callback for status events
                (service, status, metadata) → Any

        Returns:
            TriageResponse with decision, reason, and observability metadata.
        """

        start_time = time.time()

        # Build full prompt first so we can surface it via status events
        messages = self._build_messages(request)
        prompt_payload = [{"role": m.role, "content": m.content} for m in messages]

        if send_status:
            await send_status(
                "triage",
                "started",
                {
                    "session_id": str(request.session_id),
                    "prompt": prompt_payload,
                },
            )

        decision: TriageDecision = TriageDecision.SKIP
        reason: str = "triage_error"
        latency_ms: int | None = None
        tokens_used: int | None = None
        cost_cents: int | None = None
        provider: str | None = None
        model: str | None = None
        provider_call_id: UUID | None = None

        # Retry once on failure
        retries = 1
        for attempt in range(retries + 1):
            try:
                llm_start = time.time()

                model_to_use = _model_id or self._default_model_id
                llm_response, call_row = await self.call_logger.call_llm_generate(
                    service="triage",
                    provider=self.llm.name,
                    model_id=model_to_use,
                    prompt_messages=prompt_payload,
                    call=lambda model=model_to_use: self.llm.generate(
                        messages,
                        model=model,
                        max_tokens=128,
                        temperature=0.0,
                    ),
                    session_id=request.session_id,
                    user_id=None,
                    interaction_id=interaction_id,
                    request_id=request_id,
                )

                latency_ms = call_row.latency_ms or int((time.time() - llm_start) * 1000)
                provider = self.llm.name
                model = llm_response.model
                provider_call_id = call_row.id

                full_content = llm_response.content
                if not full_content or not full_content.strip():
                    raise ValueError("Empty response from Triage LLM")

                try:
                    parsed = self._parse_response(full_content)
                except Exception as e:
                    raise ValueError(
                        f"Failed to parse triage response: {str(e)} | Raw content: {full_content!r}"
                    ) from e

                decision = TriageDecision(parsed["decision"])
                reason = parsed.get("reason", "") or "unspecified"

                tokens_in = getattr(llm_response, "tokens_in", None)
                tokens_out = getattr(llm_response, "tokens_out", None)
                if tokens_in is not None and tokens_out is not None:
                    tokens_used = tokens_in + tokens_out
                else:
                    # Fallback estimate if provider does not return usage
                    tokens_in_est = sum(len(m.content) for m in messages) // 4
                    tokens_used = tokens_in_est

                cost_cents = estimate_llm_cost_cents(
                    provider=self.llm.name,
                    model=model,
                    tokens_in=tokens_in if tokens_in is not None else 0,
                    tokens_out=tokens_out if tokens_out is not None else 0,
                )

                call_row.output_parsed = {"decision": decision.value, "reason": reason}
                call_row.cost_cents = cost_cents

                logger.info(
                    "Triage decision",
                    extra={
                        "service": "triage",
                        "session_id": str(request.session_id),
                        "decision": decision.value,
                        "reason": reason,
                        "latency_ms": latency_ms,
                        "tokens_used": tokens_used,
                        "cost_cents": cost_cents,
                        "provider": provider,
                        "model": model,
                    },
                )

                if send_status:
                    await send_status(
                        "triage",
                        "complete",
                        {
                            "decision": decision.value,
                            "reason": reason,
                            "latency_ms": latency_ms,
                            "provider": provider,
                            "model": model,
                        },
                    )

                # If successful, break retry loop
                break

            except Exception as exc:
                maybe_call_id = getattr(exc, "_provider_call_id", None)
                if isinstance(maybe_call_id, UUID):
                    provider_call_id = maybe_call_id

                is_last_attempt = attempt == retries
                if not is_last_attempt:
                    logger.warning(
                        "Triage attempt failed, retrying",
                        extra={
                            "service": "triage",
                            "attempt": attempt + 1,
                            "error": str(exc),
                        },
                    )
                    continue

                # Final failure handling
                latency_ms = int((time.time() - start_time) * 1000)
                logger.error(
                    "Triage classification failed",
                    extra={
                        "service": "triage",
                        "session_id": str(request.session_id),
                        "error": str(exc),
                        "latency_ms": latency_ms,
                    },
                    exc_info=True,
                )
                decision = TriageDecision.SKIP
                reason = "triage_error"
                tokens_used = None
                cost_cents = None

                if send_status:
                    await send_status(
                        "triage",
                        "error",
                        {"error": str(exc)},
                    )

        # Write triage_log entry regardless of success/failure
        await self._log_triage(
            session_id=request.session_id,
            interaction_id=interaction_id,
            decision=decision,
            reason=reason,
            provider_call_id=provider_call_id,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
            cost_cents=cost_cents,
            provider=provider,
            model=model,
        )

        total_duration_ms = int((time.time() - start_time) * 1000)
        logger.debug(
            "Triage completed",
            extra={
                "service": "triage",
                "session_id": str(request.session_id),
                "decision": decision.value,
                "reason": reason,
                "duration_ms": total_duration_ms,
            },
        )

        return TriageResponse(
            decision=decision,
            reason=reason,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
            cost_cents=cost_cents,
            provider=provider,
            model=model,
        )

    def _build_messages(self, request: TriageRequest) -> list[LLMMessage]:
        """Build LLM messages for triage classification.

        We keep the prompt compact: short context + latest user response +
        JSON-only output instructions.
        """

        # Format recent context as plain text lines
        context_lines: list[str] = []
        for msg in request.context:
            role = "User" if msg.role.value == "user" else "Coach"
            context_lines.append(f"{role}: {msg.content}")

        context_text = "\n".join(context_lines) if context_lines else "(no prior context)"

        user_prompt = (
            "Classify the LAST user response in the following conversation.\n\n"
            f"Context (previous turns):\n{context_text}\n\n"
            f"Latest user response:\n{request.user_response}\n\n"
            "Remember: Respond ONLY with a JSON object as documented in the system prompt."
        )

        return [
            LLMMessage(role="system", content=self._system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]

    @staticmethod
    def _parse_response(raw: str) -> dict[str, Any]:
        """Parse LLM JSON response for triage.

        Tries to be robust to minor formatting issues (e.g. code fences).
        Raises ValueError if parsing fails or decision is invalid.
        """

        # Strip common Markdown code fences if present
        text = raw.strip()
        if text.startswith("```"):
            # Remove leading ```... and trailing ```
            text = text.strip("`")
            # In case language is specified (```json) we try to find the first brace
            brace_idx = text.find("{")
            if brace_idx != -1:
                text = text[brace_idx:]

        # Extract JSON object substring if there's surrounding text
        if "{" in text and "}" in text:
            start = text.index("{")
            end = text.rfind("}") + 1
            text = text[start:end]

        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("Triage response JSON must be an object")

        decision = data.get("decision")
        reason = data.get("reason")

        if decision not in ("assess", "skip"):
            raise ValueError(f"Invalid triage decision: {decision}")

        return {"decision": decision, "reason": reason}

    async def _log_triage(
        self,
        *,
        session_id: UUID,
        interaction_id: UUID | None,
        decision: TriageDecision,
        reason: str,
        provider_call_id: UUID | None,
        latency_ms: int | None,
        tokens_used: int | None,
        cost_cents: int | None,
        provider: str | None,
        model: str | None,
    ) -> None:
        """Persist a TriageLog entry to the database."""
        # Import via services facade so tests can patch app.services.triage.TriageLog
        try:
            from app.domains.assessment import triage as triage_facade  # type: ignore
            TriageLogFacade = triage_facade.TriageLog
        except Exception:
            # Fallback to direct model if facade import fails
            from app.models import TriageLog as TriageLogFacade  # type: ignore

        log_entry = TriageLogFacade(
            session_id=session_id,
            interaction_id=interaction_id,
            provider_call_id=provider_call_id,
            decision=decision.value,
            reason=reason,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
            cost_cents=cost_cents,
        )
        self.db.add(log_entry)
        # Do not commit here; callers should batch commits to avoid many
        # small transactions that can block the event loop.
        await self.db.flush()

        logger.debug(
            "Triage log entry created",
            extra={
                "service": "triage",
                "session_id": str(session_id),
                "interaction_id": str(interaction_id) if interaction_id else None,
                "decision": decision.value,
                "latency_ms": latency_ms,
                "tokens_used": tokens_used,
                "cost_cents": cost_cents,
                "provider": provider,
                "model": model,
            },
        )
