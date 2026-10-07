from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import require_roles
from app.models.academic import CourseAllocation
from app.models.audit import SystemSetting
from app.models.user import User, UserRole
from app.schemas.analytics import Defaulter
from app.services.analytics import defaulter_list

router = APIRouter(prefix="/faculty/analytics", tags=["faculty analytics"])
Faculty = Depends(require_roles(UserRole.FACULTY.value))


@router.get("/defaulters", response_model=list[Defaulter])
def defaulters(
    allocation_id: UUID,
    threshold: float | None = Query(default=None, ge=0, le=100),
    faculty: User = Faculty,
    db: Session = Depends(get_db),
) -> list[dict]:
    allocation = db.get(CourseAllocation, allocation_id)
    if not allocation:
        raise HTTPException(404, "Course allocation not found")
    if allocation.faculty_id != faculty.id:
        raise HTTPException(403, "You are not assigned to this course")
    try:
        setting = db.get(SystemSetting, "attendance_threshold")
        applied_threshold = (
            threshold
            if threshold is not None
            else float(setting.value["percentage"])
            if setting
            else 75.0
        )
        return defaulter_list(db, allocation_id, applied_threshold)
    except ValueError as error:
        raise HTTPException(422, str(error)) from None
