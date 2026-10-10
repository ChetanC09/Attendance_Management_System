import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AnnouncementCreate(BaseModel):
    allocation_id: uuid.UUID
    title: str = Field(min_length=3, max_length=160)
    body: str = Field(min_length=1, max_length=5000)


class AnnouncementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    faculty_id: uuid.UUID
    allocation_id: uuid.UUID
    title: str
    body: str
    created_at: datetime
