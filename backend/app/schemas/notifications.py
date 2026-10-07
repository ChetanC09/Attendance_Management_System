import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.notifications import NotificationChannel, NotificationStatus


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    message: str
    channel: NotificationChannel
    status: NotificationStatus
    payload: dict | None
    read_at: datetime | None
    created_at: datetime
