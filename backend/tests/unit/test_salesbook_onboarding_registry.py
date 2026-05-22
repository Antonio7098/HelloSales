from __future__ import annotations

from hello_sales_backend.modules.salesbook.domain.onboarding_registry import (
    get_onboarding_questions,
    get_phase_questions,
    get_phase_sections,
    get_phase_totals,
    get_section_questions,
)


def test_get_onboarding_questions_loads_registry() -> None:
    questions = get_onboarding_questions()

    assert questions
    first_key = next(iter(questions))
    assert questions[first_key]["key"] == first_key


def test_phase_questions_and_sections_are_consistent() -> None:
    phase_questions = get_phase_questions(1)
    sections = get_phase_sections(1)

    assert phase_questions
    assert sections
    assert all(question["phase"] == 1 for question in phase_questions.values())
    assert all(question["section"] in sections for question in phase_questions.values())


def test_section_questions_filter_by_phase_and_section() -> None:
    section = get_phase_sections(1)[0]
    questions = get_section_questions(1, section)

    assert questions
    assert all(question["phase"] == 1 for question in questions.values())
    assert all(question["section"] == section for question in questions.values())


def test_phase_totals_match_contract_counts() -> None:
    assert get_phase_totals() == (57, 22, 35, 114)
