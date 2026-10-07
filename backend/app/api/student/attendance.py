from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import require_roles
from app.models.academic import Course, CourseAllocation, StudentProfile
from app.models.attendance import Attendance
from app.models.audit import SystemSetting
from app.models.timetable import Lecture
from app.models.user import User, UserRole
from app.schemas.analytics import (
    AttendanceHistoryItem,
    AttendanceProjection,
    CourseAttendanceSummary,
    OverallAttendanceSummary,
    RecoveryPlan,
)
from app.services.analytics import course_counts
from app.services.analytics_math import projected_attendance, recovery_plan

router = APIRouter(prefix="/student", tags=["student attendance"])
Student = Depends(require_roles(UserRole.STUDENT.value))


@router.get("/attendance", response_model=list[CourseAttendanceSummary])
def attendance_summary(
    course_id: UUID | None = None,
    student: User = Student,
    db: Session = Depends(get_db),
) -> list[dict]:
    return course_counts(db, student.id, course_id)


@router.get("/analytics/overall", response_model=OverallAttendanceSummary)
def overall_attendance(student: User = Student, db: Session = Depends(get_db)) -> dict:
    summaries = course_counts(db, student.id)
    attended = sum(item["attended_lectures"] for item in summaries)
    conducted = sum(item["conducted_lectures"] for item in summaries)
    return {
        "attended_lectures": attended,
        "conducted_lectures": conducted,
        "attendance_percentage": round(attended / conducted * 100, 2) if conducted else 0.0,
    }


@router.get("/attendance/history", response_model=list[AttendanceHistoryItem])
def attendance_history(
    course_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    student: User = Student,
    db: Session = Depends(get_db),
) -> list[dict]:
    statement = (
        select(Lecture, Course, Attendance)
        .join(CourseAllocation, CourseAllocation.id == Lecture.allocation_id)
        .join(Course, Course.id == CourseAllocation.course_id)
        .outerjoin(
            Attendance,
            (Attendance.lecture_id == Lecture.id) & (Attendance.student_id == student.id),
        )
        .where(
            CourseAllocation.section_id
            == select(StudentProfile.section_id)
            .where(StudentProfile.user_id == student.id)
            .scalar_subquery()
        )
        .order_by(Lecture.starts_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if course_id:
        statement = statement.where(Course.id == course_id)
    rows = db.execute(statement).all()
    return [
        {
            "lecture_id": lecture.id,
            "course_code": course.code,
            "course_name": course.name,
            "starts_at": lecture.starts_at.isoformat(),
            "status": attendance.status.value if attendance else None,
        }
        for lecture, course, attendance in rows
    ]


@router.get("/analytics/recovery", response_model=RecoveryPlan)
def recovery(
    course_id: UUID,
    target_percentage: float | None = Query(default=None, ge=0, le=100),
    student: User = Student,
    db: Session = Depends(get_db),
) -> dict:
    summary = course_counts(db, student.id, course_id)
    if not summary:
        raise HTTPException(404, "Course attendance not found")
    item = summary[0]
    setting = db.get(SystemSetting, "attendance_threshold")
    target = (
        target_percentage
        if target_percentage is not None
        else float(setting.value["percentage"])
        if setting
        else 75.0
    )
    return recovery_plan(item["attended_lectures"], item["conducted_lectures"], target)


@router.get("/analytics/projection", response_model=AttendanceProjection)
def projection(
    course_id: UUID,
    potential_absences: int = Query(default=1, ge=0, le=100),
    student: User = Student,
    db: Session = Depends(get_db),
) -> dict:
    summary = course_counts(db, student.id, course_id)
    if not summary:
        raise HTTPException(404, "Course attendance not found")
    item = summary[0]
    setting = db.get(SystemSetting, "attendance_threshold")
    threshold = float(setting.value["percentage"]) if setting else 75.0
    return projected_attendance(
        item["attended_lectures"], item["conducted_lectures"], potential_absences, threshold
    )
