"""ChatStreamingService for SRP compliance.

Handles LLM streaming with fallback logic and circuit breaker enforcement.
"""

import asyncio
import logging
import time
import uuid
from collections.abc import Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers.base import LLMMessage, LLMProvider
from app.ai.providers.factory import get_llm_provider
from app.ai.substrate import ProviderCallLogger, get_circuit_breaker
from app.ai.substrate.events import get_event_sink

logger = logging.getLogger("chat")


class ChatStreamingService:
    """Service for streaming LLM responses with fallback and circuit breaker.

    Responsibilities:
    - Stream LLM responses with token-by-token delivery
    - Handle provider fallback on failure
    - Enforce circuit breaker policy
    - Track metrics (TTFT, token count, etc.)
    """

    def __init__(
        self,
        db: AsyncSession,
        llm_provider: LLMProvider,
    ) -> None:
        """Initialize streaming service.

        Args:
            db: Database session
            llm_provider: LLM provider to use
        """
        self.db = db
        self.llm = llm_provider
        self.call_logger = ProviderCallLogger(db)

    async def stream_with_fallback(
        self,
        *,
        messages: list[LLMMessage],
        model_id: str | None = None,
        session_id: uuid.UUID | None = None,
        stage_started_at: float | None = None,
        send_status: Callable[[str, str, dict[str, Any] | None], Any] | None = None,
        send_token: Callable[[str], Any] | None = None,
        max_tokens: int | None = None,
        user_id: uuid.UUID | None = None,
        request_id: uuid.UUID | None = None,
        pipeline_run_id: uuid.UUID | None = None,
        org_id: uuid.UUID | None = None,
        interaction_id: uuid.UUID | None = None,
    ) -> tuple[str, int, str, str, int, uuid.UUID]:
        """Stream LLM response with fallback on failure.

        Returns:
            Tuple of (full_response, token_count, provider_name, model_id, ttft_ms, provider_call_id)
        """
        start_time = stage_started_at or time.time()

        llm_provider = self.llm

        # Try primary provider
        try:
            return await self._stream_from_llm(
                llm=llm_provider,
                messages=messages,
                model_id=model_id,
                session_id=session_id,
                stage_started_at=start_time,
                send_status=send_status,
                send_token=send_token,
                max_tokens=max_tokens,
                user_id=user_id,
                request_id=request_id,
                pipeline_run_id=pipeline_run_id,
                org_id=org_id,
                _interaction_id=interaction_id,
            )
        except Exception as primary_error:
            logger.warning(
                f"Primary LLM provider failed: {primary_error}",
                extra={
                    "service": "chat",
                    "provider": llm_provider.name,
                    "error": str(primary_error),
                },
            )

            # Check if fallback is disabled
            if getattr(self, "_fallback_disabled", False):
                raise

            # Try backup providers
            backup_providers = getattr(self.llm, "backup_providers", None) or []
            for backup_provider_name in backup_providers:
                try:
                    backup_provider = get_llm_provider(backup_provider_name)
                    logger.info(
                        f"Trying backup provider: {backup_provider_name}",
                        extra={
                            "service": "chat",
                            "provider": backup_provider_name,
                        },
                    )
                    return await self._stream_from_llm(
                        llm=backup_provider,
                        messages=messages,
                        model_id=model_id,
                        session_id=session_id,
                        stage_started_at=start_time,
                        send_status=send_status,
                        send_token=send_token,
                        max_tokens=max_tokens,
                        user_id=user_id,
                        request_id=request_id,
                        pipeline_run_id=pipeline_run_id,
                        org_id=org_id,
                        _interaction_id=interaction_id,
                    )
                except Exception as backup_error:
                    logger.warning(
                        f"Backup provider {backup_provider_name} failed: {backup_error}",
                        extra={
                            "service": "chat",
                            "provider": backup_provider_name,
                            "error": str(backup_error),
                        },
                    )
                    continue

            # All providers failed
            raise

    async def _stream_from_llm(
        self,
        *,
        llm: LLMProvider,
        messages: list[LLMMessage],
        model_id: str | None,
        session_id: uuid.UUID | None,
        stage_started_at: float,
        send_status: Callable[[str, str, dict[str, Any] | None], Any] | None,
        send_token: Callable[[str], Any] | None,
        max_tokens: int | None,
        user_id: uuid.UUID | None,
        request_id: uuid.UUID | None,
        pipeline_run_id: uuid.UUID | None,
        org_id: uuid.UUID | None,
        _interaction_id: uuid.UUID | None,
    ) -> tuple[str, int, str, str, int, uuid.UUID]:
        """Stream response from a single LLM provider."""
        provider_name = llm.name
        effective_model_id = model_id or getattr(llm, "default_model", None)

        # Check circuit breaker before making the call
        breaker = get_circuit_breaker()
        if await breaker.is_open(
            operation="llm.stream",
            provider=provider_name,
            model_id=effective_model_id,
        ):
            get_event_sink().try_emit(
                type="llm.breaker.denied",
                data={
                    "operation": "llm.stream",
                    "provider": provider_name,
                    "model_id": effective_model_id,
                    "reason": "circuit_open",
                },
            )
            logger.warning(
                "LLM call denied by circuit breaker",
                extra={
                    "service": "chat",
                    "operation": "llm.stream",
                    "provider": provider_name,
                    "model_id": effective_model_id,
                },
            )
            from app.ai.substrate import CircuitBreakerOpenError
            raise CircuitBreakerOpenError(
                f"LLM call denied by circuit breaker: provider={provider_name}, model_id={effective_model_id}"
            )

        await breaker.note_attempt(
            operation="llm.stream", provider=provider_name, model_id=effective_model_id
        )

        # Prepare prompt messages for logging
        prompt_messages = [
            {"role": msg.role, "content": msg.content[:500]}  # Truncate for logging
            for msg in messages
        ]

        try:
            async with self.call_logger.time_call(
                service="chat",
                provider=provider_name,
                model_id=effective_model_id,
                prompt_messages=prompt_messages,
                session_id=session_id,
                user_id=user_id,
                request_id=request_id,
                pipeline_run_id=pipeline_run_id,
                org_id=org_id,
            ) as log:
                # Stream from LLM
                tokens: list[str] = []
                token_count = 0
                full_response = ""

                # Get stream from provider
                stream = llm.stream(
                    messages=messages,
                    max_tokens=max_tokens,
                    model=model_id,
                )

                first_token_received = False
                ttft_ms = 0

                async for token in stream:
                    if token and not first_token_received:
                        first_token_received = True
                        ttft_ms = int((time.time() - stage_started_at) * 1000)
                        if send_status:
                            await send_status(
                                "llm",
                                "first_token",
                                {
                                    "provider": provider_name,
                                    "model": effective_model_id,
                                    "ttft_ms": ttft_ms,
                                },
                            )

                    tokens.append(token)
                    token_count += 1

                    token_display = token if token not in {" ", ""} else ""
                    full_response += token_display

                    if send_token:
                        await send_token(token)

                # Update log payload
                log["output_content"] = full_response
                log["tokens_out"] = token_count

                # Estimate tokens in (rough: 1 token ≈ 4 chars)
                log["tokens_in"] = len("".join(m.content for m in messages)) // 4

                # Update provider call record if available
                provider_call_id = getattr(log, "_call_id", None)

        except asyncio.CancelledError:
            # Handle cancellation
            if send_status:
                await send_status("llm", "cancelled", None)
            raise

        except Exception:
            # Log error
            await breaker.record_failure(
                operation="llm.stream",
                provider=provider_name,
                model_id=effective_model_id,
                reason="error",
            )
            raise

        # Record success
        await breaker.record_success(
            operation="llm.stream",
            provider=provider_name,
            model_id=effective_model_id,
        )

        # Emit completion event
        if send_status:
            await send_status(
                "llm",
                "completed",
                {
                    "provider": provider_name,
                    "model": effective_model_id,
                    "ttft_ms": ttft_ms,
                    "token_count": token_count,
                    "duration_ms": int((time.time() - stage_started_at) * 1000),
                },
            )

        return (
            full_response,
            token_count,
            provider_name,
            effective_model_id or "",
            ttft_ms,
            provider_call_id or uuid.uuid4(),
        )
