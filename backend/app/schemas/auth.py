import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=12, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=20, max_length=256)
    new_password: str = Field(min_length=12, max_length=128)


class RequestPasswordOtpRequest(BaseModel):
    email: EmailStr | None = None


class VerifyPasswordOtpRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)
    new_password: str = Field(min_length=12, max_length=128)


class UserResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    institutional_id: str
    email: str
    full_name: str
    role: UserRole


class SessionResponse(BaseModel):
    model_config = {"from_attributes": True}

    user: UserResponse
    expires_at: datetime
