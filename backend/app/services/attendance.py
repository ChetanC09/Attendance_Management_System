import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.academic import CourseAllocation, StudentProfile
from app.models.attendance import (
    Attendance,
    AttendanceSession,
    AttendanceSessionStatus,
    AttendanceSource,
    AttendanceStatus,
)
from app.models.exceptions import LeaveRequest, RequestStatus, RequestType
from app.models.timetable import Lecture, LectureStatus
from app.models.user import User, UserRole
from app.services.audit import record_audit


class AttendanceRuleError(Exception):
    pass


def _authorized_lecture(db: Session, lecture_id: uuid.UUID, faculty_id: uuid.UUID) -> Lecture:
    lecture = db.get(Lecture, lecture_id)
    if not lecture:
        raise AttendanceRuleError("Lecture not found")
    allocation = db.get(CourseAllocation, lecture.allocation_id)
    if not allocation or allocation.faculty_id != faculty_id or not allocation.is_active:
        raise AttendanceRuleError("You are not assigned to this lecture")
    return lecture


def create_attendance_session(
    db: Session, faculty: User, lecture_id: uuid.UUID
) -> AttendanceSession:
    lecture = _authorized_lecture(db, lecture_id, faculty.id)
    if lecture.status != LectureStatus.SCHEDULED:
        raise AttendanceRuleError("Attendance can only be opened for a scheduled lecture")
    existing = db.scalar(
        select(AttendanceSession).where(
            AttendanceSession.lecture_id == lecture_id,
            AttendanceSession.status == AttendanceSessionStatus.OPEN,
        )
    )
    if existing:
        raise AttendanceRuleError("An attendance session is already open for this lecture")
    session = AttendanceSession(lecture_id=lecture_id, opened_by=faculty.id)
    db.add(session)
    try:
        db.flush()
        record_audit(
            db,
            actor_id=faculty.id,
            action="OPEN",
            resource_type="attendance_session",
            resource_id=str(session.id),
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AttendanceRuleError(
            "An attendance session is already open for this lecture"
        ) from None
    db.refresh(session)
    return session


def get_authorized_session(db: Session, faculty: User, session_id: uuid.UUID) -> AttendanceSession:
    session = db.get(AttendanceSession, session_id)
    if not session:
        raise AttendanceRuleError("Attendance session not found")
    _authorized_lecture(db, session.lecture_id, faculty.id)
    return session


def record_attendance(
    db: Session,
    faculty: User,
    session: AttendanceSession,
    student_id: uuid.UUID,
    attendance_status: AttendanceStatus,
    reason: str | None,
    source: AttendanceSource = AttendanceSource.MANUAL,
) -> Attendance:
    if session.status != AttendanceSessionStatus.OPEN:
        raise AttendanceRuleError("This attendance session is closed")
    lecture = _authorized_lecture(db, session.lecture_id, faculty.id)
    allocation = db.get(CourseAllocation, lecture.allocation_id)
    student = db.get(User, student_id)
    profile = db.get(StudentProfile, student_id)
    if not student or student.role != UserRole.STUDENT or not student.is_active:
        raise AttendanceRuleError("Student account is not valid")
    if not profile or profile.section_id != allocation.section_id:
        raise AttendanceRuleError("Student is not enrolled in this section")
    if db.scalar(
        select(Attendance.id).where(
            Attendance.student_id == student_id, Attendance.lecture_id == lecture.id
        )
    ):
        raise AttendanceRuleError("Attendance has already been recorded for this student")
    row = Attendance(
        student_id=student_id,
        lecture_id=lecture.id,
        session_id=session.id,
        status=attendance_status,
        source=source,
        marked_by=faculty.id,
        reason=reason,
    )
    db.add(row)
    try:
        db.flush()
        record_audit(
            db,
            actor_id=faculty.id,
            action="CREATE",
            resource_type="attendance",
            resource_id=str(row.id),
            after={
                "student_id": str(student_id),
                "lecture_id": str(lecture.id),
                "session_id": str(session.id),
                "status": attendance_status.value,
                "source": source.value,
                "reason": reason,
            },
            reason=reason,
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AttendanceRuleError("Attendance has already been recorded for this student") from None
    db.refresh(row)
    return row


def modify_attendance(
    db: Session, faculty: User, attendance_id: uuid.UUID, new_status: AttendanceStatus, reason: str
) -> Attendance:
    row = db.get(Attendance, attendance_id)
    if not row:
        raise AttendanceRuleError("Attendance record not found")
    _authorized_lecture(db, row.lecture_id, faculty.id)
    if row.status == new_status:
        raise AttendanceRuleError("Attendance already has that status")
    before = {"status": row.status.value, "reason": row.reason}
    row.status = new_status
    row.reason = reason
    row.source = AttendanceSource.MANUAL
    row.marked_by = faculty.id
    row.marked_at = datetime.now(UTC)
    record_audit(
        db,
        actor_id=faculty.id,
        action="MODIFY",
        resource_type="attendance",
        resource_id=str(row.id),
        before=before,
        after={"status": new_status.value, "reason": reason},
        reason=reason,
    )
    db.commit()
    db.refresh(row)
    return row


def close_attendance_session(
    db: Session, faculty: User, session: AttendanceSession
) -> AttendanceSession:
    if session.status == AttendanceSessionStatus.CLOSED:
        return session
    lecture = _authorized_lecture(db, session.lecture_id, faculty.id)
    allocation = db.get(CourseAllocation, lecture.allocation_id)
    roster = db.scalars(
        select(StudentProfile.user_id)
        .join(User, User.id == StudentProfile.user_id)
        .where(StudentProfile.section_id == allocation.section_id, User.is_active.is_(True))
    ).all()
    present_ids = set(
        db.scalars(select(Attendance.student_id).where(Attendance.lecture_id == lecture.id)).all()
    )
    approved_leave_ids = set(
        db.scalars(
            select(LeaveRequest.student_id).where(
                LeaveRequest.lecture_id == lecture.id,
                LeaveRequest.request_type == RequestType.LEAVE,
                LeaveRequest.status == RequestStatus.APPROVED,
            )
        ).all()
    )
    for student_id in roster:
        if student_id not in present_ids:
            db.add(
                Attendance(
                    student_id=student_id,
                    lecture_id=lecture.id,
                    session_id=session.id,
                    status=AttendanceStatus.EXCUSED
                    if student_id in approved_leave_ids
                    else AttendanceStatus.ABSENT,
                    source=AttendanceSource.MANUAL,
                    marked_by=faculty.id,
                    reason="Approved leave"
                    if student_id in approved_leave_ids
                    else "Unmarked at session close",
                )
            )
    session.status = AttendanceSessionStatus.CLOSED
    session.closed_at = datetime.now(UTC)
    lecture.status = LectureStatus.CONDUCTED
    record_audit(
        db,
        actor_id=faculty.id,
        action="CLOSE",
        resource_type="attendance_session",
        resource_id=str(session.id),
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AttendanceRuleError(
            "Could not close the attendance session due to a concurrent update"
        ) from None
    db.refresh(session)
    return session
