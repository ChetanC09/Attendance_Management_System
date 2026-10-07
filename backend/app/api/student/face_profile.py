from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.dependencies.auth import require_roles
from app.models.attendance import FaceEmbedding, FaceProfile
from app.models.user import User, UserRole
from app.services.audit import record_audit
from app.vision.service import get_vision_engine

router = APIRouter(prefix="/student/face-profile", tags=["face profile"])
Student = Depends(require_roles(UserRole.STUDENT.value))


@router.post("/enroll", status_code=201)
async def enroll_face(
    consent: bool = Form(...),
    image: UploadFile = File(...),
    student: User = Student,
    db: Session = Depends(get_db),
) -> dict:
    if not consent:
        raise HTTPException(422, "Explicit face-recognition consent is required")
    if image.content_type not in {"image/jpeg", "image/png"}:
        raise HTTPException(415, "Enrollment image must be JPEG or PNG")
    content = await image.read(settings.max_document_bytes + 1)
    if not content or len(content) > settings.max_document_bytes:
        raise HTTPException(413, "Image is empty or exceeds the configured size limit")
    try:
        engine = get_vision_engine()
        embedding, count = engine.embedding_from_image(content)
    except RuntimeError as error:
        raise HTTPException(503, str(error)) from None
    if count != 1 or not embedding:
        raise HTTPException(422, "Enrollment image must contain exactly one clearly detected face")
    profile = db.scalar(select(FaceProfile).where(FaceProfile.student_id == student.id))
    now = datetime.now(UTC)
    if profile:
        profile.revoked_at = None
        profile.consented_at = now
    else:
        profile = FaceProfile(student_id=student.id, consented_at=now)
        db.add(profile)
        db.flush()
    embedding_row = FaceEmbedding(
        profile_id=profile.id, embedding=embedding, model_version="insightface-buffalo_l"
    )
    db.add(embedding_row)
    record_audit(
        db,
        actor_id=student.id,
        action="ENROLL_FACE",
        resource_type="face_profile",
        resource_id=str(profile.id),
        after={"model_version": embedding_row.model_version},
    )
    db.commit()
    return {"status": "enrolled", "profile_id": str(profile.id)}


@router.delete("", status_code=204)
def revoke_face(student: User = Student, db: Session = Depends(get_db)) -> None:
    profile = db.scalar(select(FaceProfile).where(FaceProfile.student_id == student.id))
    if profile and profile.revoked_at is None:
        profile.revoked_at = datetime.now(UTC)
        record_audit(
            db,
            actor_id=student.id,
            action="REVOKE_FACE",
            resource_type="face_profile",
            resource_id=str(profile.id),
        )
        db.commit()
