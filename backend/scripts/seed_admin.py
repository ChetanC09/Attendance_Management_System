"""Create the first administrator from explicit environment values."""

import os

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole


def main() -> None:
    email = os.environ["AMS_BOOTSTRAP_ADMIN_EMAIL"].strip().lower()
    institutional_id = os.environ["AMS_BOOTSTRAP_ADMIN_ID"].strip()
    full_name = os.environ["AMS_BOOTSTRAP_ADMIN_NAME"].strip()
    password = os.environ["AMS_BOOTSTRAP_ADMIN_PASSWORD"]
    if len(password) < 12:
        raise SystemExit("AMS_BOOTSTRAP_ADMIN_PASSWORD must be at least 12 characters")

    with SessionLocal.begin() as db:
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
    print(f"Administrator account created for {email}")


if __name__ == "__main__":
    main()
