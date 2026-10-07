from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.attendance.websocket import attendance_connections
from app.core.config import settings
from app.core.database import get_db
from app.dependencies.auth import require_roles
from app.models.attendance import Attendance, AttendanceSession, AttendanceSource, AttendanceStatus
from app.models.user import User, UserRole
from app.schemas.attendance import (
    AttendanceResponse,
    AttendanceSessionDetail,
    AttendanceSessionResponse,
    AttendanceUpdateRequest,
    ManualAttendanceRequest,
    StartSessionRequest,
)
from app.services.attendance import (
    AttendanceRuleError,
    close_attendance_session,
    create_attendance_session,
    get_authorized_session,
    modify_attendance,
    record_attendance,
)
from app.vision.schemas import AttendanceRecognitionResponse, RecognitionState
from app.vision.service import recognize_image

router = APIRouter(prefix="/faculty/attendance", tags=["faculty attendance"])
Faculty = Depends(require_roles(UserRole.FACULTY.value))


def _raise_rule(error: AttendanceRuleError) -> None:
    message = str(error)
    code = (
        404 if "not found" in message.lower() else 403 if "not assigned" in message.lower() else 409
    )
    raise HTTPException(code, message) from None


@router.post("/session", response_model=AttendanceSessionResponse, status_code=201)
def start_session(
    payload: StartSessionRequest, faculty: User = Faculty, db: Session = Depends(get_db)
) -> AttendanceSession:
    try:
        return create_attendance_session(db, faculty, payload.lecture_id)
    except AttendanceRuleError as error:
        _raise_rule(error)


@router.get("/session/{session_id}", response_model=AttendanceSessionDetail)
def read_session(session_id: UUID, faculty: User = Faculty, db: Session = Depends(get_db)) -> dict:
    try:
        session = get_authorized_session(db, faculty, session_id)
    except AttendanceRuleError as error:
        _raise_rule(error)
    records = list(db.scalars(select(Attendance).where(Attendance.session_id == session.id)))
    return {**AttendanceSessionResponse.model_validate(session).model_dump(), "records": records}


@router.post("/manual", response_model=AttendanceResponse, status_code=201)
async def manual_attendance(
    payload: ManualAttendanceRequest, faculty: User = Faculty, db: Session = Depends(get_db)
) -> Attendance:
    try:
        session = get_authorized_session(db, faculty, payload.session_id)
        row = record_attendance(
            db, faculty, session, payload.student_id, payload.status, payload.reason
        )
        await attendance_connections.broadcast(
            session.id,
            {
                "type": "ATTENDANCE_RECORDED",
                "attendance_id": str(row.id),
                "student_id": str(row.student_id),
            },
        )
        return row
    except AttendanceRuleError as error:
        _raise_rule(error)


@router.patch("/{attendance_id}", response_model=AttendanceResponse)
def update_attendance(
    attendance_id: UUID,
    payload: AttendanceUpdateRequest,
    faculty: User = Faculty,
    db: Session = Depends(get_db),
) -> Attendance:
    try:
        return modify_attendance(db, faculty, attendance_id, payload.status, payload.reason)
    except AttendanceRuleError as error:
        _raise_rule(error)


@router.post("/session/{session_id}/close", response_model=AttendanceSessionResponse)
async def close_session(
    session_id: UUID, faculty: User = Faculty, db: Session = Depends(get_db)
) -> AttendanceSession:
    try:
        session = get_authorized_session(db, faculty, session_id)
        closed = close_attendance_session(db, faculty, session)
        await attendance_connections.broadcast(
            session.id, {"type": "SESSION_CLOSED", "session_id": str(session.id)}
        )
        return closed
    except AttendanceRuleError as error:
        _raise_rule(error)


@router.post("/session/{session_id}/recognize", response_model=AttendanceRecognitionResponse)
async def recognize_attendance(
    session_id: UUID,
    image: UploadFile = File(...),
    faculty: User = Faculty,
    db: Session = Depends(get_db),
) -> AttendanceRecognitionResponse:
    try:
        session = get_authorized_session(db, faculty, session_id)
    except AttendanceRuleError as error:
        _raise_rule(error)
    if image.content_type not in {"image/jpeg", "image/png"}:
        raise HTTPException(415, "Image must be JPEG or PNG")
    content = await image.read(settings.max_document_bytes + 1)
    if not content or len(content) > settings.max_document_bytes:
        raise HTTPException(413, "Image is empty or exceeds the configured size limit")
    result = recognize_image(content, db, settings.vision_minimum_confidence)
    if result.state != RecognitionState.RECOGNIZED or not result.student_id:
        return AttendanceRecognitionResponse(
            state=result.state, confidence=result.confidence, message=result.message
        )
    try:
        row = record_attendance(
            db,
            faculty,
            session,
            result.student_id,
            AttendanceStatus.PRESENT,
            None,
            source=AttendanceSource.VISION,
        )
    except AttendanceRuleError as error:
        if "already been recorded" in str(error):
            return AttendanceRecognitionResponse(
                state=RecognitionState.RECOGNIZED,
                attendance_state="duplicate",
                student_id=result.student_id,
                confidence=result.confidence,
                message="Attendance was already recorded",
            )
        _raise_rule(error)
    row.recognition_metadata = {"confidence": result.confidence}
    db.commit()
    await attendance_connections.broadcast(
        session.id,
        {
            "type": "ATTENDANCE_RECORDED",
            "attendance_id": str(row.id),
            "student_id": str(row.student_id),
            "confidence": result.confidence,
        },
    )
    return AttendanceRecognitionResponse(
        state=RecognitionState.RECOGNIZED,
        attendance_state="recorded",
        student_id=result.student_id,
        confidence=result.confidence,
    )
