from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import hash_password, verify_password
from app.main import app
from app.models import (
    AttendanceSession,
    AttendanceSessionStatus,
    AuditLog,
    AuthSession,
    Base,
    Lecture,
    LectureStatus,
    PasswordResetToken,
    SupportingDocument,
    User,
    UserRole,
)
from app.services.auth import create_password_reset, reset_password
from app.services.storage import StorageUnavailable


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
        # Protected routes reject an anonymous caller before any role-specific work.
        assert admin_client.get("/api/admin/overview").status_code == 401
        login = admin_client.post(
            "/api/auth/login",
            json={"email": admin.email, "password": "Admin password 2026!"},
        )
        assert login.status_code == 200
        assert admin_client.get("/api/student/attendance/threshold").status_code == 403

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
            unassigned_faculty_response = admin_client.post(
                "/api/admin/users",
                json={
                    "institutional_id": "FAC-2",
                    "email": "other-faculty@example.edu",
                    "full_name": "Other Faculty",
                    "password": "Other faculty password 2026!",
                    "role": "FACULTY",
                    "department_id": department_id,
                },
            )
            assert unassigned_faculty_response.status_code == 201
            with TestClient(app) as other_faculty_client:
                other_login = other_faculty_client.post(
                    "/api/auth/login",
                    json={
                        "email": "other-faculty@example.edu",
                        "password": "Other faculty password 2026!",
                    },
                )
                assert other_login.status_code == 200
                assert (
                    other_faculty_client.get(
                        f"/api/faculty/attendance/session/{session_id}"
                    ).status_code
                    == 403
                )
            # The socket route uses its own session factory; bind it to this isolated test DB.
            monkeypatch.setattr(
                "app.api.attendance.websocket.SessionLocal",
                sessionmaker(bind=db.get_bind(), expire_on_commit=False),
            )
            with (
                faculty_client.websocket_connect(f"/ws/attendance/{session_id}") as socket_one,
                faculty_client.websocket_connect(f"/ws/attendance/{session_id}") as socket_two,
            ):
                for socket in (socket_one, socket_two):
                    started = socket.receive_json()
                    assert started["type"] == "SESSION_STARTED"
                    assert started["session_id"] == session_id

                manual_response = faculty_client.post(
                    "/api/faculty/attendance/manual",
                    json={
                        "session_id": session_id,
                        "student_id": second_student_id,
                        "status": "ABSENT",
                        "reason": "Student not present at manual check.",
                    },
                )
                assert manual_response.status_code == 201, manual_response.text
                for socket in (socket_one, socket_two):
                    event = socket.receive_json()
                    assert event["type"] == "ATTENDANCE_RECORDED"
                    assert event["attendance_id"] == manual_response.json()["id"]

                close_response = faculty_client.post(
                    f"/api/faculty/attendance/session/{session_id}/close"
                )
                assert close_response.status_code == 200, close_response.text
                for socket in (socket_one, socket_two):
                    assert socket.receive_json()["type"] == "SESSION_CLOSED"

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
                assert student_client.get("/api/admin/overview").status_code == 403
                assert (
                    student_client.post(
                        "/api/faculty/attendance/manual",
                        json={
                            "session_id": session_id,
                            "student_id": student_id,
                            "status": "PRESENT",
                        },
                    ).status_code
                    == 403
                )
                threshold_response = student_client.get("/api/student/attendance/threshold")
                assert threshold_response.status_code == 200
                assert threshold_response.json() == {"attendance_threshold": 75.0}
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

                stored_objects: dict[str, bytes] = {}

                class TestStorage:
                    def upload(self, filename: str, content: bytes) -> str:
                        key = f"test-{len(stored_objects)}.pdf"
                        stored_objects[key] = content
                        return key

                    def download(self, storage_key: str) -> bytes:
                        return stored_objects[storage_key]

                    def delete(self, storage_key: str) -> None:
                        stored_objects.pop(storage_key, None)

                monkeypatch.setattr(
                    "app.api.student.documents.get_storage_service", lambda: TestStorage()
                )
                upload_response = student_client.post(
                    f"/api/student/requests/{request_id}/documents",
                    files={
                        "file": (
                            "evidence.pdf",
                            b"%PDF-1.7 test evidence",
                            "application/pdf",
                        )
                    },
                )
                assert upload_response.status_code == 201, upload_response.text
                document_id = upload_response.json()["id"]
                assert upload_response.json()["filename"] == "evidence.pdf"
                assert (
                    student_client.get(f"/api/student/requests/{request_id}/documents").json()[0][
                        "id"
                    ]
                    == document_id
                )
                assert (
                    student_client.get(f"/api/student/requests/documents/{document_id}").content
                    == b"%PDF-1.7 test evidence"
                )
                assert (
                    student_client.post(
                        f"/api/student/requests/{request_id}/documents",
                        files={"file": ("spoofed.pdf", b"not a pdf", "application/pdf")},
                    ).status_code
                    == 415
                )
                with TestClient(app) as other_student_client:
                    other_login = other_student_client.post(
                        "/api/auth/login",
                        json={
                            "email": "student2@example.edu",
                            "password": "Student two password 2026!",
                        },
                    )
                    assert other_login.status_code == 200
                    assert (
                        other_student_client.get(
                            f"/api/student/requests/documents/{document_id}"
                        ).status_code
                        == 404
                    )

                def unavailable_storage():
                    raise StorageUnavailable("sanitized provider failure")

                monkeypatch.setattr(
                    "app.api.student.documents.get_storage_service", unavailable_storage
                )
                provider_failure = student_client.post(
                    f"/api/student/requests/{request_id}/documents",
                    files={"file": ("second.pdf", b"%PDF-1.7 second", "application/pdf")},
                )
                assert provider_failure.status_code == 503
                own_requests = student_client.get("/api/student/requests").json()
                assert (
                    next(item for item in own_requests if item["id"] == request_id)["status"]
                    == "PENDING"
                )

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
        attendance_audit = db.scalar(
            select(AuditLog).where(
                AuditLog.resource_type == "attendance",
                AuditLog.resource_id == manual_response.json()["id"],
            )
        )
        assert attendance_audit is not None
        assert attendance_audit.actor_id == UUID(faculty_id)
        assert attendance_audit.reason == "Student not present at manual check."
        assert attendance_audit.after_state["student_id"] == str(second_student_id)
        assert attendance_audit.after_state["status"] == "ABSENT"
        stored_document = db.get(SupportingDocument, UUID(document_id))
        assert stored_document is not None
        assert stored_document.original_filename == "evidence.pdf"
        assert stored_document.content_type == "application/pdf"
        assert stored_document.size_bytes == len(b"%PDF-1.7 test evidence")
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


def test_password_reset_is_one_time_and_revokes_existing_sessions(api_database: Session) -> None:
    db = api_database
    user = User(
        institutional_id="STU-RESET",
        email="reset@example.edu",
        full_name="Reset User",
        password_hash=hash_password("Old password 2026!"),
        role=UserRole.STUDENT,
        is_active=True,
    )
    db.add(user)
    db.flush()
    session = AuthSession(user_id=user.id, expires_at=datetime.now(UTC) + timedelta(minutes=20))
    db.add(session)
    db.commit()

    raw_token = create_password_reset(db, user)
    token_row = db.scalar(select(PasswordResetToken).where(PasswordResetToken.user_id == user.id))
    assert token_row is not None
    assert raw_token not in token_row.token_digest
    assert reset_password(db, raw_token, "New password 2026!")
    assert token_row.used_at is not None
    assert db.get(AuthSession, session.id).revoked_at is not None
    assert verify_password("New password 2026!", db.get(User, user.id).password_hash)
    assert not reset_password(db, raw_token, "Another password 2026!")


def test_production_login_cookie_uses_secure_cross_origin_attributes(
    api_database: Session, monkeypatch
) -> None:
    user = User(
        institutional_id="ADM-COOKIE",
        email="cookie-admin@example.edu",
        full_name="Cookie Admin",
        password_hash=hash_password("Cookie test password 2026!"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    api_database.add(user)
    api_database.commit()
    monkeypatch.setattr("app.api.auth.router.settings.env", "production")
    monkeypatch.setattr("app.api.auth.router.settings.cookie_samesite", "none")

    with TestClient(app, base_url="https://testserver") as client:
        response = client.post(
            "/api/auth/login",
            json={"email": user.email, "password": "Cookie test password 2026!"},
        )

    assert response.status_code == 200
    cookie = response.headers.get("set-cookie", "").lower()
    assert "httponly" in cookie
    assert "secure" in cookie
    assert "samesite=none" in cookie
