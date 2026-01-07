import pytest

from app.domains.assessment.benchmark import compute_level_accuracy


@pytest.mark.parametrize(
    "expected, actual, expected_accuracy",
    [
        (0, 0, 1.0),
        (5, 5, 1.0),
        (10, 10, 1.0),
        (7, 6, 0.9),
        (7, 9, 0.8),
        (3, 9, 0.4),
        (0, 10, 0.0),
        (10, 0, 0.0),
    ],
)
def test_compute_level_accuracy(expected: int, actual: int, expected_accuracy: float) -> None:
    """Ensure level accuracy scales linearly and is clipped to [0, 1]."""

    value = compute_level_accuracy(expected, actual)
    assert isinstance(value, float)
    assert pytest.approx(expected_accuracy, rel=1e-6) == value
