"""Default configuration values for the pipeline system.

This module provides centralized default values for timeouts, guardrails,
fallbacks, and quality modes. These can be overridden via environment
variables or configuration files.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

# =============================================================================
# Timeout Defaults
# =============================================================================

@dataclass(frozen=True)
class TimeoutDefaults:
    """Default timeout values for various pipeline operations (in milliseconds)."""

    LLM_STREAM_MS: int = 30000          # 30 seconds for LLM streaming
    LLM_COMPLETE_MS: int = 60000        # 60 seconds for non-streaming LLM
    STT_MS: int = 15000                 # 15 seconds for speech-to-text
    TTS_MS: int = 30000                 # 30 seconds for text-to-speech
    ASSESSMENT_MS: int = 10000          # 10 seconds for assessment
    POLICY_MS: int = 5000               # 5 seconds for policy checks
    GUARDRAILS_MS: int = 5000           # 5 seconds for guardrails checks
    CONTEXT_BUILD_MS: int = 5000        # 5 seconds for context building
    VALIDATION_MS: int = 5000           # 5 seconds for validation
    TRIAGE_MS: int = 10000              # 10 seconds for triage
    PERSIST_MS: int = 5000              # 5 seconds for persistence


TIMEOUTS = TimeoutDefaults()


# =============================================================================
# Guardrails Defaults
# =============================================================================

@dataclass(frozen=True)
class GuardrailsDefaults:
    """Default guardrails configuration."""

    # Content filtering thresholds
    MAX_INPUT_LENGTH: int = 10000       # Max characters for input
    MAX_OUTPUT_LENGTH: int = 50000      # Max characters for output

    # Safety settings
    BLOCK_SELF_HARM: bool = True
    BLOCK_HATE_SPEECH: bool = True
    BLOCK_VIOLENCE: bool = True
    BLOCK_SEXUAL: bool = True
    BLOCK_MEDICAL: bool = True

    # Custom rules
    MAX_URLS_PER_MESSAGE: int = 5
    MAX_MENTIONS_PER_MESSAGE: int = 10


GUARDRAILS = GuardrailsDefaults()


# =============================================================================
# Fallback Defaults
# =============================================================================

@dataclass(frozen=True)
class FallbackDefaults:
    """Default fallback configuration for degraded modes."""

    # Provider fallback chain
    LLM_FALLBACK_CHAIN: list[str] = None  # Configured in settings
    STT_FALLBACK_CHAIN: list[str] = None
    TTS_FALLBACK_CHAIN: list[str] = None

    # Circuit breaker settings
    CIRCUIT_BREAKER_THRESHOLD: int = 5    # Failures before opening
    CIRCUIT_BREAKER_TIMEOUT_MS: int = 30000  # 30 seconds

    # Degraded mode settings
    USE_STUB_ON_FAILURE: bool = True
    STUB_LLM_MODEL: str = "stub-llm"


FALLBACKS = FallbackDefaults()


# =============================================================================
# Quality Mode Defaults
# =============================================================================

QualityMode = Literal["fast", "balanced", "accurate", "practice"]


@dataclass(frozen=True)
class QualityModeDefaults:
    """Default configuration for quality modes."""

    # Fast mode - lowest latency, lower quality
    fast: dict[str, Any] = None

    # Balanced mode - default trade-off
    balanced: dict[str, Any] = None

    # Accurate mode - highest quality, higher latency
    accurate: dict[str, Any] = None

    # Practice mode - optimized for practice sessions
    practice: dict[str, Any] = None

    def __post_init__(self):
        object.__setattr__(
            self,
            "fast",
            {
                "model": "fast-model",
                "temperature": 0.7,
                "max_tokens": 256,
                "stream": True,
            },
        )
        object.__setattr__(
            self,
            "balanced",
            {
                "model": "balanced-model",
                "temperature": 0.5,
                "max_tokens": 512,
                "stream": True,
            },
        )
        object.__setattr__(
            self,
            "accurate",
            {
                "model": "accurate-model",
                "temperature": 0.3,
                "max_tokens": 1024,
                "stream": True,
            },
        )
        object.__setattr__(
            self,
            "practice",
            {
                "model": "practice-model",
                "temperature": 0.6,
                "max_tokens": 512,
                "stream": True,
                "include_assessment": True,
            },
        )


QUALITY_MODES = QualityModeDefaults()


# =============================================================================
# Retry Defaults
# =============================================================================

@dataclass(frozen=True)
class RetryDefaults:
    """Default retry configuration."""

    MAX_RETRIES: int = 3
    INITIAL_DELAY_MS: int = 1000
    MAX_DELAY_MS: int = 10000
    EXPONENTIAL_BASE: float = 2.0


RETRIES = RetryDefaults()


# =============================================================================
# Summary Defaults
# =============================================================================

@dataclass(frozen=True)
class SummaryDefaults:
    """Default configuration for conversation summary."""

    SUMMARY_THRESHOLD: int = 8  # Generate summary every 8 turns
    ALWAYS_INCLUDE_LAST_N: int = 6  # Always include last N messages
    MAX_SUMMARY_LENGTH: int = 1000
    META_SUMMARY_THRESHOLD: int = 10  # Meta-summary after 10 summaries


SUMMARIES = SummaryDefaults()


# =============================================================================
# Mode-to-Quality Mapping
# =============================================================================

# Default mapping from mode to quality mode
MODE_TO_QUALITY: dict[str, QualityMode] = {
    "conversational": "balanced",
    "practice": "practice",
    "accurate": "accurate",
    "fast": "fast",
    "interview_prep": "balanced",
    "presentation_practice": "balanced",
    "cold_outreach": "fast",
    "sales_pitch": "balanced",
}


__all__ = [
    "TimeoutDefaults",
    "TIMEOUTS",
    "GuardrailsDefaults",
    "GUARDRAILS",
    "FallbackDefaults",
    "FALLBACKS",
    "QualityModeDefaults",
    "QualityMode",
    "QUALITY_MODES",
    "RetryDefaults",
    "RETRIES",
    "SummaryDefaults",
    "SUMMARIES",
    "MODE_TO_QUALITY",
]
