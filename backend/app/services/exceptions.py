import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.academic import CourseAllocation, StudentProfile
from app.models.attendance import Attendance, AttendanceSource, AttendanceStatus
from app.models.exceptions import LeaveRequest, RequestStatus, RequestType
from app.models.timetable import Lecture, LectureStatus
from app.models.user import User
from app.services.audit import record_audit


class RequestRuleError(Exception):
    pass


def create_request(
    db: Session, student: User, lecture_id: uuid.UUID, request_type: RequestType, reason: str
) -> LeaveRequest:
    lecture = db.get(Lecture, lecture_id)
    profile = db.get(StudentProfile, student.id)
    if not lecture or not profile:
        raise RequestRuleError("Lecture or student academic profile not found")
    allocation = db.get(CourseAllocation, lecture.allocation_id)
    if not allocation or allocation.section_id != profile.section_id:
        raise RequestRuleError("Student is not enrolled in this lecture")
    if request_type == RequestType.REGULARIZATION:
        if lecture.status != LectureStatus.CONDUCTED:
            raise RequestRuleError("Regularization is only available after a conducted lecture")
        attendance = db.scalar(
            select(Attendance).where(
                Attendance.student_id == student.id,
                Attendance.lecture_id == lecture.id,
            )
        )
        if not attendance or attendance.status not in {
            AttendanceStatus.ABSENT,
            AttendanceStatus.EXCUSED,
        }:
            raise RequestRuleError("Only an absent or excused lecture can be regularized")
    request = LeaveRequest(
        student_id=student.id,
        lecture_id=lecture_id,
        request_type=request_type,
        status=RequestStatus.PENDING,
        reason=reason,
    )
    db.add(request)
    db.flush()
    record_audit(
        db,
        actor_id=student.id,
        action="CREATE",
        resource_type="leave_request",
        resource_id=str(request.id),
        after={"status": request.status.value, "type": request_type.value},
    )
    db.commit()
    db.refresh(request)
    return request


def review_request(
    db: Session,
    faculty: User,
    request_id: uuid.UUID,
    approve: bool,
    reason: str | None,
) -> LeaveRequest:
    request = db.get(LeaveRequest, request_id)
    if not request:
        raise RequestRuleError("Request not found")
    if not request.lecture_id:
        raise RequestRuleError("The request is not linked to a lecture")
    lecture = db.get(Lecture, request.lecture_id)
    allocation = db.get(CourseAllocation, lecture.allocation_id) if lecture else None
    if not allocation or allocation.faculty_id != faculty.id:
        raise RequestRuleError("You are not assigned to review this request")
    if request.status != RequestStatus.PENDING:
        raise RequestRuleError("This request has already been reviewed")
    if not approve and not reason:
        raise RequestRuleError("A rejection reason is required")

    before = {"status": request.status.value}
    request.status = RequestStatus.APPROVED if approve else RequestStatus.REJECTED
    request.reviewed_by = faculty.id
    request.review_reason = reason
    request.reviewed_at = datetime.now(UTC)
    if approve:
        attendance = db.scalar(
            select(Attendance).where(
                Attendance.student_id == request.student_id,
                Attendance.lecture_id == request.lecture_id,
            )
        )
        target_status = (
            AttendanceStatus.PRESENT
            if request.request_type == RequestType.REGULARIZATION
            else AttendanceStatus.EXCUSED
        )
        if attendance:
            if request.request_type == RequestType.REGULARIZATION and attendance.status not in {
                AttendanceStatus.ABSENT,
                AttendanceStatus.EXCUSED,
            }:
                raise RequestRuleError("Attendance is no longer eligible for regularization")
            if attendance.status not in {AttendanceStatus.PRESENT, AttendanceStatus.LATE}:
                attendance.status = target_status
                attendance.source = AttendanceSource.REGULARIZATION
                attendance.marked_by = faculty.id
                attendance.reason = (
                    f"Approved {request.request_type.value.lower()} request {request.id}"
                )
                attendance.marked_at = datetime.now(UTC)
        elif (
            request.request_type == RequestType.REGULARIZATION
            or lecture.status == LectureStatus.CONDUCTED
        ):
            db.add(
                Attendance(
                    student_id=request.student_id,
                    lecture_id=request.lecture_id,
                    status=target_status,
                    source=AttendanceSource.REGULARIZATION,
                    marked_by=faculty.id,
                    reason=f"Approved {request.request_type.value.lower()} request {request.id}",
                )
            )
    record_audit(
        db,
        actor_id=faculty.id,
        action="APPROVE" if approve else "REJECT",
        resource_type="leave_request",
        resource_id=str(request.id),
        before=before,
        after={"status": request.status.value, "review_reason": reason},
        reason=reason,
    )
    db.commit()
    db.refresh(request)
    return request
