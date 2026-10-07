from datetime import date, time
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.models.academic import Classroom, CourseAllocation
from app.models.timetable import TimetableEntry
from app.services.timetable import ScheduleConflict, validate_timetable_entry


def test_timetable_rejects_overlapping_classroom_use() -> None:
    allocation_id, classroom_id = uuid4(), uuid4()
    allocation = CourseAllocation(id=allocation_id, faculty_id=uuid4(), is_active=True)
    classroom = Classroom(id=classroom_id, is_active=True)
    entry = TimetableEntry(
        allocation_id=allocation_id,
        classroom_id=classroom_id,
        weekday=1,
        starts_at=time(10),
        ends_at=time(11),
        effective_from=date(2026, 9, 1),
        effective_until=None,
    )
    other = TimetableEntry(
        id=uuid4(),
        allocation_id=uuid4(),
        classroom_id=classroom_id,
        weekday=1,
        starts_at=time(10, 30),
        ends_at=time(11, 30),
        effective_from=date(2026, 9, 1),
        effective_until=None,
        is_active=True,
    )
    db = MagicMock()
    db.get.side_effect = lambda model, key: {
        (CourseAllocation, allocation_id): allocation,
        (Classroom, classroom_id): classroom,
        (CourseAllocation, other.allocation_id): CourseAllocation(
            id=other.allocation_id, faculty_id=uuid4(), is_active=True
        ),
    }[(model, key)]
    db.scalars.return_value.all.return_value = [other]

    with pytest.raises(ScheduleConflict, match="classroom"):
        validate_timetable_entry(db, entry)


def test_deactivating_schedule_skips_conflict_validation() -> None:
    entry = TimetableEntry(is_active=False)
    db = MagicMock()

    validate_timetable_entry(db, entry)

    db.get.assert_not_called()
    db.scalars.assert_not_called()
