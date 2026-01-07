"""Google Gemini LLM provider."""

import logging
from collections.abc import AsyncGenerator
from typing import Any

from app.ai.providers.base import LLMMessage, LLMProvider, LLMResponse
from app.ai.providers.registry import register_llm_provider

logger = logging.getLogger("providers.gemini")


@register_llm_provider
class GeminiProvider(LLMProvider):
    """LLM provider using Google's Gemini API."""

    DEFAULT_MODEL = "gemini-2.0-flash"

    @classmethod
    def resolve_model(cls, model: str | None) -> str | None:
        m = (model or "").strip()
        if not m:
            return cls.DEFAULT_MODEL

        if not m.startswith("gemini-"):
            return cls.DEFAULT_MODEL

        return m

    def __init__(self, api_key: str, model: str | None = None):
        self._api_key = api_key
        self._model = model or self.DEFAULT_MODEL
        self._client = None

    @property
    def name(self) -> str:
        return "gemini"

    def _get_client(self):
        """Lazily initialize the Gemini client."""
        if self._client is None:
            try:
                import google.generativeai as genai

                genai.configure(api_key=self._api_key)
                self._client = genai.GenerativeModel(self._model)
            except ImportError as e:
                raise ImportError(
                    "google-generativeai package not installed. "
                    "Install with: pip install google-generativeai"
                ) from e
        return self._client

    def _convert_messages(self, messages: list[LLMMessage]) -> tuple[str | None, list[dict]]:
        """Convert LLMMessage list to Gemini format.

        Gemini uses a different format:
        - System instruction is separate
        - Messages are 'user' and 'model' roles

        Returns:
            Tuple of (system_instruction, history)
        """
        system_instruction = None
        history = []

        for msg in messages:
            if msg.role == "system":
                # Gemini handles system as a separate instruction
                system_instruction = msg.content
            elif msg.role == "user":
                history.append({"role": "user", "parts": [msg.content]})
            elif msg.role == "assistant":
                history.append({"role": "model", "parts": [msg.content]})

        return system_instruction, history

    async def generate(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a response using Gemini."""
        import google.generativeai as genai

        # Configure with API key
        genai.configure(api_key=self._api_key)

        model_id = model or self._model
        system_instruction, history = self._convert_messages(messages)

        # Log full prompt for debugging
        logger.info(
            "Gemini generate started",
            extra={
                "service": "providers.gemini",
                "model": model_id,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "system_instruction": system_instruction,
                "history": history,
            },
        )

        # Create model with system instruction if present
        gen_model = genai.GenerativeModel(
            model_name=model_id,
            system_instruction=system_instruction,
            generation_config=genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
        )

        # If we have history, use chat; otherwise just generate
        if kwargs:
            logger.debug(
                "Gemini stream extra kwargs",
                extra={
                    "service": "providers.gemini",
                    "model": model_id,
                    "extra_kwargs": kwargs,
                },
            )

        if len(history) > 1:
            # Use chat for multi-turn
            chat = gen_model.start_chat(history=history[:-1])
            last_message = history[-1]["parts"][0] if history else ""
            response = await chat.send_message_async(last_message)
        else:
            # Single message
            prompt = history[0]["parts"][0] if history else ""
            response = await gen_model.generate_content_async(prompt)

        # Extract text from response
        text = response.text if response.text else ""

        # Estimate tokens (Gemini doesn't always return exact counts)
        # Prefer accurate counts from usage metadata or the model's
        # count_tokens API, and fall back to a rough heuristic only if
        # those are unavailable.

        tokens_in = 0
        tokens_out = 0

        # 1) Try to use usage metadata if the SDK provides it
        usage = getattr(response, "usage_metadata", None)
        if usage is not None:
            try:
                tokens_in = int(getattr(usage, "prompt_token_count", 0) or 0)
                tokens_out = int(getattr(usage, "candidates_token_count", 0) or 0)
            except Exception:  # pragma: no cover - defensive path
                tokens_in = 0
                tokens_out = 0

        # 2) If metadata is missing or zero, fall back to count_tokens
        # on the configured model. We use the structured history for
        # input tokens and the final text for output tokens.
        try:
            if tokens_in <= 0:
                token_counts_in = gen_model.count_tokens(history or [])
                tokens_in = int(getattr(token_counts_in, "total_tokens", 0) or 0)
        except Exception:  # pragma: no cover - defensive path
            tokens_in = tokens_in or 0

        try:
            if tokens_out <= 0 and text:
                token_counts_out = gen_model.count_tokens(text)
                tokens_out = int(getattr(token_counts_out, "total_tokens", 0) or 0)
        except Exception:  # pragma: no cover - defensive path
            tokens_out = tokens_out or 0

        # 3) Final fallback: rough estimate ~4 chars per token if we
        # still don't have usable counts.
        if tokens_in <= 0:
            tokens_in = sum(len(m.content) for m in messages) // 4
        if tokens_out <= 0:
            tokens_out = len(text) // 4

        if kwargs:
            logger.debug(
                "Gemini generate extra kwargs",
                extra={
                    "service": "providers.gemini",
                    "model": model_id,
                    "extra_kwargs": kwargs,
                },
            )

        logger.debug(
            "Gemini generation complete",
            extra={
                "service": "providers.gemini",
                "model": model_id,
                "tokens_in_estimate": tokens_in,
                "tokens_out_estimate": tokens_out,
            },
        )

        return LLMResponse(
            content=text,
            model=model_id,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            finish_reason="stop",
        )

    async def stream(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Stream a response using Gemini."""
        import google.generativeai as genai

        genai.configure(api_key=self._api_key)

        model_id = model or self._model
        system_instruction, history = self._convert_messages(messages)

        # Log full prompt for debugging
        logger.info(
            "Gemini stream started",
            extra={
                "service": "providers.gemini",
                "model": model_id,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "system_instruction": system_instruction,
                "history": history,
            },
        )

        if kwargs:
            logger.debug(
                "Gemini stream extra kwargs",
                extra={
                    "service": "providers.gemini",
                    "model": model_id,
                    "extra_kwargs": kwargs,
                },
            )

        gen_model = genai.GenerativeModel(
            model_name=model_id,
            system_instruction=system_instruction,
            generation_config=genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
        )

        if len(history) > 1:
            chat = gen_model.start_chat(history=history[:-1])
            last_message = history[-1]["parts"][0] if history else ""
            response = await chat.send_message_async(last_message, stream=True)
        else:
            prompt = history[0]["parts"][0] if history else ""
            response = await gen_model.generate_content_async(prompt, stream=True)

        async for chunk in response:
            if chunk.text:
                yield chunk.text
