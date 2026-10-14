from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import require_roles
from app.models.academic import Course, CourseAllocation, Section
from app.models.attendance import Attendance, AttendanceStatus
from app.models.audit import SystemSetting
from app.models.timetable import Lecture
from app.models.user import User, UserRole
from app.schemas.analytics import Defaulter
from app.services.analytics import defaulter_list

router = APIRouter(prefix="/faculty/analytics", tags=["faculty analytics"])
Faculty = Depends(require_roles(UserRole.FACULTY.value))


@router.get("/allocations")
def allocations(faculty: User = Faculty, db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(
        select(CourseAllocation.id, Course.code, Course.name, Section.name)
        .join(Course, Course.id == CourseAllocation.course_id)
        .join(Section, Section.id == CourseAllocation.section_id)
        .where(CourseAllocation.faculty_id == faculty.id, CourseAllocation.is_active.is_(True))
        .order_by(Course.code, Section.name)
    ).all()
    return [
        {
            "allocation_id": row[0],
            "course_code": row[1],
            "course_name": row[2],
            "section_name": row[3],
        }
        for row in rows
    ]


@router.get("/trend")
def attendance_trend(
    allocation_id: UUID,
    faculty: User = Faculty,
    db: Session = Depends(get_db),
) -> list[dict]:
    allocation = db.get(CourseAllocation, allocation_id)
    if not allocation:
        raise HTTPException(404, "Course allocation not found")
    if allocation.faculty_id != faculty.id:
        raise HTTPException(403, "You are not assigned to this course")
    attended = func.sum(
        case((Attendance.status.in_([AttendanceStatus.PRESENT, AttendanceStatus.LATE]), 1), else_=0)
    )
    rows = db.execute(
        select(Lecture.id, Lecture.starts_at, func.count(Attendance.id), attended)
        .outerjoin(Attendance, Attendance.lecture_id == Lecture.id)
        .where(Lecture.allocation_id == allocation_id)
        .group_by(Lecture.id, Lecture.starts_at)
        .order_by(Lecture.starts_at.desc())
        .limit(30)
    ).all()
    return [
        {
            "lecture_id": row[0],
            "starts_at": row[1].isoformat(),
            "recorded": row[2],
            "attended": int(row[3] or 0),
            "attendance_percentage": round(int(row[3] or 0) / row[2] * 100, 1) if row[2] else 0.0,
        }
        for row in reversed(rows)
    ]


@router.get("/defaulters", response_model=list[Defaulter])
def defaulters(
    allocation_id: UUID,
    threshold: float | None = Query(default=None, ge=0, le=100),
    faculty: User = Faculty,
    db: Session = Depends(get_db),
) -> list[dict]:
    allocation = db.get(CourseAllocation, allocation_id)
    if not allocation:
        raise HTTPException(404, "Course allocation not found")
    if allocation.faculty_id != faculty.id:
        raise HTTPException(403, "You are not assigned to this course")
    try:
        setting = db.get(SystemSetting, "attendance_threshold")
        applied_threshold = (
            threshold
            if threshold is not None
            else float(setting.value["percentage"])
            if setting
            else 75.0
        )
        return defaulter_list(db, allocation_id, applied_threshold)
    except ValueError as error:
        raise HTTPException(422, str(error)) from None


@router.get("/defaulters/pdf")
def export_defaulters_pdf(
    allocation_id: UUID,
    threshold: float | None = Query(default=None, ge=0, le=100),
    faculty: User = Faculty,
    db: Session = Depends(get_db),
) -> Response:
    from fastapi.responses import Response
    from app.services.reports import generate_defaulters_pdf

    allocation = db.get(CourseAllocation, allocation_id)
    if not allocation:
        raise HTTPException(404, "Course allocation not found")
    if allocation.faculty_id != faculty.id:
        raise HTTPException(403, "You are not assigned to this course")
    setting = db.get(SystemSetting, "attendance_threshold")
    applied_threshold = (
        threshold
        if threshold is not None
        else float(setting.value["percentage"])
        if setting
        else 75.0
    )
    pdf_bytes = generate_defaulters_pdf(db, allocation_id, applied_threshold)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="defaulters_{allocation_id}_{int(applied_threshold)}.pdf"'
        },
    )


@router.get("/student/{student_id}/pdf")
def export_student_report_pdf(
    student_id: UUID,
    faculty: User = Faculty,
    db: Session = Depends(get_db),
) -> Response:
    from fastapi.responses import Response
    from app.services.reports import generate_student_attendance_pdf

    student = db.get(User, student_id)
    if not student:
        raise HTTPException(404, "Student not found")
    pdf_bytes = generate_student_attendance_pdf(db, student_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="attendance_report_{student.institutional_id}.pdf"'
        },
    )


@router.post("/defaulters/notify")
def notify_defaulters_endpoint(
    allocation_id: UUID,
    threshold: float | None = Query(default=None, ge=0, le=100),
    faculty: User = Faculty,
    db: Session = Depends(get_db),
) -> dict[str, int]:
    from app.services.notifications import enqueue_in_app_notification

    allocation = db.get(CourseAllocation, allocation_id)
    if not allocation:
        raise HTTPException(404, "Course allocation not found")
    if allocation.faculty_id != faculty.id:
        raise HTTPException(403, "You are not assigned to this course")
    course = db.get(Course, allocation.course_id)
    setting = db.get(SystemSetting, "attendance_threshold")
    applied_threshold = (
        threshold
        if threshold is not None
        else float(setting.value["percentage"])
        if setting
        else 75.0
    )
    defaulters = defaulter_list(db, allocation_id, applied_threshold)
    course_name = f"{course.code} ({course.name})" if course else "your course"
    for row in defaulters:
        enqueue_in_app_notification(
            user_id=row["student_id"],
            title="Attendance Warning: Defaulter Notice",
            message=(
                f"Your attendance in {course_name} is currently {row['attendance_percentage']:.1f}%, "
                f"which is below the required {applied_threshold:.0f}%. "
                f"Please submit regularization requests or contact Prof. {faculty.full_name}."
            ),
            payload={"allocation_id": str(allocation_id), "type": "DEFAULTER_NOTICE"},
        )
    return {"notified_count": len(defaulters)}
