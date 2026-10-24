from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import Request

from app.api.faculty.attendance import start_session, update_network_lock


class CommitTracker:
    def __init__(self) -> None:
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1


def make_request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "scheme": "https",
            "path": "/api/faculty/attendance/session",
            "headers": [],
            "client": ("203.0.113.17", 1234),
            "server": ("testserver", 443),
        }
    )


def test_start_session_commits_network_binding(monkeypatch) -> None:
    session = SimpleNamespace(id=uuid4())
    faculty = SimpleNamespace(id=uuid4())
    db = CommitTracker()
    bind_calls = []
    monkeypatch.setattr(
        "app.api.faculty.attendance.create_attendance_session",
        lambda *_args: session,
    )
    monkeypatch.setattr(
        "app.api.faculty.attendance.get_client_ip", lambda _request: "203.0.113.17"
    )
    monkeypatch.setattr(
        "app.api.faculty.attendance.bind_session_network",
        lambda *args, **kwargs: bind_calls.append((args, kwargs)),
    )

    result = start_session(
        SimpleNamespace(lecture_id=uuid4()), make_request(), faculty, db
    )

    assert result is session
    assert db.commits == 1
    assert bind_calls


@pytest.mark.parametrize("auto_detect", [True, False])
def test_network_controls_commit_changes(monkeypatch, auto_detect: bool) -> None:
    session_id = uuid4()
    faculty = SimpleNamespace(id=uuid4())
    db = CommitTracker()
    monkeypatch.setattr(
        "app.api.faculty.attendance.get_authorized_session",
        lambda *_args: SimpleNamespace(id=session_id),
    )
    monkeypatch.setattr(
        "app.api.faculty.attendance.bind_session_network",
        lambda *_args, **_kwargs: {"bound_subnet": "203.0.113.17/32"},
    )
    monkeypatch.setattr(
        "app.api.faculty.attendance.update_session_network",
        lambda *_args, **_kwargs: {"enforced": False},
    )
    monkeypatch.setattr(
        "app.api.faculty.attendance.get_client_ip", lambda _request: "203.0.113.17"
    )

    result = update_network_lock(
        session_id,
        {"auto_detect": auto_detect, "enforced": not auto_detect},
        make_request(),
        faculty,
        db,
    )

    assert result
    assert db.commits == 1
