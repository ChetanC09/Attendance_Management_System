import uuid
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import settings

password_hasher = PasswordHasher()
JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def create_access_token(user_id: uuid.UUID, session_id: uuid.UUID, expires_at: datetime) -> str:
    return jwt.encode(
        {"sub": str(user_id), "sid": str(session_id), "exp": expires_at},
        settings.secret_key.get_secret_value(),
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> tuple[uuid.UUID, uuid.UUID]:
    claims = jwt.decode(token, settings.secret_key.get_secret_value(), algorithms=[JWT_ALGORITHM])
    return uuid.UUID(claims["sub"]), uuid.UUID(claims["sid"])


def access_token_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(minutes=settings.access_token_minutes)
