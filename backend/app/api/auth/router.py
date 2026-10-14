from datetime import UTC, datetime

import jwt
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, decode_access_token
from app.dependencies.auth import get_current_user
from app.models.user import AuthSession, User
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RequestPasswordOtpRequest,
    ResetPasswordRequest,
    SessionResponse,
    UserResponse,
    VerifyPasswordOtpRequest,
)
from app.services.audit import record_audit
from app.services.auth import (
    AccountLocked,
    InvalidCredentials,
    authenticate,
    change_password,
    create_password_otp,
    create_password_reset,
    reset_password,
    verify_password_otp,
)
from app.services.email import send_otp_email, send_password_reset_email

router = APIRouter(prefix="/auth", tags=["authentication"])
COOKIE_NAME = "ams_session"


@router.post("/login", response_model=SessionResponse)
def login(
    payload: LoginRequest, response: Response, db: Session = Depends(get_db)
) -> SessionResponse:
    try:
        user, auth_session = authenticate(db, str(payload.email), payload.password)
    except AccountLocked:
        raise HTTPException(status_code=423, detail="Account temporarily locked") from None
    except InvalidCredentials:
        raise HTTPException(status_code=401, detail="Invalid email or password") from None

    expires_at = auth_session.expires_at
    response.set_cookie(
        COOKIE_NAME,
        create_access_token(user.id, auth_session.id, expires_at),
        httponly=True,
        secure=settings.env != "development",
        samesite=settings.cookie_samesite,
        max_age=settings.access_token_minutes * 60,
        path="/",
    )
    return SessionResponse(user=UserResponse.model_validate(user), expires_at=expires_at)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> Response:
    token = request.cookies.get(COOKIE_NAME)
    if token:
        try:
            _, session_id = decode_access_token(token)
        except (jwt.InvalidTokenError, ValueError, KeyError):
            pass
        else:
            auth_session = db.get(AuthSession, session_id)
            if auth_session and auth_session.revoked_at is None:
                auth_session.revoked_at = datetime.now(UTC)
                record_audit(
                    db,
                    actor_id=auth_session.user_id,
                    action="LOGOUT",
                    resource_type="auth",
                    resource_id=str(auth_session.user_id),
                )
                db.commit()
    response.delete_cookie(
        COOKIE_NAME,
        path="/",
        httponly=True,
        secure=settings.env != "development",
        samesite=settings.cookie_samesite,
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password_endpoint(
    payload: ChangePasswordRequest,
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    try:
        change_password(db, user, payload.current_password, payload.new_password)
    except InvalidCredentials:
        raise HTTPException(status_code=400, detail="Current password is incorrect") from None
    response.delete_cookie(
        COOKIE_NAME,
        path="/",
        httponly=True,
        secure=settings.env != "development",
        samesite=settings.cookie_samesite,
    )
    return response


@router.post("/forgot-password", status_code=202)
def forgot_password(
    payload: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    user = db.scalar(
        select(User).where(User.email == str(payload.email).lower(), User.is_active.is_(True))
    )
    if user:
        token = create_password_reset(db, user)
        background_tasks.add_task(send_password_reset_email, user.email, token)
    return {"detail": "If the account exists, password reset instructions have been sent"}


@router.post("/reset-password", status_code=204)
def reset_password_endpoint(
    payload: ResetPasswordRequest, db: Session = Depends(get_db)
) -> Response:
    if not reset_password(db, payload.token, payload.new_password):
        raise HTTPException(400, "Reset token is invalid or expired")
    return Response(status_code=204)


@router.post("/request-password-otp")
def request_password_otp(
    payload: RequestPasswordOtpRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str | None]:
    target_email = payload.email
    if not target_email:
        cookie = request.cookies.get(COOKIE_NAME)
        if cookie:
            try:
                claims = decode_access_token(cookie)
                user = db.get(User, claims.get("sub"))
                if user and user.is_active:
                    target_email = user.email
            except Exception:
                pass
    if not target_email:
        raise HTTPException(422, "Email is required to request a password verification code")

    user = db.scalar(
        select(User).where(User.email == str(target_email).lower(), User.is_active.is_(True))
    )
    dev_otp = None
    if user:
        otp = create_password_otp(db, user)
        background_tasks.add_task(send_otp_email, user.email, otp)
        if settings.env == "development":
            dev_otp = otp

    return {
        "detail": f"If an active account exists for {target_email}, a 6-digit verification code has been dispatched.",
        "dev_otp": dev_otp,
    }


@router.post("/verify-password-otp", status_code=200)
def verify_password_otp_endpoint(
    payload: VerifyPasswordOtpRequest, db: Session = Depends(get_db)
) -> dict[str, str]:
    success = verify_password_otp(
        db, str(payload.email).lower(), payload.otp, payload.new_password
    )
    if not success:
        raise HTTPException(400, "Invalid or expired verification code")
    return {"detail": "Password updated successfully. Please sign in with your new password."}
