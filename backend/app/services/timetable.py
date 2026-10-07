from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.academic import Classroom, CourseAllocation
from app.models.timetable import Lecture, LectureStatus, TimetableEntry

COLLEGE_TIMEZONE = ZoneInfo("Asia/Kolkata")


class ScheduleConflict(Exception):
    pass


def validate_timetable_entry(db: Session, entry: TimetableEntry) -> None:
    if entry.is_active is False:
        return
    allocation = db.get(CourseAllocation, entry.allocation_id)
    if not allocation or not allocation.is_active:
        raise ValueError("The timetable entry must reference an active allocation")
    classroom = db.get(Classroom, entry.classroom_id)
    if not classroom or not classroom.is_active:
        raise ValueError("The timetable entry must reference an active classroom")
    if entry.effective_until and entry.effective_until < entry.effective_from:
        raise ValueError("The timetable effective date range is invalid")

    candidates = db.scalars(
        select(TimetableEntry).where(
            TimetableEntry.is_active.is_(True),
            TimetableEntry.weekday == entry.weekday,
            TimetableEntry.id != entry.id,
        )
    ).all()
    for other in candidates:
        date_overlap = (
            other.effective_until is None or other.effective_until >= entry.effective_from
        ) and (entry.effective_until is None or entry.effective_until >= other.effective_from)
        time_overlap = other.starts_at < entry.ends_at and entry.starts_at < other.ends_at
        if not date_overlap or not time_overlap:
            continue
        other_allocation = db.get(CourseAllocation, other.allocation_id)
        if not other_allocation:
            continue
        if other.classroom_id == entry.classroom_id:
            raise ScheduleConflict("The classroom is already scheduled during this time")
        if other_allocation.faculty_id == allocation.faculty_id:
            raise ScheduleConflict("The faculty member is already scheduled during this time")


def generate_lectures(db: Session, entry: TimetableEntry, through: date) -> int:
    if not entry.is_active:
        raise ValueError("Cannot generate lectures for an inactive timetable entry")
    if through < entry.effective_from:
        return 0
    if (through - entry.effective_from).days > 366:
        raise ValueError("Generate lectures for no more than one year at a time")
    end_date = min(through, entry.effective_until) if entry.effective_until else through
    current = entry.effective_from
    while current.weekday() != entry.weekday:
        current += timedelta(days=1)
    created = 0
    while current <= end_date:
        starts = datetime.combine(current, entry.starts_at, tzinfo=COLLEGE_TIMEZONE)
        if not db.scalar(
            select(Lecture.id).where(
                Lecture.allocation_id == entry.allocation_id,
                Lecture.starts_at == starts,
            )
        ):
            ends = datetime.combine(current, entry.ends_at, tzinfo=COLLEGE_TIMEZONE)
            db.add(
                Lecture(
                    allocation_id=entry.allocation_id,
                    timetable_entry_id=entry.id,
                    classroom_id=entry.classroom_id,
                    starts_at=starts,
                    ends_at=ends,
                    status=LectureStatus.SCHEDULED,
                )
            )
            created += 1
        current += timedelta(days=7)
    return created


def cancel_lecture(db: Session, lecture: Lecture, reason: str) -> None:
    if lecture.status == LectureStatus.CONDUCTED:
        raise ValueError("A conducted lecture cannot be cancelled")
    if lecture.status == LectureStatus.CANCELLED:
        return
    lecture.status = LectureStatus.CANCELLED
    lecture.cancellation_reason = reason
