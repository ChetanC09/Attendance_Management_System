import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.core.security import decode_access_token
from app.models.attendance import Attendance, AttendanceSession, AttendanceSessionStatus
from app.models.user import UserRole
from app.services.attendance import _authorized_lecture

router = APIRouter()


class AttendanceConnections:
    def __init__(self) -> None:
        self.connections: dict[uuid.UUID, set[WebSocket]] = {}

    async def connect(self, session_id: uuid.UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.setdefault(session_id, set()).add(websocket)

    def disconnect(self, session_id: uuid.UUID, websocket: WebSocket) -> None:
        peers = self.connections.get(session_id)
        if peers:
            peers.discard(websocket)
            if not peers:
                self.connections.pop(session_id, None)

    async def broadcast(self, session_id: uuid.UUID, event: dict) -> None:
        for websocket in list(self.connections.get(session_id, set())):
            try:
                await websocket.send_json(event)
            except Exception:
                self.disconnect(session_id, websocket)


attendance_connections = AttendanceConnections()


@router.websocket("/ws/attendance/{session_id}")
async def attendance_session_socket(websocket: WebSocket, session_id: uuid.UUID) -> None:
    token = websocket.cookies.get("ams_session")
    if not token:
        await websocket.close(code=4401, reason="Authentication required")
        return
    try:
        user_id, auth_session_id = decode_access_token(token)
    except Exception:
        await websocket.close(code=4401, reason="Invalid session")
        return

    with SessionLocal() as db:
        from app.models.user import AuthSession, User

        auth_session = db.get(AuthSession, auth_session_id)
        user = db.get(User, user_id)
        attendance_session = db.get(AttendanceSession, session_id)
        if (
            not auth_session
            or auth_session.revoked_at is not None
            or not user
            or not user.is_active
            or user.role != UserRole.FACULTY
            or not attendance_session
            or attendance_session.status != AttendanceSessionStatus.OPEN
        ):
            await websocket.close(code=4403, reason="Session access denied")
            return
        try:
            _authorized_lecture(db, attendance_session.lecture_id, user.id)
        except Exception:
            await websocket.close(code=4403, reason="Session access denied")
            return
        count = (
            db.scalar(
                select(func.count(Attendance.id)).where(
                    Attendance.session_id == attendance_session.id
                )
            )
            or 0
        )
        await attendance_connections.connect(session_id, websocket)

    await websocket.send_json(
        {"type": "SESSION_STARTED", "session_id": str(session_id), "attendance_count": count}
    )
    try:
        while True:
            event = await websocket.receive_json()
            if event.get("type") == "PING":
                await websocket.send_json({"type": "PONG"})
            else:
                await websocket.send_json(
                    {"type": "ERROR", "message": "Send camera frames to the recognition API"}
                )
    except WebSocketDisconnect:
        attendance_connections.disconnect(session_id, websocket)
