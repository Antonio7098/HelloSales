from app.api.admin.benchmarks import EvalTestCasesImportBody
from app.schemas.eval import EvalTestCaseCreate, EvalTestCaseExpectedAssessment


def test_eval_import_body_accepts_minimal_cases() -> None:
    case = EvalTestCaseCreate(
        name="example",
        transcript="Hello, this is a test transcript.",
    )

    body = EvalTestCasesImportBody(cases=[case])

    assert len(body.cases) == 1
    assert body.cases[0].name == "example"
    assert body.cases[0].transcript.startswith("Hello")


def test_eval_import_body_with_expected_assessments() -> None:
    expected_assessment = EvalTestCaseExpectedAssessment(
        skill_slug="clarity",
        expected_level=6,
        level_tolerance=1,
        expected_keywords=["structure", "filler"],
    )

    case = EvalTestCaseCreate(
        name="assessment-case",
        transcript="User response for assessment.",
        tracked_skills=["clarity"],
        expected_triage_decision="skill_practice",
        expected_assessments=[expected_assessment],
    )

    body = EvalTestCasesImportBody(cases=[case])

    assert len(body.cases) == 1
    parsed = body.cases[0]
    assert parsed.tracked_skills == ["clarity"]
    assert parsed.expected_triage_decision == "skill_practice"
    assert parsed.expected_assessments is not None
    assert parsed.expected_assessments[0].skill_slug == "clarity"
