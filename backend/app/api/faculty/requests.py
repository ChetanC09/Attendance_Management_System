from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import require_roles
from app.models.academic import CourseAllocation
from app.models.exceptions import LeaveRequest, SupportingDocument
from app.models.timetable import Lecture
from app.models.user import User, UserRole
from app.schemas.exceptions import RequestResponse, RequestReview, SupportingDocumentResponse
from app.services.exceptions import RequestRuleError, review_request
from app.services.notifications import enqueue_in_app_notification
from app.services.storage import get_storage_service

router = APIRouter(prefix="/faculty/requests", tags=["faculty requests"])
Faculty = Depends(require_roles(UserRole.FACULTY.value))


@router.get("", response_model=list[RequestResponse])
def list_requests(faculty: User = Faculty, db: Session = Depends(get_db)) -> list[LeaveRequest]:
    return list(
        db.scalars(
            select(LeaveRequest)
            .join(Lecture, Lecture.id == LeaveRequest.lecture_id)
            .join(CourseAllocation, CourseAllocation.id == Lecture.allocation_id)
            .where(CourseAllocation.faculty_id == faculty.id)
            .order_by(LeaveRequest.created_at.desc())
        )
    )


@router.get("/{request_id}", response_model=RequestResponse)
def read_request(
    request_id: UUID, faculty: User = Faculty, db: Session = Depends(get_db)
) -> LeaveRequest:
    request = db.get(LeaveRequest, request_id)
    lecture = db.get(Lecture, request.lecture_id) if request and request.lecture_id else None
    allocation = db.get(CourseAllocation, lecture.allocation_id) if lecture else None
    if not request or not allocation or allocation.faculty_id != faculty.id:
        raise HTTPException(404, "Request not found")
    return request


@router.get("/{request_id}/documents", response_model=list[SupportingDocumentResponse])
def list_request_documents(
    request_id: UUID, faculty: User = Faculty, db: Session = Depends(get_db)
) -> list[SupportingDocument]:
    request = db.get(LeaveRequest, request_id)
    lecture = db.get(Lecture, request.lecture_id) if request and request.lecture_id else None
    allocation = db.get(CourseAllocation, lecture.allocation_id) if lecture else None
    if not request or not allocation or allocation.faculty_id != faculty.id:
        raise HTTPException(404, "Request not found")
    return list(
        db.scalars(select(SupportingDocument).where(SupportingDocument.request_id == request_id))
    )


@router.get("/documents/{document_id}")
def download_supporting_document(
    document_id: UUID, faculty: User = Faculty, db: Session = Depends(get_db)
) -> Response:
    document = db.get(SupportingDocument, document_id)
    request = db.get(LeaveRequest, document.request_id) if document else None
    lecture = db.get(Lecture, request.lecture_id) if request and request.lecture_id else None
    allocation = db.get(CourseAllocation, lecture.allocation_id) if lecture else None
    if not document or not request or not allocation or allocation.faculty_id != faculty.id:
        raise HTTPException(404, "Document not found")
    try:
        content = get_storage_service().download(document.storage_key)
    except FileNotFoundError:
        raise HTTPException(404, "Document content is unavailable") from None
    return Response(content, media_type=document.content_type)


def _review(
    request_id: UUID,
    approve: bool,
    payload: RequestReview,
    faculty: User,
    db: Session,
    background_tasks: BackgroundTasks,
) -> LeaveRequest:
    try:
        request = review_request(db, faculty, request_id, approve, payload.reason)
    except RequestRuleError as error:
        message = str(error)
        code = (
            404
            if "not found" in message.lower()
            else 403
            if "not assigned" in message.lower()
            else 409
        )
        raise HTTPException(code, message) from None
    background_tasks.add_task(
        enqueue_in_app_notification,
        request.student_id,
        "Request decision",
        f"Your {request.request_type.value.lower()} request was {request.status.value.lower()}.",
        {"request_id": str(request.id), "status": request.status.value},
    )
    return request


@router.post("/{request_id}/approve", response_model=RequestResponse)
def approve_request(
    request_id: UUID,
    payload: RequestReview,
    background_tasks: BackgroundTasks,
    faculty: User = Faculty,
    db: Session = Depends(get_db),
) -> LeaveRequest:
    return _review(request_id, True, payload, faculty, db, background_tasks)


@router.post("/{request_id}/reject", response_model=RequestResponse)
def reject_request(
    request_id: UUID,
    payload: RequestReview,
    background_tasks: BackgroundTasks,
    faculty: User = Faculty,
    db: Session = Depends(get_db),
) -> LeaveRequest:
    return _review(request_id, False, payload, faculty, db, background_tasks)
