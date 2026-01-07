"""
Assessment Engine Test Scripts
------------------------------
Test examples and runners for the triage and assessment services.

Modules:
- general_chatter: Examples that should be SKIPPED by triage
- skill_attempt: Examples that should be ASSESSED by triage

Usage:
    # Run as pytest
    pytest backend/tests/scripts/ -v

    # Run standalone for inspection
    python backend/tests/scripts/general_chatter.py
    python backend/tests/scripts/skill_attempt.py
"""

from .general_chatter import GENERAL_CHATTER_EXAMPLES
from .general_chatter import get_all_examples as get_chatter_examples
from .skill_attempt import SKILL_ATTEMPT_EXAMPLES
from .skill_attempt import get_all_examples as get_skill_examples

__all__ = [
    "GENERAL_CHATTER_EXAMPLES",
    "SKILL_ATTEMPT_EXAMPLES",
    "get_chatter_examples",
    "get_skill_examples",
]
