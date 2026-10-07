import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class AdminUserCreate(BaseModel):
    institutional_id: str = Field(min_length=1, max_length=64)
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=160)
    phone_number: str | None = Field(default=None, pattern=r"^\+[1-9]\d{7,14}$")
    password: str = Field(min_length=12, max_length=128)
    role: UserRole
    department_id: uuid.UUID | None = None
    section_id: uuid.UUID | None = None


class AdminUserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=160)
    is_active: bool | None = None
    phone_number: str | None = Field(default=None, pattern=r"^\+[1-9]\d{7,14}$")


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    institutional_id: str
    email: str
    full_name: str
    phone_number: str | None
    role: UserRole
    is_active: bool
    created_at: datetime


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_id: uuid.UUID | None
    action: str
    resource_type: str
    resource_id: str | None
    before_state: dict | None
    after_state: dict | None
    reason: str | None
    occurred_at: datetime
