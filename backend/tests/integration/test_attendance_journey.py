from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import hash_password
from app.main import app
from app.models import (
    AttendanceSession,
    AttendanceSessionStatus,
    AuditLog,
    Base,
    Lecture,
    LectureStatus,
    User,
    UserRole,
)


@pytest.fixture
def api_database():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_sessions = sessionmaker(bind=engine, expire_on_commit=False)
    db = test_sessions()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield db
    finally:
        app.dependency_overrides.clear()
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_admin_to_student_regularization_journey(api_database: Session, monkeypatch) -> None:
    db = api_database
    admin = User(
        institutional_id="ADM-1",
        email="admin@example.edu",
        full_name="Admin",
        password_hash=hash_password("Admin password 2026!"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(admin)
    db.commit()

    with TestClient(app) as admin_client:
        login = admin_client.post(
            "/api/auth/login",
            json={"email": admin.email, "password": "Admin password 2026!"},
        )
        assert login.status_code == 200

        department_response = admin_client.post(
            "/api/admin/departments", json={"code": "CSE", "name": "Computer Science"}
        )
        assert department_response.status_code == 201, department_response.text
        department_id = department_response.json()["id"]

        year_response = admin_client.post(
            "/api/admin/academic-years",
            json={"name": "2026-2027", "starts_on": "2026-04-01", "ends_on": "2027-03-31"},
        )
        assert year_response.status_code == 201, year_response.text
        year_id = year_response.json()["id"]

        semester_response = admin_client.post(
            "/api/admin/semesters",
            json={
                "academic_year_id": year_id,
                "number": 1,
                "starts_on": "2026-04-01",
                "ends_on": "2026-09-30",
            },
        )
        assert semester_response.status_code == 201, semester_response.text
        semester_id = semester_response.json()["id"]

        section_response = admin_client.post(
            "/api/admin/sections",
            json={"department_id": department_id, "academic_year_id": year_id, "name": "CSE-A"},
        )
        assert section_response.status_code == 201, section_response.text
        section_id = section_response.json()["id"]

        course_response = admin_client.post(
            "/api/admin/courses",
            json={
                "department_id": department_id,
                "code": "CS101",
                "name": "Foundations",
                "credits": 4,
            },
        )
        assert course_response.status_code == 201, course_response.text
        course_id = course_response.json()["id"]

        classroom_response = admin_client.post(
            "/api/admin/classrooms", json={"code": "R101", "name": "Room 101", "capacity": 60}
        )
        assert classroom_response.status_code == 201, classroom_response.text
        classroom_id = classroom_response.json()["id"]

        faculty_response = admin_client.post(
            "/api/admin/users",
            json={
                "institutional_id": "FAC-1",
                "email": "faculty@example.edu",
                "full_name": "Faculty",
                "password": "Faculty password 2026!",
                "role": "FACULTY",
                "department_id": department_id,
            },
        )
        assert faculty_response.status_code == 201, faculty_response.text
        faculty_id = faculty_response.json()["id"]

        student_response = admin_client.post(
            "/api/admin/users",
            json={
                "institutional_id": "STU-1",
                "email": "student@example.edu",
                "full_name": "Student",
                "password": "Student password 2026!",
                "role": "STUDENT",
                "section_id": section_id,
            },
        )
        assert student_response.status_code == 201, student_response.text
        student_id = student_response.json()["id"]

        second_student_response = admin_client.post(
            "/api/admin/users",
            json={
                "institutional_id": "STU-2",
                "email": "student2@example.edu",
                "full_name": "Student Two",
                "password": "Student two password 2026!",
                "role": "STUDENT",
                "section_id": section_id,
            },
        )
        assert second_student_response.status_code == 201, second_student_response.text
        second_student_id = second_student_response.json()["id"]

        allocation_response = admin_client.post(
            "/api/admin/allocations",
            json={
                "course_id": course_id,
                "semester_id": semester_id,
                "section_id": section_id,
                "faculty_id": faculty_id,
            },
        )
        assert allocation_response.status_code == 201, allocation_response.text
        allocation_id = allocation_response.json()["id"]

        timetable_response = admin_client.post(
            "/api/admin/timetable",
            json={
                "allocation_id": allocation_id,
                "classroom_id": classroom_id,
                "weekday": 0,
                "starts_at": "10:00:00",
                "ends_at": "11:00:00",
                "effective_from": "2026-10-05",
            },
        )
        assert timetable_response.status_code == 201, timetable_response.text
        timetable_id = timetable_response.json()["id"]

        lecture = Lecture(
            allocation_id=UUID(allocation_id),
            timetable_entry_id=UUID(timetable_id),
            classroom_id=UUID(classroom_id),
            starts_at=datetime.now(UTC),
            ends_at=datetime.now(UTC) + timedelta(hours=1),
            status=LectureStatus.SCHEDULED,
        )
        db.add(lecture)
        db.commit()
        lecture_id = lecture.id

        with TestClient(app) as faculty_client:
            faculty_login = faculty_client.post(
                "/api/auth/login",
                json={"email": "faculty@example.edu", "password": "Faculty password 2026!"},
            )
            assert faculty_login.status_code == 200
            session_response = faculty_client.post(
                "/api/faculty/attendance/session", json={"lecture_id": str(lecture_id)}
            )
            assert session_response.status_code == 201, session_response.text
            session_id = session_response.json()["id"]
            close_response = faculty_client.post(
                f"/api/faculty/attendance/session/{session_id}/close"
            )
            assert close_response.status_code == 200, close_response.text

            queued_notifications: list[tuple] = []
            monkeypatch.setattr(
                "app.api.faculty.requests.enqueue_in_app_notification",
                lambda *args: queued_notifications.append(args),
            )

            with TestClient(app) as student_client:
                student_login = student_client.post(
                    "/api/auth/login",
                    json={"email": "student@example.edu", "password": "Student password 2026!"},
                )
                assert student_login.status_code == 200
                request_response = student_client.post(
                    "/api/student/requests",
                    json={
                        "lecture_id": str(lecture_id),
                        "request_type": "REGULARIZATION",
                        "reason": "I attended this class but was marked absent.",
                    },
                )
                assert request_response.status_code == 201, request_response.text
                request_id = request_response.json()["id"]

                review_response = faculty_client.post(
                    f"/api/faculty/requests/{request_id}/approve", json={"reason": "Verified."}
                )
                assert review_response.status_code == 200, review_response.text
                assert review_response.json()["status"] == "APPROVED"

                summary_response = student_client.get("/api/student/attendance")
                assert summary_response.status_code == 200, summary_response.text
                summary = summary_response.json()
                assert len(summary) == 1
                assert summary[0]["attended_lectures"] == 1
                assert summary[0]["attendance_percentage"] == 100

            assert queued_notifications

            defaulters_response = faculty_client.get(
                "/api/faculty/analytics/defaulters",
                params={"allocation_id": allocation_id, "threshold": 75},
            )
            assert defaulters_response.status_code == 200, defaulters_response.text
            defaulters = defaulters_response.json()
            assert len(defaulters) == 1
            assert defaulters[0]["student_id"] == second_student_id

        actions = set(db.scalars(select(AuditLog.action)).all())
        assert {"CREATE", "OPEN", "CLOSE", "APPROVE"}.issubset(actions)
        assert db.get(User, UUID(student_id)) is not None


def test_database_allows_only_one_open_session_per_lecture(api_database: Session) -> None:
    db = api_database
    lecture_id, faculty_id = uuid4(), uuid4()
    lecture = Lecture(
        id=lecture_id,
        allocation_id=uuid4(),
        classroom_id=uuid4(),
        starts_at=datetime.now(UTC),
        ends_at=datetime.now(UTC) + timedelta(hours=1),
        status=LectureStatus.SCHEDULED,
    )
    db.add(lecture)
    db.flush()
    db.add(
        AttendanceSession(
            lecture_id=lecture_id,
            opened_by=faculty_id,
            status=AttendanceSessionStatus.OPEN,
        )
    )
    db.commit()

    db.add(
        AttendanceSession(
            lecture_id=lecture_id,
            opened_by=faculty_id,
            status=AttendanceSessionStatus.OPEN,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
