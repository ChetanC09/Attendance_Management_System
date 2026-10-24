"""Idempotently seed public demo data for the SPIT AMS deployment.

The Render API startup runs this after applying database migrations. It is safe
to run again after a restart: existing accounts and records are preserved.

Demo accounts use intentionally public credentials; never use them for real
personal or institutional data.
"""

from datetime import UTC, date, datetime, time, timedelta
import os

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

# ── Fixed demo credentials ───────────────────────────────────────────────────
ADMIN_EMAIL = "admin@spit.ac.in"
ADMIN_ID = "SPIT-ADMIN-001"
ADMIN_NAME = "SPIT Administrator"
ADMIN_PASSWORD = "Admin@SPIT2024"

FACULTY_EMAIL = "dr.patel@spit.ac.in"
FACULTY_ID = "FAC-CE-001"
FACULTY_NAME = "Dr. Meera Patel"
FACULTY_PASSWORD = "Faculty@SPIT2024"

STUDENT_PASSWORD = "Student@SPIT2024"
STUDENTS = [
    ("Rahul Mehta",   "CE-2022-001", "rahul.mehta@spit.ac.in"),
    ("Isha Joshi",    "CE-2022-002", "isha.joshi@spit.ac.in"),
    ("Kabir Rao",     "CE-2022-003", "kabir.rao@spit.ac.in"),
    ("Mira Desai",    "CE-2022-004", "mira.desai@spit.ac.in"),
    ("Neel Shah",     "CE-2022-005", "neel.shah@spit.ac.in"),
]
# ─────────────────────────────────────────────────────────────────────────────


def _bootstrap_configured_admin() -> None:
    """Create an owner-supplied first admin when bootstrap values are configured."""
    names = (
        "AMS_BOOTSTRAP_ADMIN_EMAIL",
        "AMS_BOOTSTRAP_ADMIN_ID",
        "AMS_BOOTSTRAP_ADMIN_NAME",
        "AMS_BOOTSTRAP_ADMIN_PASSWORD",
    )
    values = [os.getenv(name) for name in names]
    if not any(values):
        return
    if not all(values):
        raise SystemExit("Configure all AMS_BOOTSTRAP_ADMIN_* values or remove them")

    with SessionLocal() as db:
        has_admin = db.scalar(select(User.id).where(User.role == UserRole.ADMIN).limit(1))
    if has_admin:
        return

    from scripts.seed_admin import main as create_first_admin

    create_first_admin()


def _upsert_user(db, email, inst_id, name, role, password_hash):
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            email=email,
            institutional_id=inst_id,
            full_name=name,
            password_hash=password_hash,
            role=role,
            is_active=True,
        )
        db.add(user)
        db.flush()
    return user


def main() -> None:
    _bootstrap_configured_admin()
    today = datetime.now(UTC).date()
    # Academic year: July–June
    ay_start = date(today.year if today.month >= 7 else today.year - 1, 7, 1)
    ay_end = date(ay_start.year + 1, 6, 30)
    sem_start = ay_start
    sem_end = date(ay_start.year, 12, 31)

    admin_hash = hash_password(ADMIN_PASSWORD)
    faculty_hash = hash_password(FACULTY_PASSWORD)
    student_hash = hash_password(STUDENT_PASSWORD)

    with SessionLocal.begin() as db:
        # ── Admin ────────────────────────────────────────────────────────────
        admin = db.scalar(select(User).where(User.email == ADMIN_EMAIL))
        if admin is None:
            # Only create admin if no admin exists at all
            existing_admin = db.scalar(
                select(User.id).where(User.role == UserRole.ADMIN).limit(1)
            )
            if existing_admin is None:
                admin = _upsert_user(
                    db, ADMIN_EMAIL, ADMIN_ID, ADMIN_NAME, UserRole.ADMIN, admin_hash
                )
            else:
                print(
                    "An admin already exists — skipping admin creation. "
                    "Log in with your existing admin credentials."
                )

        # ── Department / Academic structure ──────────────────────────────────
        dept = db.scalar(select(Department).where(Department.code == "CSE"))
        if dept is None:
            dept = Department(code="CSE", name="Computer Engineering")
            db.add(dept)
            db.flush()

        ay = db.scalar(
            select(AcademicYear).where(
                AcademicYear.name == f"{ay_start.year}-{ay_end.year}"
            )
        )
        if ay is None:
            ay = AcademicYear(
                name=f"{ay_start.year}-{ay_end.year}",
                starts_on=ay_start,
                ends_on=ay_end,
            )
            db.add(ay)
            db.flush()

        sem = db.scalar(
            select(Semester).where(
                Semester.academic_year_id == ay.id, Semester.number == 5
            )
        )
        if sem is None:
            sem = Semester(
                academic_year_id=ay.id,
                number=5,
                starts_on=sem_start,
                ends_on=sem_end,
            )
            db.add(sem)
            db.flush()

        section = db.scalar(
            select(Section).where(
                Section.department_id == dept.id,
                Section.academic_year_id == ay.id,
                Section.name == "CE-A",
            )
        )
        if section is None:
            section = Section(
                department_id=dept.id, academic_year_id=ay.id, name="CE-A"
            )
            db.add(section)
            db.flush()

        # ── Classroom ────────────────────────────────────────────────────────
        room = db.scalar(select(Classroom).where(Classroom.code == "CE-301"))
        if room is None:
            room = Classroom(code="CE-301", name="Seminar Hall 301", capacity=60)
            db.add(room)
            db.flush()

        # ── Faculty user + profile ───────────────────────────────────────────
        faculty = _upsert_user(
            db, FACULTY_EMAIL, FACULTY_ID, FACULTY_NAME, UserRole.FACULTY, faculty_hash
        )
        if not db.scalar(
            select(FacultyProfile.id).where(FacultyProfile.user_id == faculty.id)
        ):
            db.add(FacultyProfile(user_id=faculty.id, department_id=dept.id))
            db.flush()

        # ── Students + profiles ──────────────────────────────────────────────
        students = []
        for name, inst_id, email in STUDENTS:
            s = _upsert_user(
                db, email, inst_id, name, UserRole.STUDENT, student_hash
            )
            if not db.scalar(
                select(StudentProfile.id).where(StudentProfile.user_id == s.id)
            ):
                db.add(
                    StudentProfile(
                        user_id=s.id,
                        department_id=dept.id,
                        section_id=section.id,
                        enrollment_year=ay_start.year,
                    )
                )
            students.append(s)
        db.flush()

        # ── Courses + allocations + timetable ────────────────────────────────
        course_specs = [
            ("CS501", "Database Management Systems", 4, today.weekday(), time(9, 0)),
            ("CS502", "Operating Systems", 4, (today.weekday() + 2) % 5, time(11, 0)),
            ("CS503", "Computer Networks", 3, (today.weekday() + 4) % 5, time(14, 0)),
        ]

        allocations = []
        entries = []
        for code, cname, credits, weekday, start_time in course_specs:
            course = db.scalar(
                select(Course).where(
                    Course.department_id == dept.id, Course.code == code
                )
            )
            if course is None:
                course = Course(
                    department_id=dept.id, code=code, name=cname, credits=credits
                )
                db.add(course)
                db.flush()

            alloc = db.scalar(
                select(CourseAllocation).where(
                    CourseAllocation.course_id == course.id,
                    CourseAllocation.semester_id == sem.id,
                    CourseAllocation.section_id == section.id,
                )
            )
            if alloc is None:
                alloc = CourseAllocation(
                    course_id=course.id,
                    semester_id=sem.id,
                    section_id=section.id,
                    faculty_id=faculty.id,
                )
                db.add(alloc)
                db.flush()
            allocations.append(alloc)

            entry = db.scalar(
                select(TimetableEntry).where(
                    TimetableEntry.allocation_id == alloc.id,
                    TimetableEntry.weekday == weekday,
                )
            )
            if entry is None:
                entry = TimetableEntry(
                    allocation_id=alloc.id,
                    classroom_id=room.id,
                    weekday=weekday,
                    starts_at=start_time,
                    ends_at=(
                        datetime.combine(today, start_time) + timedelta(minutes=60)
                    ).time(),
                    effective_from=sem_start,
                    effective_until=sem_end,
                    is_active=True,
                )
                db.add(entry)
                db.flush()
            entries.append(entry)

        # ── Historical lectures + attendance (past 10 weeks) ─────────────────
        now = datetime.now(UTC)
        lecture_by_alloc: dict = {}
        history_start = today - timedelta(weeks=10)

        for alloc, entry in zip(allocations, entries, strict=True):
            current = history_start
            while current <= today:
                if current.weekday() == entry.weekday and current < today:
                    starts_at = datetime.combine(
                        current, entry.starts_at, tzinfo=UTC
                    )
                    existing = db.scalar(
                        select(Lecture).where(
                            Lecture.allocation_id == alloc.id,
                            Lecture.starts_at == starts_at,
                        )
                    )
                    if existing is None:
                        existing = Lecture(
                            allocation_id=alloc.id,
                            timetable_entry_id=entry.id,
                            classroom_id=room.id,
                            starts_at=starts_at,
                            ends_at=starts_at + timedelta(minutes=60),
                            status=LectureStatus.CONDUCTED,
                        )
                        db.add(existing)
                        db.flush()
                    lecture_by_alloc.setdefault(alloc.id, []).append(existing)
                current += timedelta(days=1)

        # ── Today's SCHEDULED lecture for the first course ──────────────────
        today_start = datetime.combine(today, time(9, 0), tzinfo=UTC)
        if not db.scalar(
            select(Lecture.id).where(
                Lecture.allocation_id == allocations[0].id,
                Lecture.starts_at >= datetime.combine(today, time.min, tzinfo=UTC),
                Lecture.starts_at
                < datetime.combine(today + timedelta(days=1), time.min, tzinfo=UTC),
            )
        ):
            db.add(
                Lecture(
                    allocation_id=allocations[0].id,
                    timetable_entry_id=entries[0].id,
                    classroom_id=room.id,
                    starts_at=today_start,
                    ends_at=today_start + timedelta(minutes=60),
                    status=LectureStatus.SCHEDULED,
                )
            )

        # ── Attendance records (realistic mix — student1 borderline at ~74%) ─
        for ai, (alloc, entry) in enumerate(zip(allocations, entries, strict=True)):
            lectures = lecture_by_alloc.get(alloc.id, [])
            for li, lecture in enumerate(lectures):
                if lecture.starts_at > now:
                    continue
                for si, student in enumerate(students):
                    if db.scalar(
                        select(Attendance.id).where(
                            Attendance.student_id == student.id,
                            Attendance.lecture_id == lecture.id,
                        )
                    ):
                        continue
                    # Student 0 (Rahul) absent ~26% of the time for demo effect
                    if si == 0:
                        is_present = li % 4 != 0
                    else:
                        is_present = (si + li + ai) % 7 != 0
                    db.add(
                        Attendance(
                            student_id=student.id,
                            lecture_id=lecture.id,
                            status=(
                                AttendanceStatus.PRESENT
                                if is_present
                                else AttendanceStatus.ABSENT
                            ),
                            source=AttendanceSource.MANUAL,
                            marked_by=faculty.id,
                            marked_at=lecture.ends_at,
                            reason="Demo fixture",
                        )
                    )

        db.flush()

        # ── Pending regularization request (student 0 → 2nd lecture absent) ─
        lectures_for_req = lecture_by_alloc.get(allocations[0].id, [])
        req_lecture = next(
            (lec for lec in lectures_for_req if lec.starts_at.date() < today),
            None,
        )
        if req_lecture and not db.scalar(
            select(LeaveRequest).where(
                LeaveRequest.student_id == students[0].id,
                LeaveRequest.lecture_id == req_lecture.id,
            )
        ):
            db.add(
                LeaveRequest(
                    student_id=students[0].id,
                    lecture_id=req_lecture.id,
                    request_type=RequestType.REGULARIZATION,
                    status=RequestStatus.PENDING,
                    reason=(
                        "I was absent due to a medical appointment. "
                        "Attaching doctor's certificate for review."
                    ),
                )
            )

        # ── Announcement ─────────────────────────────────────────────────────
        if not db.scalar(
            select(Announcement).where(
                Announcement.allocation_id == allocations[0].id,
                Announcement.title == "Mid-semester assessment schedule",
            )
        ):
            db.add(
                Announcement(
                    allocation_id=allocations[0].id,
                    faculty_id=faculty.id,
                    title="Mid-semester assessment schedule",
                    body=(
                        "The mid-semester examination for CS501 will be held on "
                        f"{(today + timedelta(weeks=2)).strftime('%d %B %Y')}. "
                        "Syllabus covers Units 1–4. Please ensure 75% attendance "
                        "to be eligible."
                    ),
                )
            )

        # ── In-app notification for student 0 ────────────────────────────────
        if not db.scalar(
            select(Notification).where(
                Notification.user_id == students[0].id,
                Notification.title == "Attendance alert: CS501",
            )
        ):
            db.add(
                Notification(
                    user_id=students[0].id,
                    title="Attendance alert: CS501",
                    message=(
                        "Your attendance in Database Management Systems has dropped to 74%. "
                        "You need to attend the next 3 lectures to reach 75%."
                    ),
                    channel=NotificationChannel.IN_APP,
                    status=NotificationStatus.SENT,
                )
            )

        # ── System settings ───────────────────────────────────────────────────
        if not db.get(SystemSetting, "attendance_threshold"):
            db.add(SystemSetting(key="attendance_threshold", value={"percentage": 75.0}))
        if not db.get(SystemSetting, "notification_delivery"):
            db.add(
                SystemSetting(
                    key="notification_delivery",
                    value={"email_enabled": True, "sms_enabled": False},
                )
            )

    # ── Summary ───────────────────────────────────────────────────────────────
    print("SPIT AMS production demo data seeded; existing account passwords were preserved.")
    print(f"Demo admin: {ADMIN_EMAIL}; faculty: {FACULTY_EMAIL}; students: {len(STUDENTS)}")
    print("  Demo student for video: rahul.mehta@spit.ac.in")
    print("  Rahul is borderline at ~74% attendance — good for recovery demo.")
    print("  Today's DBMS lecture is SCHEDULED and ready for faculty to open.")
    print("  One pending regularization request from Rahul is queued for faculty.")
    print()


if __name__ == "__main__":
    if settings.env != "production":
        raise SystemExit("Production demo seeding requires AMS_ENV=production")
    main()
