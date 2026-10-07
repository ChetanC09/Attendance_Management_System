from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.dependencies.auth import require_roles
from app.models.audit import AuditLog, SystemSetting
from app.models.user import User, UserRole
from app.schemas.admin import AuditLogResponse
from app.services.audit import record_audit

router = APIRouter(prefix="/admin", tags=["administration"])
Admin = Depends(require_roles(UserRole.ADMIN.value))


class ThresholdUpdate(BaseModel):
    attendance_threshold: float = Field(ge=0, le=100)


class NotificationDeliveryUpdate(BaseModel):
    email_enabled: bool
    sms_enabled: bool = False


@router.get("/settings/attendance-threshold")
def get_attendance_threshold(_: User = Admin, db: Session = Depends(get_db)) -> dict[str, float]:
    setting = db.get(SystemSetting, "attendance_threshold")
    return {"attendance_threshold": float(setting.value["percentage"]) if setting else 75.0}


@router.put("/settings/attendance-threshold")
def set_attendance_threshold(
    payload: ThresholdUpdate, admin: User = Admin, db: Session = Depends(get_db)
) -> dict[str, float]:
    setting = db.get(SystemSetting, "attendance_threshold")
    if not setting:
        setting = SystemSetting(
            key="attendance_threshold", value={"percentage": payload.attendance_threshold}
        )
        db.add(setting)
    else:
        setting.value = {"percentage": payload.attendance_threshold}
    setting.updated_by = admin.id
    record_audit(
        db,
        actor_id=admin.id,
        action="UPDATE",
        resource_type="system_setting",
        resource_id="attendance_threshold",
        after=setting.value,
    )
    db.commit()
    return {"attendance_threshold": payload.attendance_threshold}


@router.get("/settings/notifications")
def get_notification_settings(_: User = Admin, db: Session = Depends(get_db)) -> dict[str, bool]:
    setting = db.get(SystemSetting, "notification_delivery")
    if setting:
        return {
            "email_enabled": bool(setting.value.get("email_enabled", False)),
            "sms_enabled": bool(setting.value.get("sms_enabled", False)),
        }
    return {
        "email_enabled": bool(settings.smtp_host),
        "sms_enabled": bool(
            settings.twilio_account_sid
            and settings.twilio_auth_token
            and settings.twilio_from_number
        ),
    }


@router.put("/settings/notifications")
def set_notification_settings(
    payload: NotificationDeliveryUpdate, admin: User = Admin, db: Session = Depends(get_db)
) -> dict[str, bool]:
    if payload.email_enabled and not settings.smtp_host:
        raise HTTPException(422, "Configure SMTP before enabling email delivery")
    if payload.sms_enabled:
        if not (
            settings.twilio_account_sid
            and settings.twilio_auth_token
            and settings.twilio_from_number
        ):
            raise HTTPException(422, "Configure Twilio before enabling SMS delivery")
    setting = db.get(SystemSetting, "notification_delivery")
    value = {"email_enabled": payload.email_enabled, "sms_enabled": payload.sms_enabled}
    if not setting:
        setting = SystemSetting(key="notification_delivery", value=value)
        db.add(setting)
    else:
        setting.value = value
    setting.updated_by = admin.id
    record_audit(
        db,
        actor_id=admin.id,
        action="UPDATE",
        resource_type="system_setting",
        resource_id="notification_delivery",
        after=value,
    )
    db.commit()
    return value


@router.get("/audit-logs", response_model=list[AuditLogResponse])
def list_audit_logs(
    action: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _: User = Admin,
    db: Session = Depends(get_db),
) -> list[AuditLog]:
    statement = select(AuditLog).order_by(AuditLog.occurred_at.desc()).limit(limit).offset(offset)
    if action:
        statement = statement.where(AuditLog.action == action)
    if since:
        statement = statement.where(AuditLog.occurred_at >= since)
    if until:
        statement = statement.where(AuditLog.occurred_at <= until)
    return list(db.scalars(statement))
