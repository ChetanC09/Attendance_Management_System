"""Create the first administrator from explicit environment values."""

import os

from sqlalchemy import select, text

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole


def require_production_environment() -> None:
    if settings.env != "production":
        raise SystemExit("Administrator bootstrap is production-only")


def require_first_admin(db) -> None:
    # Serialize concurrent bootstrap invocations across API instances.
    db.execute(text("SELECT pg_advisory_xact_lock(1095582465)"))
    existing_admin = db.scalar(select(User.id).where(User.role == UserRole.ADMIN).limit(1))
    if existing_admin:
        raise SystemExit("An administrator already exists; bootstrap is disabled")


def main() -> None:
    require_production_environment()
    email = os.environ["AMS_BOOTSTRAP_ADMIN_EMAIL"].strip().lower()
    institutional_id = os.environ["AMS_BOOTSTRAP_ADMIN_ID"].strip()
    full_name = os.environ["AMS_BOOTSTRAP_ADMIN_NAME"].strip()
    password = os.environ["AMS_BOOTSTRAP_ADMIN_PASSWORD"]
    if not email or not institutional_id or not full_name:
        raise SystemExit("Bootstrap email, institutional ID, and name must be non-empty")
    if len(password) < 12:
        raise SystemExit("AMS_BOOTSTRAP_ADMIN_PASSWORD must be at least 12 characters")

    with SessionLocal.begin() as db:
        require_first_admin(db)
        duplicate = db.scalar(
            select(User.id).where(
                (User.email == email) | (User.institutional_id == institutional_id)
            )
        )
        if duplicate:
            raise SystemExit("An account already uses this email or institutional ID")
        db.add(
            User(
                email=email,
                institutional_id=institutional_id,
                full_name=full_name,
                password_hash=hash_password(password),
                role=UserRole.ADMIN,
            )
        )
    print("Initial administrator account created")


if __name__ == "__main__":
    main()
