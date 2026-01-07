"""Meta summary service for cross-session memory management.

.. deprecated::
    Use :mod:`app.domains.summary.meta_summary` instead. This module is kept for
    backwards compatibility and will be removed in a future version.
"""

from app.domains.summary.meta_summary import (
    META_SUMMARY_SYSTEM_PROMPT,
    MetaSummaryService,
)

__all__ = [
    "MetaSummaryService",
    "META_SUMMARY_SYSTEM_PROMPT",
]
