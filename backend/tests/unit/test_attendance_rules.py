from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.academic import CourseAllocation, StudentProfile
from app.models.attendance import AttendanceSession, AttendanceSessionStatus, AttendanceStatus
from app.models.timetable import Lecture, LectureStatus
from app.models.user import User, UserRole
from app.services.attendance import (
    AttendanceRuleError,
    create_attendance_session,
    record_attendance,
)


def test_concurrent_open_session_insert_maps_database_unique_conflict() -> None:
    faculty_id, lecture_id, allocation_id = uuid4(), uuid4(), uuid4()
    faculty = User(id=faculty_id, role=UserRole.FACULTY)
    lecture = Lecture(id=lecture_id, allocation_id=allocation_id, status=LectureStatus.SCHEDULED)
    allocation = CourseAllocation(id=allocation_id, faculty_id=faculty_id, is_active=True)
    db = MagicMock()
    db.get.side_effect = lambda model, _: {
        Lecture: lecture,
        CourseAllocation: allocation,
    }[model]
    db.scalar.return_value = None
    db.flush.side_effect = IntegrityError("insert", {}, RuntimeError("unique violation"))

    with patch("app.services.attendance.record_audit") as record_audit:
        with pytest.raises(AttendanceRuleError, match="already open"):
            create_attendance_session(db, faculty, lecture_id)

    record_audit.assert_not_called()
    db.rollback.assert_called_once()


def test_attendance_is_rejected_when_student_already_has_a_lecture_row() -> None:
    faculty_id, student_id, lecture_id, allocation_id = uuid4(), uuid4(), uuid4(), uuid4()
    faculty = User(id=faculty_id, role=UserRole.FACULTY)
    student = User(id=student_id, role=UserRole.STUDENT, is_active=True)
    session = AttendanceSession(
        id=uuid4(), lecture_id=lecture_id, status=AttendanceSessionStatus.OPEN
    )
    lecture = Lecture(id=lecture_id, allocation_id=allocation_id, status=LectureStatus.SCHEDULED)
    allocation = CourseAllocation(
        id=allocation_id, faculty_id=faculty_id, section_id=uuid4(), is_active=True
    )
    profile = StudentProfile(user_id=student_id, section_id=allocation.section_id)
    db = MagicMock()
    db.get.side_effect = lambda model, _: {
        Lecture: lecture,
        CourseAllocation: allocation,
        User: student,
        StudentProfile: profile,
    }[model]
    db.scalar.return_value = uuid4()

    with patch("app.services.attendance.record_audit"):
        with pytest.raises(AttendanceRuleError, match="already been recorded"):
            record_attendance(db, faculty, session, student_id, AttendanceStatus.PRESENT, None)

    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_manual_attendance_creation_records_audit_with_reason() -> None:
    faculty_id, student_id, lecture_id, allocation_id, session_id = (
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
    )
    faculty = User(id=faculty_id, role=UserRole.FACULTY)
    student = User(id=student_id, role=UserRole.STUDENT, is_active=True)
    session = AttendanceSession(
        id=session_id, lecture_id=lecture_id, status=AttendanceSessionStatus.OPEN
    )
    lecture = Lecture(id=lecture_id, allocation_id=allocation_id, status=LectureStatus.SCHEDULED)
    allocation = CourseAllocation(
        id=allocation_id, faculty_id=faculty_id, section_id=uuid4(), is_active=True
    )
    profile = StudentProfile(user_id=student_id, section_id=allocation.section_id)
    db = MagicMock()
    db.get.side_effect = lambda model, _: {
        Lecture: lecture,
        CourseAllocation: allocation,
        User: student,
        StudentProfile: profile,
    }[model]
    db.scalar.return_value = None

    with patch("app.services.attendance.record_audit") as record_audit:
        record_attendance(
            db,
            faculty,
            session,
            student_id,
            AttendanceStatus.PRESENT,
            "Verified in browser test.",
        )

    record_audit.assert_called_once()
    audit = record_audit.call_args.kwargs
    assert audit["actor_id"] == faculty_id
    assert audit["action"] == "CREATE"
    assert audit["resource_type"] == "attendance"
    assert audit["after"]["student_id"] == str(student_id)
    assert audit["after"]["lecture_id"] == str(lecture_id)
    assert audit["after"]["session_id"] == str(session_id)
    assert audit["after"]["status"] == AttendanceStatus.PRESENT.value
    assert audit["after"]["reason"] == "Verified in browser test."
    assert audit["reason"] == "Verified in browser test."
    db.commit.assert_called_once()
