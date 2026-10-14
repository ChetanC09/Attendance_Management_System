"""Student self-service face check-in endpoint.

Workflow:
  1. Validate that the request IP is within an allowed college subnet
     (configured via AMS_ALLOWED_CHECKIN_SUBNETS). If the list is empty the
     restriction is skipped (development / unconfigured mode).
  2. Run face recognition against the student's enrolled face profile.
  3. Confirm the recognised face matches the authenticated student's profile.
  4. Locate the active attendance session for the student's current lecture
     (a lecture whose time window overlaps now and that has an open session).
  5. Record the student as PRESENT via the vision source.
"""

from __future__ import annotations

import ipaddress
import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.dependencies.auth import require_roles
from app.models.academic import Course, CourseAllocation, StudentProfile
from app.models.attendance import (
    Attendance,
    AttendanceSession,
    AttendanceSessionStatus,
    AttendanceSource,
    AttendanceStatus,
)
from app.models.timetable import Lecture
from app.models.user import User, UserRole
from app.services.audit import record_audit
from app.services.network import get_client_ip, is_ip_allowed_for_session
from app.vision.schemas import RecognitionState
from app.vision.service import recognize_image

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/student/checkin", tags=["student checkin"])
Student = Depends(require_roles(UserRole.STUDENT.value))


def _client_ip(request: Request) -> str:
    """Return the real client IP using the shared network service."""
    return get_client_ip(request)


def _ip_allowed(ip_str: str, db: Session | None = None, session_id: uuid.UUID | None = None) -> tuple[bool, str, dict]:
    """Return whether client IP is allowed, utilizing session geofencing and demo bypass."""
    if not db:
        return True, "Allowed", {}
    return is_ip_allowed_for_session(db, session_id, ip_str)


def _active_lecture_and_session(
    db: Session, section_id: uuid.UUID, now: datetime
) -> tuple[Lecture | None, AttendanceSession | None, Course | None]:
    """Return the ongoing lecture + its open session + course for the given section."""
    from app.models.timetable import LectureStatus

    # 1. First look for any currently OPEN attendance session for this section
    open_session = db.scalar(
        select(AttendanceSession)
        .join(Lecture, Lecture.id == AttendanceSession.lecture_id)
        .join(CourseAllocation, CourseAllocation.id == Lecture.allocation_id)
        .where(
            CourseAllocation.section_id == section_id,
            AttendanceSession.status == AttendanceSessionStatus.OPEN,
            Lecture.status != LectureStatus.CANCELLED,
        )
        .order_by(AttendanceSession.opened_at.desc())
        .limit(1)
    )
    if open_session:
        lecture = db.get(Lecture, open_session.lecture_id)
        allocation = db.get(CourseAllocation, lecture.allocation_id) if lecture else None
        course = db.get(Course, allocation.course_id) if allocation else None
        return lecture, open_session, course

    # 2. If no open session, look for the scheduled lecture happening right now
    lecture = db.scalar(
        select(Lecture)
        .join(CourseAllocation, CourseAllocation.id == Lecture.allocation_id)
        .where(
            CourseAllocation.section_id == section_id,
            Lecture.starts_at <= now,
            Lecture.ends_at >= now,
            Lecture.status != LectureStatus.CANCELLED,
        )
        .order_by(Lecture.starts_at.desc())
        .limit(1)
    )
    if not lecture:
        return None, None, None

    allocation = db.get(CourseAllocation, lecture.allocation_id)
    course = db.get(Course, allocation.course_id) if allocation else None
    return lecture, None, course


@router.get("/active-session")
def get_active_session(
    request: Request,
    student: User = Student,
    db: Session = Depends(get_db),
) -> dict:
    """Return the currently open attendance session for the student's ongoing lecture, if any."""
    now = datetime.now(UTC)
    profile = db.scalar(select(StudentProfile).where(StudentProfile.user_id == student.id))
    if not profile:
        return {"session": None, "message": "No student profile found"}

    lecture, session, course = _active_lecture_and_session(db, profile.section_id, now)
    client_ip = _client_ip(request)
    is_allowed, reason, net_info = _ip_allowed(client_ip, db, session.id if session else None)
    network_verif = {
        "client_ip": client_ip,
        "allowed": is_allowed,
        "reason": reason,
        "enforced": net_info.get("enforced", True),
        "bound_subnet": net_info.get("bound_subnet", "Campus Wi-Fi"),
    }

    if not lecture:
        return {
            "session": None,
            "message": "No active lecture right now for your section",
            "network_verification": network_verif,
        }
    if not session:
        return {
            "session": None,
            "message": "Faculty has not opened an attendance session yet",
            "network_verification": network_verif,
        }

    existing = db.scalar(
        select(Attendance).where(
            Attendance.student_id == student.id,
            Attendance.lecture_id == lecture.id,
        )
    )

    return {
        "session": {
            "id": str(session.id),
            "lecture_id": str(lecture.id),
            "course_name": course.name if course else "Unknown course",
            "course_code": course.code if course else "",
            "starts_at": lecture.starts_at.isoformat(),
            "ends_at": lecture.ends_at.isoformat(),
        },
        "already_marked": existing is not None,
        "existing_status": existing.status.value if existing else None,
        "message": "Active session found",
        "network_verification": network_verif,
    }


@router.post("")
async def face_checkin(
    request: Request,
    image: UploadFile = File(...),
    student: User = Student,
    db: Session = Depends(get_db),
) -> dict:
    """Student self-service check-in via face recognition.

    The student's device must be on the configured college subnet or
    match the active classroom Wi-Fi network.
    """
    # --- 1. Subnet / IP validation ---
    client_ip = _client_ip(request)
    is_allowed, reason, net_info = _ip_allowed(client_ip, db)
    if not is_allowed:
        raise HTTPException(
            403,
            f"{reason} Connect to the classroom Wi-Fi and try again.",
        )

    # --- 2. Image validation ---
    if image.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(415, "Image must be JPEG, PNG, or WebP")
    content = await image.read(settings.max_document_bytes + 1)
    if not content or len(content) > settings.max_document_bytes:
        raise HTTPException(413, "Image is empty or exceeds the configured size limit")

    # --- 3. Face recognition ---
    result = recognize_image(content, db, settings.vision_minimum_confidence)
    if result.state == RecognitionState.MULTIPLE_FACES:
        raise HTTPException(422, "Multiple faces detected. Please position only your face in the frame.")
    if result.state in (RecognitionState.UNKNOWN, RecognitionState.LOW_CONFIDENCE):
        raise HTTPException(
            422,
            "Face not recognised. Ensure good lighting and look directly at the camera. "
            "If this keeps failing, re-enrol your face from Profile settings.",
        )
    if result.state == RecognitionState.ERROR:
        raise HTTPException(503, result.message or "Vision service is currently unavailable")
    if result.state != RecognitionState.RECOGNIZED or not result.student_id:
        raise HTTPException(422, "Face not recognised")

    # --- 4. Confirm the recognised face belongs to this student ---
    if result.student_id != student.id:
        raise HTTPException(
            403,
            "The face in the image does not match your enrolled profile. "
            "Please use your own device and your own face.",
        )

    # --- 5. Find the active lecture and session ---
    now = datetime.now(UTC)
    profile = db.scalar(select(StudentProfile).where(StudentProfile.user_id == student.id))
    if not profile:
        raise HTTPException(404, "Student profile not found. Contact admin.")

    lecture, session, course = _active_lecture_and_session(db, profile.section_id, now)
    if not lecture:
        raise HTTPException(404, "No active lecture right now for your section")
    if not session:
        raise HTTPException(
            404,
            "Your faculty has not opened an attendance session yet. Please wait.",
        )

    # --- 6. Check for duplicate ---
    existing = db.scalar(
        select(Attendance).where(
            Attendance.student_id == student.id,
            Attendance.lecture_id == lecture.id,
        )
    )
    if existing:
        raise HTTPException(409, "Your attendance has already been recorded for this lecture")

    # --- 7. Record attendance directly (student self-checkin, not faculty) ---
    row = Attendance(
        student_id=student.id,
        lecture_id=lecture.id,
        session_id=session.id,
        status=AttendanceStatus.PRESENT,
        source=AttendanceSource.VISION,
        marked_by=student.id,  # self-checkin
        reason=None,
    )
    db.add(row)
    try:
        db.flush()
        record_audit(
            db,
            actor_id=student.id,
            action="SELF_CHECKIN",
            resource_type="attendance",
            resource_id=str(row.id),
            after={
                "student_id": str(student.id),
                "lecture_id": str(lecture.id),
                "session_id": str(session.id),
                "status": AttendanceStatus.PRESENT.value,
                "source": AttendanceSource.VISION.value,
                "confidence": result.confidence,
                "client_ip": client_ip,
            },
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Attendance already recorded (concurrent submission)") from None

    db.refresh(row)

    logger.info(
        "Student self-checkin: student_id=%s lecture_id=%s confidence=%.3f ip=%s",
        student.id,
        lecture.id,
        result.confidence or 0,
        client_ip,
    )

    return {
        "status": "recorded",
        "attendance_id": str(row.id),
        "lecture_id": str(lecture.id),
        "course_name": course.name if course else "Unknown",
        "course_code": course.code if course else "",
        "confidence": result.confidence,
        "message": "Attendance recorded successfully! ✓",
    }
