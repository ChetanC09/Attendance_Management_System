import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.models.user import AuthSession, PasswordResetToken, User
from app.services.audit import record_audit

MAX_FAILED_LOGINS = 5
LOCK_MINUTES = 15


class InvalidCredentials(Exception):
    pass


class AccountLocked(Exception):
    pass


def authenticate(db: Session, email: str, password: str) -> tuple[User, AuthSession]:
    user = db.scalar(select(User).where(User.email == email.lower()))
    if not user or not user.is_active:
        record_audit(
            db,
            actor_id=user.id if user else None,
            action="LOGIN_FAILED",
            resource_type="auth",
            resource_id=str(user.id) if user else None,
            reason="inactive_account" if user else "unknown_account",
        )
        db.commit()
        raise InvalidCredentials

    now = datetime.now(UTC)
    if user.locked_until and user.locked_until > now:
        record_audit(
            db,
            actor_id=user.id,
            action="LOGIN_FAILED",
            resource_type="auth",
            resource_id=str(user.id),
            reason="account_locked",
        )
        db.commit()
        raise AccountLocked
    if user.locked_until:
        user.locked_until = None
        user.failed_login_attempts = 0

    if not verify_password(password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= MAX_FAILED_LOGINS:
            user.locked_until = now + timedelta(minutes=LOCK_MINUTES)
            record_audit(
                db,
                actor_id=user.id,
                action="LOGIN_FAILED",
                resource_type="auth",
                resource_id=str(user.id),
                reason="lock_threshold_reached",
            )
            db.commit()
            raise AccountLocked
        record_audit(
            db,
            actor_id=user.id,
            action="LOGIN_FAILED",
            resource_type="auth",
            resource_id=str(user.id),
            reason="invalid_credentials",
        )
        db.commit()
        raise InvalidCredentials

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    auth_session = AuthSession(
        user=user,
        expires_at=now + timedelta(minutes=settings.access_token_minutes),
    )
    db.add(auth_session)
    record_audit(
        db, actor_id=user.id, action="LOGIN_SUCCESS", resource_type="auth", resource_id=str(user.id)
    )
    db.commit()
    db.refresh(auth_session)
    return user, auth_session


def change_password(db: Session, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise InvalidCredentials
    user.password_hash = hash_password(new_password)
    for session in db.scalars(
        select(AuthSession).where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
    ):
        session.revoked_at = datetime.now(UTC)
    record_audit(
        db,
        actor_id=user.id,
        action="CHANGE_PASSWORD",
        resource_type="user",
        resource_id=str(user.id),
    )
    db.commit()


def create_password_reset(db: Session, user: User) -> str:
    raw_token = secrets.token_urlsafe(32)
    digest = hashlib.sha256(
        f"{settings.secret_key.get_secret_value()}:{raw_token}".encode()
    ).hexdigest()
    now = datetime.now(UTC)
    for token in db.scalars(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
        )
    ):
        token.used_at = now
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_digest=digest,
            expires_at=now + timedelta(minutes=30),
        )
    )
    db.commit()
    return raw_token


def reset_password(db: Session, raw_token: str, new_password: str) -> bool:
    digest = hashlib.sha256(
        f"{settings.secret_key.get_secret_value()}:{raw_token}".encode()
    ).hexdigest()
    now = datetime.now(UTC)
    reset = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_digest == digest,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
        )
    )
    if not reset:
        return False
    user = db.get(User, reset.user_id)
    if not user or not user.is_active:
        return False
    user.password_hash = hash_password(new_password)
    reset.used_at = now
    for session in db.scalars(
        select(AuthSession).where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
    ):
        session.revoked_at = now
    record_audit(
        db,
        actor_id=user.id,
        action="RESET_PASSWORD",
        resource_type="user",
        resource_id=str(user.id),
    )
    db.commit()
    return True
