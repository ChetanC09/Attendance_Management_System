from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
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


def import_timetable_csv(
    db: Session, csv_text: str, generate_through: date | None = None
) -> dict:
    """Import timetable entries from CSV text and optionally generate dated lectures."""
    import csv
    import io
    from datetime import time
    from app.models.academic import Course, Section

    day_map = {
        "mon": 0, "monday": 0, "0": 0,
        "tue": 1, "tuesday": 1, "1": 1,
        "wed": 2, "wednesday": 2, "2": 2,
        "thu": 3, "thursday": 3, "3": 3,
        "fri": 4, "friday": 4, "4": 4,
        "sat": 5, "saturday": 5, "5": 5,
        "sun": 6, "sunday": 6, "6": 6,
    }

    reader = csv.DictReader(io.StringIO(csv_text.strip()))
    imported_count = 0
    lectures_count = 0
    errors: list[dict] = []

    for index, row in enumerate(reader, start=1):
        try:
            # Normalize keys to lower case
            clean_row = {k.strip().lower(): v.strip() for k, v in row.items() if k}
            course_code = clean_row.get("course_code") or clean_row.get("course")
            section_name = clean_row.get("section_name") or clean_row.get("section")
            room_code = clean_row.get("classroom_code") or clean_row.get("classroom") or clean_row.get("room")
            weekday_str = str(clean_row.get("weekday", "")).lower()
            starts_at_str = clean_row.get("starts_at") or clean_row.get("start_time")
            ends_at_str = clean_row.get("ends_at") or clean_row.get("end_time")
            from_str = clean_row.get("effective_from") or clean_row.get("from_date")
            until_str = clean_row.get("effective_until") or clean_row.get("until_date")

            if not all([course_code, section_name, room_code, weekday_str, starts_at_str, ends_at_str, from_str]):
                errors.append({"row": index, "error": "Missing required fields (course, section, classroom, weekday, starts_at, ends_at, effective_from)"})
                continue

            weekday = day_map.get(weekday_str)
            if weekday is None:
                errors.append({"row": index, "error": f"Invalid weekday: {weekday_str}"})
                continue

            # Lookup allocation
            course = db.scalar(select(Course).where(func.lower(Course.code) == course_code.lower()))
            if not course:
                errors.append({"row": index, "error": f"Course code not found: {course_code}"})
                continue

            section = db.scalar(select(Section).where(func.lower(Section.name) == section_name.lower()))
            if not section:
                errors.append({"row": index, "error": f"Section not found: {section_name}"})
                continue

            allocation = db.scalar(
                select(CourseAllocation).where(
                    CourseAllocation.course_id == course.id,
                    CourseAllocation.section_id == section.id,
                    CourseAllocation.is_active.is_(True),
                )
            )
            if not allocation:
                errors.append({"row": index, "error": f"No active course allocation for {course_code} in section {section_name}"})
                continue

            classroom = db.scalar(select(Classroom).where(func.lower(Classroom.code) == room_code.lower()))
            if not classroom:
                errors.append({"row": index, "error": f"Classroom code not found: {room_code}"})
                continue

            # Parse times
            start_parts = [int(p) for p in starts_at_str.split(":")[:2]]
            end_parts = [int(p) for p in ends_at_str.split(":")[:2]]
            starts_time = time(start_parts[0], start_parts[1])
            ends_time = time(end_parts[0], end_parts[1])

            effective_from = datetime.strptime(from_str, "%Y-%m-%d").date()
            effective_until = datetime.strptime(until_str, "%Y-%m-%d").date() if until_str else None

            entry = TimetableEntry(
                allocation_id=allocation.id,
                classroom_id=classroom.id,
                weekday=weekday,
                starts_at=starts_time,
                ends_at=ends_time,
                effective_from=effective_from,
                effective_until=effective_until,
                is_active=True,
            )
            validate_timetable_entry(db, entry)
            db.add(entry)
            db.flush()
            imported_count += 1

            if generate_through:
                lectures_count += generate_lectures(db, entry, generate_through)

        except Exception as exc:
            errors.append({"row": index, "error": str(exc)})

    db.commit()
    return {
        "imported_entries": imported_count,
        "generated_lectures": lectures_count,
        "errors": errors,
    }
