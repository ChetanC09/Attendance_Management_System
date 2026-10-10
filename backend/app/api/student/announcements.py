from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import require_roles
from app.models.academic import CourseAllocation, StudentProfile
from app.models.announcements import Announcement
from app.models.user import User, UserRole
from app.schemas.announcements import AnnouncementResponse

router = APIRouter(prefix="/student/announcements", tags=["announcements"])
Student = Depends(require_roles(UserRole.STUDENT.value))


@router.get("", response_model=list[AnnouncementResponse])
def list_announcements(
    student: User = Student, db: Session = Depends(get_db)
) -> list[Announcement]:
    section_id = (
        select(StudentProfile.section_id)
        .where(StudentProfile.user_id == student.id)
        .scalar_subquery()
    )
    statement = (
        select(Announcement)
        .join(CourseAllocation, CourseAllocation.id == Announcement.allocation_id)
        .where(CourseAllocation.section_id == section_id, CourseAllocation.is_active.is_(True))
        .order_by(Announcement.created_at.desc())
        .limit(200)
    )
    return list(db.scalars(statement))
