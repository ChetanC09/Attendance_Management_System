from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.dependencies.auth import require_roles
from app.models.user import User, UserRole


def test_role_dependency_returns_allowed_user() -> None:
    user = User(id=uuid4(), role=UserRole.FACULTY)
    dependency = require_roles(UserRole.FACULTY.value)

    assert dependency(user) is user


def test_role_dependency_rejects_unlisted_role() -> None:
    user = User(id=uuid4(), role=UserRole.STUDENT)
    dependency = require_roles(UserRole.ADMIN.value)

    with pytest.raises(HTTPException) as error:
        dependency(user)

    assert error.value.status_code == 403
