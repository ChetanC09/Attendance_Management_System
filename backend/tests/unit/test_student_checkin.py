from datetime import UTC, datetime
from uuid import uuid4

from app.api.student.checkin import _active_lecture_and_session


class QueryCapture:
    def __init__(self) -> None:
        self.statements = []

    def scalar(self, statement):
        self.statements.append(statement)
        return None


def test_active_session_query_orders_by_existing_started_at_column() -> None:
    db = QueryCapture()

    result = _active_lecture_and_session(db, uuid4(), datetime.now(UTC))

    assert result == (None, None, None)
    sql = str(db.statements[0].compile())
    assert "attendance_sessions.started_at DESC" in sql
    assert "opened_at" not in sql
