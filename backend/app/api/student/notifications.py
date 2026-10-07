from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.notifications import Notification, NotificationChannel, NotificationPreference
from app.models.user import User
from app.schemas.notifications import NotificationResponse

router = APIRouter(prefix="/notifications", tags=["notifications"])
AuthenticatedUser = Depends(get_current_user)


@router.get("", response_model=list[NotificationResponse])
def list_notifications(
    student: User = AuthenticatedUser, db: Session = Depends(get_db)
) -> list[Notification]:
    return list(
        db.scalars(
            select(Notification)
            .where(Notification.user_id == student.id)
            .order_by(Notification.created_at.desc())
            .limit(100)
        )
    )


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_read(
    notification_id: UUID, student: User = AuthenticatedUser, db: Session = Depends(get_db)
) -> Notification:
    notification = db.get(Notification, notification_id)
    if not notification or notification.user_id != student.id:
        raise HTTPException(404, "Notification not found")
    if not notification.read_at:
        notification.read_at = datetime.now(UTC)
        db.commit()
        db.refresh(notification)
    return notification


@router.put("/preferences/{channel}")
def set_preference(
    channel: NotificationChannel,
    enabled: bool,
    student: User = AuthenticatedUser,
    db: Session = Depends(get_db),
) -> dict[str, bool | str]:
    preference = db.scalar(
        select(NotificationPreference).where(
            NotificationPreference.user_id == student.id,
            NotificationPreference.channel == channel,
        )
    )
    if not preference:
        preference = NotificationPreference(user_id=student.id, channel=channel, enabled=enabled)
        db.add(preference)
    else:
        preference.enabled = enabled
    db.commit()
    return {"channel": channel.value, "enabled": enabled}


@router.get("/preferences")
def get_preferences(student: User = AuthenticatedUser, db: Session = Depends(get_db)) -> list[dict]:
    preferences = db.scalars(
        select(NotificationPreference).where(NotificationPreference.user_id == student.id)
    ).all()
    return [{"channel": pref.channel.value, "enabled": pref.enabled} for pref in preferences]
