from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import require_roles
from app.models.academic import Classroom, Course, CourseAllocation
from app.models.timetable import Lecture, TimetableEntry
from app.models.user import User, UserRole
from app.schemas.academic import LectureResponse, TimetableEntryResponse
from app.schemas.analytics import StudentTimetableItem

router = APIRouter(prefix="/faculty", tags=["faculty timetable"])
Faculty = Depends(require_roles(UserRole.FACULTY.value))
COLLEGE_TIMEZONE = ZoneInfo("Asia/Kolkata")


@router.get("/timetable", response_model=list[TimetableEntryResponse])
def get_timetable(faculty: User = Faculty, db: Session = Depends(get_db)) -> list[TimetableEntry]:
    return list(
        db.scalars(
            select(TimetableEntry)
            .join(CourseAllocation, CourseAllocation.id == TimetableEntry.allocation_id)
            .where(CourseAllocation.faculty_id == faculty.id, TimetableEntry.is_active.is_(True))
            .order_by(TimetableEntry.weekday, TimetableEntry.starts_at)
        )
    )


@router.get("/timetable/overview", response_model=list[StudentTimetableItem])
def timetable_overview(faculty: User = Faculty, db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(
        select(TimetableEntry, Course, Classroom)
        .join(CourseAllocation, CourseAllocation.id == TimetableEntry.allocation_id)
        .join(Course, Course.id == CourseAllocation.course_id)
        .join(Classroom, Classroom.id == TimetableEntry.classroom_id)
        .where(CourseAllocation.faculty_id == faculty.id, CourseAllocation.is_active.is_(True), TimetableEntry.is_active.is_(True))
        .order_by(TimetableEntry.weekday, TimetableEntry.starts_at)
    ).all()
    return [
        {"id": entry.id, "allocation_id": entry.allocation_id, "weekday": entry.weekday, "starts_at": entry.starts_at.isoformat(),
         "ends_at": entry.ends_at.isoformat(), "course_code": course.code, "course_name": course.name,
         "classroom_code": classroom.code, "classroom_name": classroom.name, "faculty_name": faculty.full_name}
        for entry, course, classroom in rows
    ]


@router.get("/lectures/today", response_model=list[LectureResponse])
def todays_lectures(faculty: User = Faculty, db: Session = Depends(get_db)) -> list[Lecture]:
    now = datetime.now(COLLEGE_TIMEZONE)
    start = datetime.combine(now.date(), time.min, tzinfo=COLLEGE_TIMEZONE)
    end = start + timedelta(days=1)
    return list(
        db.scalars(
            select(Lecture)
            .join(CourseAllocation, CourseAllocation.id == Lecture.allocation_id)
            .where(
                CourseAllocation.faculty_id == faculty.id,
                Lecture.starts_at >= start,
                Lecture.starts_at < end,
            )
            .order_by(Lecture.starts_at)
        )
    )
