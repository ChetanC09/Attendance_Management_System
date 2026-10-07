from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import require_roles
from app.models.academic import CourseAllocation
from app.models.timetable import Lecture, TimetableEntry
from app.models.user import User, UserRole
from app.schemas.academic import LectureResponse, TimetableEntryResponse

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
