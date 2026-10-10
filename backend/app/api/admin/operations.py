from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.dependencies.auth import require_roles
from app.models.academic import Course, CourseAllocation, Department
from app.models.attendance import (
    Attendance,
    AttendanceSession,
    AttendanceSessionStatus,
    AttendanceStatus,
)
from app.models.audit import AuditLog, SystemSetting
from app.models.exceptions import LeaveRequest, RequestStatus
from app.models.timetable import Lecture
from app.models.user import User, UserRole
from app.schemas.admin import AuditLogResponse
from app.services.analytics import defaulter_list
from app.services.audit import record_audit

router = APIRouter(prefix="/admin", tags=["administration"])
Admin = Depends(require_roles(UserRole.ADMIN.value))


@router.get("/overview")
def system_overview(_: User = Admin, db: Session = Depends(get_db)) -> dict[str, int | float]:
    """Operational totals for the administrator dashboard."""
    total_marks = db.scalar(select(func.count(Attendance.id))) or 0
    attended_marks = (
        db.scalar(
            select(func.count(Attendance.id)).where(
                Attendance.status.in_(
                    [AttendanceStatus.PRESENT, AttendanceStatus.LATE, AttendanceStatus.EXCUSED]
                )
            )
        )
        or 0
    )
    pending = (
        db.scalar(
            select(func.count(LeaveRequest.id)).where(LeaveRequest.status == RequestStatus.PENDING)
        )
        or 0
    )
    open_sessions = (
        db.scalar(
            select(func.count(AttendanceSession.id)).where(
                AttendanceSession.status == AttendanceSessionStatus.OPEN
            )
        )
        or 0
    )
    active_users = db.scalar(select(func.count(User.id)).where(User.is_active.is_(True))) or 0
    allocations = list(
        db.scalars(select(CourseAllocation).where(CourseAllocation.is_active.is_(True)))
    )
    setting = db.get(SystemSetting, "attendance_threshold")
    threshold = float(setting.value["percentage"]) if setting else 75.0
    low_attendance = sum(
        len(defaulter_list(db, allocation.id, threshold)) for allocation in allocations
    )
    return {
        "departments": db.scalar(select(func.count(Department.id))) or 0,
        "courses": db.scalar(select(func.count(Course.id))) or 0,
        "lectures": db.scalar(select(func.count(Lecture.id))) or 0,
        "attendance_records": total_marks,
        "recorded_attendance_percentage": round(attended_marks / total_marks * 100, 1)
        if total_marks
        else 0.0,
        "pending_requests": pending,
        "open_attendance_sessions": open_sessions,
        "active_users": active_users,
        "low_attendance_course_records": low_attendance,
    }


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
