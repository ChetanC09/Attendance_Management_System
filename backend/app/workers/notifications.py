import base64
import logging
from datetime import UTC, datetime, timedelta
from typing import Protocol
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from sqlalchemy import and_, or_, select

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.audit import SystemSetting
from app.models.notifications import (
    Notification,
    NotificationChannel,
    NotificationPreference,
    NotificationStatus,
)
from app.models.user import User
from app.services.email import send_email

logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 5


class NotificationAdapter(Protocol):
    def send(self, notification: Notification) -> None: ...


class SMTPEmailAdapter:
    def send(self, notification: Notification) -> None:
        with SessionLocal() as db:
            user = db.get(User, notification.user_id)
            if not user or not user.is_active:
                raise RuntimeError("Notification recipient is unavailable")
            recipient = user.email
        send_email(recipient, notification.title, notification.message)


class TwilioSMSAdapter:
    def send(self, notification: Notification) -> None:
        if (
            not settings.twilio_account_sid
            or not settings.twilio_auth_token
            or not settings.twilio_from_number
        ):
            raise RuntimeError("Twilio SMS is not configured")
        with SessionLocal() as db:
            user = db.get(User, notification.user_id)
            if not user or not user.is_active or not user.phone_number:
                raise RuntimeError("Notification recipient has no active phone number")
            phone_number = user.phone_number
        endpoint = (
            f"https://api.twilio.com/2010-04-01/Accounts/"
            f"{settings.twilio_account_sid}/Messages.json"
        )
        body = urlencode(
            {
                "To": phone_number,
                "From": settings.twilio_from_number,
                "Body": f"{notification.title}: {notification.message}"[:1500],
            }
        ).encode("utf-8")
        credentials = (
            f"{settings.twilio_account_sid}:{settings.twilio_auth_token.get_secret_value()}"
        )
        authorization = base64.b64encode(credentials.encode("utf-8")).decode("ascii")
        request = Request(
            endpoint,
            data=body,
            headers={
                "Authorization": f"Basic {authorization}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        with urlopen(request, timeout=15) as response:
            if response.status >= 300:
                raise RuntimeError(f"Twilio returned status {response.status}")


def process_notification_batch(
    adapters: dict[NotificationChannel, NotificationAdapter], limit: int = 50
) -> int:
    processed = 0
    now = datetime.now(UTC)
    with SessionLocal() as db:
        delivery = db.get(SystemSetting, "notification_delivery")
        email_enabled = (
            bool(delivery.value.get("email_enabled", False))
            if delivery
            else bool(settings.smtp_host)
        )
        sms_enabled = (
            bool(delivery.value.get("sms_enabled", False))
            if delivery
            else bool(
                settings.twilio_account_sid
                and settings.twilio_auth_token
                and settings.twilio_from_number
            )
        )
        enabled_channels = []
        if email_enabled:
            enabled_channels.append(NotificationChannel.EMAIL)
        if sms_enabled:
            enabled_channels.append(NotificationChannel.SMS)
        if not enabled_channels:
            return 0
        rows = db.scalars(
            select(Notification)
            .outerjoin(
                NotificationPreference,
                and_(
                    NotificationPreference.user_id == Notification.user_id,
                    NotificationPreference.channel == Notification.channel,
                ),
            )
            .where(
                Notification.status == NotificationStatus.PENDING,
                Notification.channel != NotificationChannel.IN_APP,
                Notification.channel.in_(enabled_channels),
                (Notification.next_attempt_at.is_(None)) | (Notification.next_attempt_at <= now),
                or_(NotificationPreference.id.is_(None), NotificationPreference.enabled.is_(True)),
            )
            .order_by(Notification.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        ).all()
        for notification in rows:
            notification.attempts += 1
            try:
                adapters[notification.channel].send(notification)
                notification.status = NotificationStatus.SENT
                notification.sent_at = now
                notification.last_error = None
                notification.next_attempt_at = None
            except Exception as error:
                notification.last_error = f"{type(error).__name__}: provider delivery failed"
                logger.warning(
                    "Notification %s delivery attempt failed (%s)",
                    notification.id,
                    type(error).__name__,
                )
                if notification.attempts >= MAX_ATTEMPTS:
                    notification.status = NotificationStatus.FAILED
                    notification.next_attempt_at = None
                else:
                    notification.next_attempt_at = now + timedelta(
                        seconds=30 * (2 ** (notification.attempts - 1))
                    )
            processed += 1
        db.commit()
    return processed
