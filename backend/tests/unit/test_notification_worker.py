import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base
from app.models.audit import SystemSetting
from app.models.exceptions import LeaveRequest, RequestStatus, RequestType
from app.models.notifications import Notification, NotificationChannel, NotificationStatus
from app.models.user import User, UserRole
from app.services import notifications as notification_service
from app.workers import notifications


def test_in_app_delivery_failure_logs_no_user_identifier_or_exception_detail(
    monkeypatch, caplog
) -> None:
    class FailedTransaction:
        def __enter__(self):
            raise RuntimeError("private database diagnostic")

        def __exit__(self, *_args):
            return False

    class FailedSessionFactory:
        def begin(self):
            return FailedTransaction()

    user_id = uuid.uuid4()
    monkeypatch.setattr(notification_service, "SessionLocal", FailedSessionFactory())

    with caplog.at_level(logging.WARNING):
        notification_service.enqueue_in_app_notification(user_id, "Title", "Message")

    assert "RuntimeError" in caplog.text
    assert str(user_id) not in caplog.text
    assert "private database diagnostic" not in caplog.text


def test_failed_provider_delivery_retries_without_losing_in_app_or_request_data(
    monkeypatch,
) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    db: Session = sessions()
    user = User(
        institutional_id="STU-WORKER",
        email="worker-student@example.edu",
        full_name="Worker Student",
        password_hash="test-only",
        role=UserRole.STUDENT,
        is_active=True,
    )
    db.add(user)
    db.flush()
    request = LeaveRequest(
        student_id=user.id,
        request_type=RequestType.LEAVE,
        status=RequestStatus.PENDING,
        reason="Existing decision data must survive provider failure.",
    )
    in_app = Notification(
        user_id=user.id,
        title="Request received",
        message="Your request is pending.",
        channel=NotificationChannel.IN_APP,
        status=NotificationStatus.PENDING,
    )
    email = Notification(
        user_id=user.id,
        title="Request update",
        message="Your request was received.",
        channel=NotificationChannel.EMAIL,
        status=NotificationStatus.PENDING,
    )
    db.add_all(
        [
            request,
            in_app,
            email,
            SystemSetting(key="notification_delivery", value={"email_enabled": True}),
        ]
    )
    db.commit()
    email_id, in_app_id, request_id = email.id, in_app.id, request.id
    db.close()
    monkeypatch.setattr(notifications, "SessionLocal", sessions)

    class FailingEmail:
        def send(self, _notification: Notification) -> None:
            raise RuntimeError("test provider unavailable")

    try:
        assert (
            notifications.process_notification_batch({NotificationChannel.EMAIL: FailingEmail()})
            == 1
        )
        with sessions() as check:
            failed_attempt = check.get(Notification, email_id)
            assert failed_attempt.status == NotificationStatus.PENDING
            assert failed_attempt.attempts == 1
            assert failed_attempt.next_attempt_at is not None
            assert failed_attempt.last_error == "RuntimeError: provider delivery failed"
            assert "test provider unavailable" not in failed_attempt.last_error
            assert check.get(Notification, in_app_id).status == NotificationStatus.PENDING
            assert check.get(LeaveRequest, request_id).status == RequestStatus.PENDING
            failed_attempt.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
            check.commit()

        assert (
            notifications.process_notification_batch({NotificationChannel.EMAIL: FailingEmail()})
            == 1
        )
        with sessions() as check:
            retry = check.get(Notification, email_id)
            assert retry.status == NotificationStatus.PENDING
            assert retry.attempts == 2
            assert (
                check.scalar(select(LeaveRequest).where(LeaveRequest.id == request_id)).status
                == RequestStatus.PENDING
            )
            retry.attempts = notifications.MAX_ATTEMPTS - 1
            retry.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
            check.commit()

        assert (
            notifications.process_notification_batch({NotificationChannel.EMAIL: FailingEmail()})
            == 1
        )
        with sessions() as check:
            exhausted = check.get(Notification, email_id)
            assert exhausted.status == NotificationStatus.FAILED
            assert exhausted.attempts == notifications.MAX_ATTEMPTS
            assert exhausted.next_attempt_at is None
        assert (
            notifications.process_notification_batch({NotificationChannel.EMAIL: FailingEmail()})
            == 0
        )
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_successful_notification_is_not_delivered_again(monkeypatch) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    with sessions.begin() as db:
        user = User(
            institutional_id="STU-WORKER-SUCCESS",
            email="worker-success@example.edu",
            full_name="Worker Success",
            password_hash="test-only",
            role=UserRole.STUDENT,
            is_active=True,
        )
        db.add(user)
        db.flush()
        notification = Notification(
            user_id=user.id,
            title="Request update",
            message="Your request was received.",
            channel=NotificationChannel.EMAIL,
            status=NotificationStatus.PENDING,
        )
        db.add_all(
            [
                notification,
                SystemSetting(key="notification_delivery", value={"email_enabled": True}),
            ]
        )
        db.flush()
        notification_id = notification.id
    monkeypatch.setattr(notifications, "SessionLocal", sessions)

    class SuccessfulEmail:
        calls = 0

        def send(self, _notification: Notification) -> None:
            self.calls += 1

    adapter = SuccessfulEmail()
    try:
        assert notifications.process_notification_batch({NotificationChannel.EMAIL: adapter}) == 1
        assert notifications.process_notification_batch({NotificationChannel.EMAIL: adapter}) == 0
        assert adapter.calls == 1
        with sessions() as check:
            delivered = check.get(Notification, notification_id)
            assert delivered.status == NotificationStatus.SENT
            assert delivered.attempts == 1
            assert delivered.sent_at is not None
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()
