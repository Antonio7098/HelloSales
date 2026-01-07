"""Summary service for context window compression.

.. deprecated::
    Use :mod:`app.domains.summary` instead. This module is kept for
    backwards compatibility and will be removed in a future version.
"""

from app.domains.summary import (
    DEFAULT_SUMMARY_THRESHOLD,
    SUMMARY_PROMPT,
    SummaryService,
)

__all__ = [
    "SummaryService",
    "DEFAULT_SUMMARY_THRESHOLD",
    "SUMMARY_PROMPT",
]
