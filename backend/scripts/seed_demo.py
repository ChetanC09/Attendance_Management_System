"""Idempotently populate a development database with realistic AMS demo records.

Never run this against production. Demo user accounts deliberately share a
development password supplied through AMS_DEMO_PASSWORD.
"""

import os
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import (
    AcademicYear,
    Announcement,
    Attendance,
    AttendanceSource,
    AttendanceStatus,
    Classroom,
    Course,
    CourseAllocation,
    Department,
    FacultyProfile,
    LeaveRequest,
    Lecture,
    LectureStatus,
    Notification,
    NotificationChannel,
    NotificationStatus,
    RequestStatus,
    RequestType,
    Section,
    Semester,
    StudentProfile,
    SystemSetting,
    TimetableEntry,
    User,
    UserRole,
)


def _user(
    db, email: str, institutional_id: str, name: str, role: UserRole, password_hash: str
) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            email=email,
            institutional_id=institutional_id,
            full_name=name,
            password_hash=password_hash,
            role=role,
            is_active=True,
        )
        db.add(user)
        db.flush()
    else:
        user.password_hash = password_hash
    return user


def main() -> None:
    if settings.env != "development" or os.getenv("AMS_SEED_DEMO", "true").lower() != "true":
        raise SystemExit(
            "Demo seeding is development-only; set AMS_ENV=development and AMS_SEED_DEMO=true"
        )
    password = os.getenv("AMS_DEMO_PASSWORD", "")
    if len(password) < 12:
        raise SystemExit(
            "Set AMS_DEMO_PASSWORD to a local development password of at least 12 characters"
        )
    password_hash = hash_password(password)
    today = datetime.now(UTC).date()
    academic_start = date(today.year if today.month >= 7 else today.year - 1, 7, 1)
    academic_end = date(academic_start.year + 1, 6, 30)
    semester_start = academic_start
    semester_end = date(academic_start.year, 12, 31)

    with SessionLocal.begin() as db:
        department = db.scalar(select(Department).where(Department.code == "CSE"))
        if department is None:
            department = Department(code="CSE", name="Computer Engineering")
            db.add(department)
            db.flush()
        year = db.scalar(
            select(AcademicYear).where(
                AcademicYear.name == f"{academic_start.year}-{academic_end.year}"
            )
        )
        if year is None:
            year = AcademicYear(
                name=f"{academic_start.year}-{academic_end.year}",
                starts_on=academic_start,
                ends_on=academic_end,
            )
            db.add(year)
            db.flush()
        semester = db.scalar(
            select(Semester).where(Semester.academic_year_id == year.id, Semester.number == 1)
        )
        if semester is None:
            semester = Semester(
                academic_year_id=year.id, number=1, starts_on=semester_start, ends_on=semester_end
            )
            db.add(semester)
            db.flush()
        section = db.scalar(
            select(Section).where(
                Section.department_id == department.id,
                Section.academic_year_id == year.id,
                Section.name == "CE-A",
            )
        )
        if section is None:
            section = Section(department_id=department.id, academic_year_id=year.id, name="CE-A")
            db.add(section)
            db.flush()

        _user(
            db,
            "admin@ams.dev",
            "DEMO-AMS-ADMIN-2026",
            "AMS Demo Administrator",
            UserRole.ADMIN,
            password_hash,
        )
        faculty = _user(
            db,
            "faculty@ams.dev",
            "FAC-2026-001",
            "Dr. Meera Patel",
            UserRole.FACULTY,
            password_hash,
        )
        if faculty.faculty_profile is None:
            db.add(FacultyProfile(user_id=faculty.id, department_id=department.id))
        students = []
        for index, name in enumerate(
            ("Aarav Shah", "Isha Mehta", "Kabir Rao", "Mira Desai", "Neel Joshi", "Sara Khan"), 1
        ):
            student = _user(
                db,
                f"student{index}@ams.dev",
                f"CE-2026-{index:03}",
                name,
                UserRole.STUDENT,
                password_hash,
            )
            if student.student_profile is None:
                db.add(
                    StudentProfile(
                        user_id=student.id,
                        department_id=department.id,
                        section_id=section.id,
                        enrollment_year=academic_start.year,
                    )
                )
            students.append(student)
        room = db.scalar(select(Classroom).where(Classroom.code == "CE-101"))
        if room is None:
            room = Classroom(code="CE-101", name="Computer Engineering 101", capacity=60)
            db.add(room)
            db.flush()

        course_specs = (
            ("CE201", "Data Structures and Algorithms", 4, 0, time(9, 0)),
            ("CE203", "Database Management Systems", 4, 1, time(10, 30)),
            ("CE205", "Computer Networks", 3, 2, time(13, 0)),
        )
        allocations = []
        entries = []
        for code, name, credits, weekday, start_time in course_specs:
            course = db.scalar(
                select(Course).where(Course.department_id == department.id, Course.code == code)
            )
            if course is None:
                course = Course(department_id=department.id, code=code, name=name, credits=credits)
                db.add(course)
                db.flush()
            allocation = db.scalar(
                select(CourseAllocation).where(
                    CourseAllocation.course_id == course.id,
                    CourseAllocation.semester_id == semester.id,
                    CourseAllocation.section_id == section.id,
                )
            )
            if allocation is None:
                allocation = CourseAllocation(
                    course_id=course.id,
                    semester_id=semester.id,
                    section_id=section.id,
                    faculty_id=faculty.id,
                )
                db.add(allocation)
                db.flush()
            allocations.append(allocation)
            entry = db.scalar(
                select(TimetableEntry).where(
                    TimetableEntry.allocation_id == allocation.id, TimetableEntry.weekday == weekday
                )
            )
            if entry is None:
                entry = TimetableEntry(
                    allocation_id=allocation.id,
                    classroom_id=room.id,
                    weekday=weekday,
                    starts_at=start_time,
                    ends_at=(datetime.combine(today, start_time) + timedelta(minutes=60)).time(),
                    effective_from=semester_start,
                    effective_until=semester_end,
                    is_active=True,
                )
                db.add(entry)
                db.flush()
            entries.append(entry)

        db.flush()
        # Populate conducted sessions from the semester start through today.
        lecture_by_allocation = {}
        now = datetime.now(UTC)
        for allocation, entry in zip(allocations, entries, strict=True):
            current = semester_start
            while current <= min(today, semester_end):
                if current.weekday() == entry.weekday:
                    starts_at = datetime.combine(current, entry.starts_at, tzinfo=UTC)
                    existing = db.scalar(
                        select(Lecture).where(
                            Lecture.allocation_id == allocation.id, Lecture.starts_at == starts_at
                        )
                    )
                    if existing is None:
                        existing = Lecture(
                            allocation_id=allocation.id,
                            timetable_entry_id=entry.id,
                            classroom_id=room.id,
                            starts_at=starts_at,
                            ends_at=starts_at + timedelta(minutes=60),
                            status=LectureStatus.CONDUCTED,
                        )
                        db.add(existing)
                        db.flush()
                    lecture_by_allocation.setdefault(allocation.id, []).append(existing)
                current += timedelta(days=1)

        # Ensure faculty has a class to open today, even when today's weekday is
        # not one of the fixed recurring demo timetable days.
        today_start = datetime.combine(today, time(15, 0), tzinfo=UTC)
        if (
            today_start > now
            and db.scalar(
                select(Lecture.id).where(
                    Lecture.allocation_id == allocations[0].id,
                    Lecture.starts_at >= datetime.combine(today, time.min, tzinfo=UTC),
                    Lecture.starts_at
                    < datetime.combine(today + timedelta(days=1), time.min, tzinfo=UTC),
                )
            )
            is None
        ):
            db.add(
                Lecture(
                    allocation_id=allocations[0].id,
                    classroom_id=room.id,
                    starts_at=today_start,
                    ends_at=today_start + timedelta(minutes=60),
                    status=LectureStatus.SCHEDULED,
                )
            )

        for allocation_index, allocation in enumerate(allocations):
            lectures = lecture_by_allocation.get(allocation.id, [])[-12:]
            for lecture_index, lecture in enumerate(lectures):
                if lecture.starts_at > now:
                    continue
                for student_index, student in enumerate(students):
                    exists = db.scalar(
                        select(Attendance.id).where(
                            Attendance.student_id == student.id, Attendance.lecture_id == lecture.id
                        )
                    )
                    if exists:
                        continue
                    is_present = (student_index + lecture_index + allocation_index) % 5 != 0
                    db.add(
                        Attendance(
                            student_id=student.id,
                            lecture_id=lecture.id,
                            status=AttendanceStatus.PRESENT
                            if is_present
                            else AttendanceStatus.ABSENT,
                            source=AttendanceSource.MANUAL,
                            marked_by=faculty.id,
                            marked_at=lecture.ends_at,
                            reason="Development fixture",
                        )
                    )
        db.flush()

        pending_lecture = next(
            (
                lecture
                for allocation_index, allocation in enumerate(allocations)
                for lecture_index, lecture in enumerate(
                    lecture_by_allocation.get(allocation.id, [])[-12:]
                )
                if lecture.starts_at.date() < today and lecture_index % 5 == allocation_index % 5
            ),
            None,
        )
        if pending_lecture:
            pending_student = students[0]
            request = db.scalar(
                select(LeaveRequest).where(
                    LeaveRequest.student_id == pending_student.id,
                    LeaveRequest.lecture_id == pending_lecture.id,
                    LeaveRequest.status == RequestStatus.PENDING,
                )
            )
            if request is None:
                db.add(
                    LeaveRequest(
                        student_id=pending_student.id,
                        lecture_id=pending_lecture.id,
                        request_type=RequestType.REGULARIZATION,
                        status=RequestStatus.PENDING,
                        reason=(
                            "Demo request: medical appointment; please review the attached record."
                        ),
                    )
                )
        announcement = db.scalar(
            select(Announcement).where(
                Announcement.allocation_id == allocations[0].id,
                Announcement.title == "Welcome to the semester",
            )
        )
        if announcement is None:
            db.add(
                Announcement(
                    allocation_id=allocations[0].id,
                    faculty_id=faculty.id,
                    title="Welcome to the semester",
                    body=(
                        "The course space is ready. Check the timetable and bring your lab "
                        "materials to the next session."
                    ),
                )
            )
        notification = db.scalar(
            select(Notification).where(
                Notification.user_id == students[0].id,
                Notification.title == "AMS demo data is ready",
            )
        )
        if notification is None:
            db.add(
                Notification(
                    user_id=students[0].id,
                    title="AMS demo data is ready",
                    message="Your course schedule and attendance history are now available.",
                    channel=NotificationChannel.IN_APP,
                    status=NotificationStatus.SENT,
                )
            )
        threshold = db.get(SystemSetting, "attendance_threshold")
        if threshold is None:
            db.add(SystemSetting(key="attendance_threshold", value={"percentage": 75.0}))

    print("Seeded development fixtures:")
    print("  admin@ams.dev, faculty@ams.dev, student1@ams.dev through student6@ams.dev")
    print("  Shared password: configured through AMS_DEMO_PASSWORD in the local environment")


if __name__ == "__main__":
    main()
