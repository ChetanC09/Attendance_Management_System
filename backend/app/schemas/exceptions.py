import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.exceptions import RequestStatus, RequestType


class RequestCreate(BaseModel):
    lecture_id: uuid.UUID
    request_type: RequestType
    reason: str = Field(min_length=10, max_length=2000)


class RequestReview(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)


class RequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    lecture_id: uuid.UUID | None
    request_type: RequestType
    status: RequestStatus
    reason: str
    reviewed_by: uuid.UUID | None
    review_reason: str | None
    reviewed_at: datetime | None
    created_at: datetime


class SupportingDocumentResponse(BaseModel):
    id: uuid.UUID
    original_filename: str
    content_type: str
    size_bytes: int
    storage_key: str
