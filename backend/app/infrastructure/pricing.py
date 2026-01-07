"""Pricing utilities for cost estimation."""

from __future__ import annotations

GROQ_COST_PER_1K_TOKENS_HUNDREDTH_CENTS = 2.7
GEMINI_COST_PER_1K_TOKENS_HUNDREDTH_CENTS = 4.0

# STT pricing: Deepgram Nova-2 $0.0043/minute = 0.43 cents/minute
# Stored in hundredths-of-cents: 43 per minute ≈ 0.7166667 per second
DEEPGRAM_COST_PER_SECOND_HUNDREDTHS = 0.7166667

DEEPGRAM_FLUX_COST_PER_SECOND_HUNDREDTHS = 1.2833333

# TTS pricing: Google Cloud TTS Neural2 $16/million characters = $0.000016/char
# 0.000016 dollars = 0.0016 cents, i.e. 0.16 hundredths-of-cents per character
GOOGLE_TTS_COST_PER_CHAR_HUNDREDTHS = 0.16

# Optional per-model overrides so we can support different prices for specific models.
# Values are in "hundredths of a cent" per 1K tokens, matching ProviderCall.cost_cents.
LLM_PRICING_PER_1K_TOKENS_INPUT: dict[tuple[str, str], float] = {
    # Llama 3.1 8B (llama-3.1-8b-instant): $0.05 / 1M input tokens
    # 0.05 dollars = 5 cents → 0.005 cents per 1K → 0.5 hundredths-of-cents.
    ("groq", "llama-3.1-8b-instant"): 0.5,
    # Llama 3.3 70B (llama-3.3-70b-versatile): $0.59 / 1M input tokens
    # 0.59 dollars = 59 cents → 0.059 cents per 1K → 5.9 hundredths-of-cents.
    ("groq", "llama-3.3-70b-versatile"): 5.9,
    # Llama Guard 4 12B (meta-llama/llama-guard-4-12b): $0.20 / 1M input tokens
    # 0.20 dollars = 20 cents → 0.02 cents per 1K → 2.0 hundredths-of-cents.
    ("groq", "meta-llama/llama-guard-4-12b"): 2.0,
    # GPT OSS 120B (openai/gpt-oss-120b): $0.15 / 1M input tokens
    # 0.15 dollars = 15 cents → 0.015 cents per 1K → 1.5 hundredths-of-cents.
    ("groq", "openai/gpt-oss-120b"): 1.5,
    # GPT OSS 20B (openai/gpt-oss-20b): $0.075 / 1M input tokens
    # 0.075 dollars = 7.5 cents → 0.0075 cents per 1K → 0.75 hundredths-of-cents.
    ("groq", "openai/gpt-oss-20b"): 0.75,
    ("gemini", "gemini-2.5-pro"): 12.5,
    ("gemini", "gemini-2.5-flash"): 3.0,
    ("gemini", "gemini-2.5-flash-lite"): 1.0,
    ("openrouter", "nvidia/nemotron-3-nano-30b-a3b:free"): 0.0,
}

LLM_PRICING_PER_1K_TOKENS_OUTPUT: dict[tuple[str, str], float] = {
    # Llama 3.1 8B (llama-3.1-8b-instant): $0.08 / 1M output tokens
    # 0.08 dollars = 8 cents → 0.008 cents per 1K → 0.8 hundredths-of-cents.
    ("groq", "llama-3.1-8b-instant"): 0.8,
    # Llama 3.3 70B (llama-3.3-70b-versatile): $0.79 / 1M output tokens
    # 0.79 dollars = 79 cents → 0.079 cents per 1K → 7.9 hundredths-of-cents.
    ("groq", "llama-3.3-70b-versatile"): 7.9,
    # Llama Guard 4 12B (meta-llama/llama-guard-4-12b): $0.20 / 1M output tokens
    # Symmetric pricing for input/output.
    ("groq", "meta-llama/llama-guard-4-12b"): 2.0,
    # GPT OSS 120B (openai/gpt-oss-120b): $0.60 / 1M output tokens
    # 0.60 dollars = 60 cents → 0.06 cents per 1K → 6.0 hundredths-of-cents.
    ("groq", "openai/gpt-oss-120b"): 6.0,
    # GPT OSS 20B (openai/gpt-oss-20b): $0.30 / 1M output tokens
    # 0.30 dollars = 30 cents → 0.03 cents per 1K → 3.0 hundredths-of-cents.
    ("groq", "openai/gpt-oss-20b"): 3.0,
    ("gemini", "gemini-2.5-pro"): 100.0,
    ("gemini", "gemini-2.5-flash"): 25.0,
    ("gemini", "gemini-2.5-flash-lite"): 4.0,
    ("openrouter", "nvidia/nemotron-3-nano-30b-a3b:free"): 0.0,
}


def estimate_llm_cost_cents(
    *,
    provider: str | None,
    model: str | None,
    tokens_in: int | None,
    tokens_out: int | None,
) -> int:
    total_tokens = 0
    if tokens_in:
        total_tokens += tokens_in
    if tokens_out:
        total_tokens += tokens_out
    if total_tokens <= 0:
        return 0

    provider_name = str(provider or "").lower()
    model_name = str(model or "").lower()

    key = (provider_name, model_name)

    # Prefer explicit per-model pricing when available, otherwise fall back
    # to provider-level defaults.
    in_rate = LLM_PRICING_PER_1K_TOKENS_INPUT.get(key)
    out_rate = LLM_PRICING_PER_1K_TOKENS_OUTPUT.get(key)

    if in_rate is None or out_rate is None:
        if "gemini" in provider_name:
            in_rate = in_rate if in_rate is not None else GEMINI_COST_PER_1K_TOKENS_HUNDREDTH_CENTS
            out_rate = (
                out_rate if out_rate is not None else GEMINI_COST_PER_1K_TOKENS_HUNDREDTH_CENTS
            )
        else:
            in_rate = in_rate if in_rate is not None else GROQ_COST_PER_1K_TOKENS_HUNDREDTH_CENTS
            out_rate = out_rate if out_rate is not None else GROQ_COST_PER_1K_TOKENS_HUNDREDTH_CENTS

    cost = 0.0
    if tokens_in:
        cost += (tokens_in / 1000) * in_rate
    if tokens_out:
        cost += (tokens_out / 1000) * out_rate

    if cost <= 0:
        return 0

    # Round to the nearest unit so that very small but non-zero calls
    # still register as a minimal cost instead of 0 due to flooring.
    units = int(round(cost))
    return max(1, units)


def estimate_stt_cost_cents(
    *,
    provider: str | None,
    model: str | None,
    audio_duration_ms: int | None,
) -> int:
    """Estimate STT cost in hundredths-of-cents based on audio duration.

    Currently supports Deepgram Nova-2 pricing and falls back to a
    provider-level default for other Deepgram models. Other providers
    default to zero until explicitly configured.
    """

    if not audio_duration_ms or audio_duration_ms <= 0:
        return 0

    provider_name = (provider or "").lower()
    model_name = (model or "").lower()

    # Per-(provider, model) overrides, in hundredths-of-cents per second
    stt_pricing_per_second: dict[tuple[str, str], float] = {
        ("deepgram", "nova-2"): DEEPGRAM_COST_PER_SECOND_HUNDREDTHS,
        ("deepgram", "flux-general-en"): DEEPGRAM_FLUX_COST_PER_SECOND_HUNDREDTHS,
    }

    key = (provider_name, model_name)
    rate_per_second = stt_pricing_per_second.get(key)

    # Fallbacks: provider-level defaults
    if rate_per_second is None:
        if "deepgram" in provider_name:
            rate_per_second = DEEPGRAM_COST_PER_SECOND_HUNDREDTHS
        else:
            rate_per_second = 0.0

    duration_seconds = audio_duration_ms / 1000
    return int(duration_seconds * rate_per_second)


def estimate_tts_cost_cents(
    *,
    provider: str | None,
    model: str | None,
    text_length: int | None,
) -> int:
    """Estimate TTS cost in hundredths-of-cents based on text length.

    Currently supports Google Cloud TTS Neural2 pricing at a provider
    level, with room to add per-voice overrides later.
    """

    if not text_length or text_length <= 0:
        return 0

    provider_name = (provider or "").lower()
    model_name = (model or "").lower()

    # Per-(provider, model) overrides, in hundredths-of-cents per character
    tts_pricing_per_char: dict[tuple[str, str], float] = {
        # For now we treat all Google Neural2 voices the same; we can add
        # more granular entries keyed by specific voice IDs or presets.
        ("google", "neural2"): GOOGLE_TTS_COST_PER_CHAR_HUNDREDTHS,
    }

    key = (provider_name, model_name)
    rate_per_char = tts_pricing_per_char.get(key)

    # Fallbacks: provider-level defaults
    if rate_per_char is None:
        rate_per_char = GOOGLE_TTS_COST_PER_CHAR_HUNDREDTHS if "google" in provider_name else 0.0

    return int(text_length * rate_per_char)
