import logging
from pathlib import Path
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.dependencies.auth import require_roles
from app.models.exceptions import LeaveRequest, RequestStatus, SupportingDocument
from app.models.user import User, UserRole
from app.schemas.exceptions import SupportingDocumentResponse
from app.services.audit import record_audit
from app.services.storage import StorageUnavailable, get_storage_service

router = APIRouter(prefix="/student/requests", tags=["supporting documents"])
Student = Depends(require_roles(UserRole.STUDENT.value))
ALLOWED_TYPES = {
    ".pdf": {"application/pdf"},
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
}
FILE_SIGNATURES = {
    ".pdf": (b"%PDF-",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
}


@router.get("/{request_id}/documents", response_model=list[SupportingDocumentResponse])
def list_documents(
    request_id: UUID, student: User = Student, db: Session = Depends(get_db)
) -> list[SupportingDocument]:
    request = db.get(LeaveRequest, request_id)
    if not request or request.student_id != student.id:
        raise HTTPException(404, "Request not found")
    return list(
        db.scalars(select(SupportingDocument).where(SupportingDocument.request_id == request_id))
    )


@router.post("/{request_id}/documents", status_code=201)
async def upload_document(
    request_id: UUID,
    file: UploadFile = File(...),
    student: User = Student,
    db: Session = Depends(get_db),
) -> dict:
    request = db.get(LeaveRequest, request_id)
    if not request or request.student_id != student.id:
        raise HTTPException(404, "Request not found")
    if request.status != RequestStatus.PENDING:
        raise HTTPException(409, "Documents can only be attached to a pending request")
    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_TYPES or file.content_type not in ALLOWED_TYPES[extension]:
        raise HTTPException(415, "Only PDF, PNG, and JPEG documents are accepted")
    content = await file.read(settings.max_document_bytes + 1)
    if not content or len(content) > settings.max_document_bytes:
        raise HTTPException(413, "Document is empty or exceeds the configured size limit")
    if not content.startswith(FILE_SIGNATURES[extension]):
        raise HTTPException(415, "Document contents do not match the declared file type")
    try:
        storage = get_storage_service()
        key = storage.upload(file.filename or "document", content)
        document = SupportingDocument(
            request_id=request.id,
            storage_key=key,
            original_filename=Path(file.filename or "document").name[:255],
            content_type=file.content_type or "application/octet-stream",
            size_bytes=len(content),
        )
        db.add(document)
        db.flush()
        record_audit(
            db,
            actor_id=student.id,
            action="UPLOAD_DOCUMENT",
            resource_type="supporting_document",
            resource_id=str(document.id),
            after={"request_id": str(request.id), "size_bytes": len(content)},
        )
        db.commit()
        db.refresh(document)
        return {
            "id": str(document.id),
            "filename": document.original_filename,
            "size_bytes": document.size_bytes,
        }
    except Exception as error:
        db.rollback()
        if "key" in locals() and "storage" in locals():
            try:
                storage.delete(key)
            except Exception as cleanup_error:
                logging.getLogger(__name__).warning(
                    "Document cleanup failed (%s)", type(cleanup_error).__name__
                )
        if isinstance(error, StorageUnavailable):
            raise HTTPException(503, "Document storage is temporarily unavailable") from None
        raise


@router.get("/documents/{document_id}")
def download_document(
    document_id: UUID, student: User = Student, db: Session = Depends(get_db)
) -> Response:
    document = db.get(SupportingDocument, document_id)
    request = db.get(LeaveRequest, document.request_id) if document else None
    if not document or not request or request.student_id != student.id:
        raise HTTPException(404, "Document not found")
    try:
        content = get_storage_service().download(document.storage_key)
    except FileNotFoundError:
        raise HTTPException(404, "Document content is unavailable") from None
    except StorageUnavailable:
        raise HTTPException(503, "Document storage is temporarily unavailable") from None
    return Response(
        content,
        media_type=document.content_type,
        headers={
            "Content-Disposition": (
                f"attachment; filename*=UTF-8''{quote(document.original_filename, safe='')}"
            )
        },
    )
