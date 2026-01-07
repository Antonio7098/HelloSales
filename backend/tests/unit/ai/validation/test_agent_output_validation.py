from app.ai.validation import parse_agent_output


def test_parse_agent_output_returns_none_for_non_json() -> None:
    parsed, error, attempted = parse_agent_output("hello")
    assert parsed is None
    assert error is None
    assert attempted is False


def test_parse_agent_output_returns_none_for_unrelated_json() -> None:
    parsed, error, attempted = parse_agent_output('{"foo": "bar"}')
    assert parsed is None
    assert error is None
    assert attempted is False


def test_parse_agent_output_accepts_minimal_agent_output() -> None:
    parsed, error, attempted = parse_agent_output(
        '{"assistant_message": "hi", "actions": [], "artifacts": []}'
    )
    assert attempted is True
    assert error is None
    assert parsed is not None
    assert parsed.assistant_message == "hi"
    assert parsed.actions == []
    assert parsed.artifacts == []


def test_parse_agent_output_rejects_extra_fields() -> None:
    parsed, error, attempted = parse_agent_output(
        '{"assistant_message": "hi", "actions": [], "artifacts": [], "extra": 1}'
    )
    assert attempted is True
    assert parsed is None
    assert error == "schema_validation_error"


def test_parse_agent_output_rejects_empty_assistant_message() -> None:
    parsed, error, attempted = parse_agent_output(
        '{"assistant_message": " ", "actions": [], "artifacts": []}'
    )
    assert attempted is True
    assert parsed is None
    assert error == "schema_validation_error"


def test_parse_agent_output_rejects_empty_action_type() -> None:
    parsed, error, attempted = parse_agent_output(
        '{"assistant_message": "hi", "actions": [{"type": " ", "payload": {}}], "artifacts": []}'
    )
    assert attempted is True
    assert parsed is None
    assert error == "schema_validation_error"


def test_parse_agent_output_rejects_empty_artifact_type() -> None:
    parsed, error, attempted = parse_agent_output(
        '{"assistant_message": "hi", "actions": [], "artifacts": [{"type": "", "payload": {}}]}'
    )
    assert attempted is True
    assert parsed is None
    assert error == "schema_validation_error"
