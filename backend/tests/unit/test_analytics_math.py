import pytest

from app.services.analytics_math import projected_attendance, recovery_plan


def test_recovery_plan_minimum_lectures_reaches_target() -> None:
    result = recovery_plan(attended=6, conducted=10, target_percentage=75)
    assert result["required_lectures"] == 6
    assert result["projected_percentage"] == 75


def test_recovery_plan_reports_target_above_100_as_unachievable() -> None:
    with pytest.raises(ValueError):
        recovery_plan(attended=6, conducted=10, target_percentage=101)


def test_recovery_plan_full_attendance_already_meets_100_percent() -> None:
    result = recovery_plan(attended=10, conducted=10, target_percentage=100)
    assert result["required_lectures"] == 0
    assert result["achievable"] is True


def test_recovery_plan_with_no_lectures_starts_with_one_attendance() -> None:
    result = recovery_plan(attended=0, conducted=0, target_percentage=75)
    assert result["required_lectures"] == 1
    assert result["projected_percentage"] == 100


def test_projection_alerts_when_future_absences_cross_threshold() -> None:
    result = projected_attendance(attended=8, conducted=10, potential_absences=2, threshold=75)
    assert result["projected_percentage"] == 66.67
    assert result["at_risk"] is True
