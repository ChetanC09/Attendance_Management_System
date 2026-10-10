import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.notifications import Notification, NotificationChannel, NotificationStatus

logger = logging.getLogger(__name__)


def enqueue_in_app_notification(
    user_id: uuid.UUID, title: str, message: str, payload: dict | None = None
) -> None:
    """Persist independently so notification failure cannot undo the triggering transaction."""
    try:
        with SessionLocal.begin() as db:
            db.add(
                Notification(
                    user_id=user_id,
                    title=title,
                    message=message,
                    channel=NotificationChannel.IN_APP,
                    status=NotificationStatus.SENT,
                    payload=payload,
                    sent_at=datetime.now(UTC),
                )
            )
    except Exception as error:
        logger.warning("Unable to enqueue in-app notification (%s)", type(error).__name__)


def create_notification(
    db: Session,
    user_id: uuid.UUID,
    title: str,
    message: str,
    channel: NotificationChannel,
    payload: dict | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        channel=channel,
        status=NotificationStatus.PENDING,
        payload=payload,
    )
    db.add(notification)
    return notification
