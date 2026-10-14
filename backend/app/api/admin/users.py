from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password
from app.dependencies.auth import require_roles
from app.models.academic import Department, FacultyProfile, Section, StudentProfile
from app.models.user import AuthSession, User, UserRole
from app.schemas.admin import AdminUserCreate, AdminUserResponse, AdminUserUpdate
from app.services.audit import record_audit

router = APIRouter(prefix="/admin/users", tags=["user administration"])
Admin = Depends(require_roles(UserRole.ADMIN.value))


def _user_to_response(user: User, db: Session) -> AdminUserResponse:
    dept_id = None
    section_id = None
    if user.role == UserRole.STUDENT:
        prof = db.scalar(select(StudentProfile).where(StudentProfile.user_id == user.id))
        if prof:
            dept_id = prof.department_id
            section_id = prof.section_id
    elif user.role == UserRole.FACULTY:
        prof = db.scalar(select(FacultyProfile).where(FacultyProfile.user_id == user.id))
        if prof:
            dept_id = prof.department_id
    return AdminUserResponse(
        id=user.id,
        institutional_id=user.institutional_id,
        email=user.email,
        full_name=user.full_name,
        phone_number=user.phone_number,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        department_id=dept_id,
        section_id=section_id,
    )


@router.get("", response_model=list[AdminUserResponse])
def list_users(
    role: UserRole | None = None,
    active: bool | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _: User = Admin,
    db: Session = Depends(get_db),
) -> list[AdminUserResponse]:
    statement = select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
    if role:
        statement = statement.where(User.role == role)
    if active is not None:
        statement = statement.where(User.is_active.is_(active))
    users = list(db.scalars(statement))
    return [_user_to_response(u, db) for u in users]


@router.post("", response_model=AdminUserResponse, status_code=201)
def create_user(
    payload: AdminUserCreate, admin: User = Admin, db: Session = Depends(get_db)
) -> AdminUserResponse:
    if payload.department_id and not db.get(Department, payload.department_id):
        raise HTTPException(404, "Department not found")
    section = None
    if payload.role == UserRole.STUDENT:
        if payload.section_id:
            section = db.get(Section, payload.section_id)
            if not section or not section.is_active:
                raise HTTPException(422, "Selected section is invalid or inactive")
            if payload.department_id and payload.department_id != section.department_id:
                raise HTTPException(422, "Student department must match the assigned section")
    elif payload.section_id:
        raise HTTPException(422, "Only students can be assigned directly to a section")

    user = User(
        institutional_id=payload.institutional_id,
        email=str(payload.email).lower(),
        full_name=payload.full_name,
        phone_number=payload.phone_number,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    try:
        db.flush()
        if payload.role == UserRole.STUDENT:
            db.add(
                StudentProfile(
                    user_id=user.id,
                    department_id=payload.department_id or (section.department_id if section else None),
                    section_id=section.id if section else None,
                )
            )
        elif payload.role == UserRole.FACULTY:
            db.add(FacultyProfile(user_id=user.id, department_id=payload.department_id))
        record_audit(
            db,
            actor_id=admin.id,
            action="CREATE",
            resource_type="user",
            resource_id=str(user.id),
            after={"institutional_id": user.institutional_id, "role": user.role.value},
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Email or institutional ID is already in use") from None
    db.refresh(user)
    return _user_to_response(user, db)


@router.patch("/{user_id}", response_model=AdminUserResponse)
def update_user(
    user_id: UUID,
    payload: AdminUserUpdate,
    admin: User = Admin,
    db: Session = Depends(get_db),
) -> AdminUserResponse:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(422, "At least one field must be provided")

    section_id = changes.pop("section_id", None)
    department_id = changes.pop("department_id", None)

    before = {key: getattr(user, key) for key in changes}
    for key, value in changes.items():
        setattr(user, key, value)

    if changes.get("is_active") is False:
        for auth_session in db.scalars(
            select(AuthSession).where(
                AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None)
            )
        ):
            auth_session.revoked_at = datetime.now(UTC)

    # Handle profile updates (section/department)
    if user.role == UserRole.STUDENT:
        prof = db.scalar(select(StudentProfile).where(StudentProfile.user_id == user.id))
        if not prof:
            prof = StudentProfile(user_id=user.id)
            db.add(prof)
        if section_id is not None:
            if section_id:
                sec = db.get(Section, section_id)
                if not sec or not sec.is_active:
                    raise HTTPException(422, "Section not found or inactive")
                prof.section_id = sec.id
                if not department_id and not prof.department_id:
                    prof.department_id = sec.department_id
            else:
                prof.section_id = None
        if department_id is not None:
            prof.department_id = department_id if department_id else None
    elif user.role == UserRole.FACULTY:
        prof = db.scalar(select(FacultyProfile).where(FacultyProfile.user_id == user.id))
        if not prof:
            prof = FacultyProfile(user_id=user.id)
            db.add(prof)
        if department_id is not None:
            prof.department_id = department_id if department_id else None

    record_audit(
        db,
        actor_id=admin.id,
        action="UPDATE",
        resource_type="user",
        resource_id=str(user_id),
        before={key: str(value) for key, value in before.items()},
        after={key: str(getattr(user, key)) for key in changes},
    )
    db.commit()
    db.refresh(user)
    return _user_to_response(user, db)
