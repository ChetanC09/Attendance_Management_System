from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.models.user import User
from app.services.auth import AccountLocked, authenticate


def test_authentication_locks_account_at_failure_threshold() -> None:
    user = User(
        institutional_id="S-100",
        email="student@example.edu",
        full_name="Student",
        password_hash="stored-hash",
        role="STUDENT",
        is_active=True,
        failed_login_attempts=4,
    )
    db = MagicMock()
    db.scalar.return_value = user

    with (
        patch("app.services.auth.verify_password", return_value=False),
        patch("app.services.auth.record_audit"),
    ):
        with pytest.raises(AccountLocked):
            authenticate(db, user.email, "incorrect-password")

    assert user.failed_login_attempts == 5
    assert user.locked_until is not None
    assert user.locked_until > datetime.now(UTC)
    db.commit.assert_called_once()


def test_authentication_refuses_an_active_lock_without_verifying_password() -> None:
    user = User(
        institutional_id="S-101",
        email="student@example.edu",
        full_name="Student",
        password_hash="stored-hash",
        role="STUDENT",
        is_active=True,
        locked_until=datetime.now(UTC) + timedelta(minutes=10),
    )
    db = MagicMock()
    db.scalar.return_value = user

    with (
        patch("app.services.auth.verify_password") as verify,
        patch("app.services.auth.record_audit"),
    ):
        with pytest.raises(AccountLocked):
            authenticate(db, user.email, "anything")

    verify.assert_not_called()
    db.commit.assert_called_once()
