from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import require_roles
from app.models.academic import CourseAllocation
from app.models.announcements import Announcement
from app.models.user import User, UserRole
from app.schemas.announcements import AnnouncementCreate, AnnouncementResponse
from app.services.audit import record_audit

router = APIRouter(prefix="/faculty/announcements", tags=["announcements"])
Faculty = Depends(require_roles(UserRole.FACULTY.value))


@router.get("", response_model=list[AnnouncementResponse])
def list_announcements(
    faculty: User = Faculty, db: Session = Depends(get_db)
) -> list[Announcement]:
    return list(
        db.scalars(
            select(Announcement)
            .where(Announcement.faculty_id == faculty.id)
            .order_by(Announcement.created_at.desc())
        )
    )


@router.post("", response_model=AnnouncementResponse, status_code=201)
def create_announcement(
    payload: AnnouncementCreate, faculty: User = Faculty, db: Session = Depends(get_db)
) -> Announcement:
    allocation = db.get(CourseAllocation, payload.allocation_id)
    if not allocation or not allocation.is_active:
        raise HTTPException(404, "Active course allocation not found")
    if allocation.faculty_id != faculty.id:
        raise HTTPException(403, "You are not assigned to this course")
    announcement = Announcement(faculty_id=faculty.id, **payload.model_dump())
    db.add(announcement)
    try:
        db.flush()
        record_audit(
            db,
            actor_id=faculty.id,
            action="CREATE",
            resource_type="announcement",
            resource_id=str(announcement.id),
            after={"allocation_id": str(allocation.id), "title": announcement.title},
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Announcement could not be saved") from None
    db.refresh(announcement)
    return announcement
