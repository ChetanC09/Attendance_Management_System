import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.attendance import AttendanceSessionStatus, AttendanceSource, AttendanceStatus


class StartSessionRequest(BaseModel):
    lecture_id: uuid.UUID


class AttendanceSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    lecture_id: uuid.UUID
    opened_by: uuid.UUID
    status: AttendanceSessionStatus
    started_at: datetime
    closed_at: datetime | None


class ManualAttendanceRequest(BaseModel):
    session_id: uuid.UUID
    student_id: uuid.UUID
    status: AttendanceStatus = AttendanceStatus.PRESENT
    reason: str | None = Field(default=None, max_length=500)


class AttendanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    lecture_id: uuid.UUID
    status: AttendanceStatus
    source: AttendanceSource
    marked_by: uuid.UUID
    marked_at: datetime
    reason: str | None


class AttendanceUpdateRequest(BaseModel):
    status: AttendanceStatus
    reason: str = Field(min_length=5, max_length=500)


class AttendanceSessionDetail(AttendanceSessionResponse):
    records: list[AttendanceResponse]


class AttendanceRosterItem(BaseModel):
    student_id: uuid.UUID
    institutional_id: str
    full_name: str
    attendance_id: uuid.UUID | None
    status: AttendanceStatus | None
    source: AttendanceSource | None
    reason: str | None
