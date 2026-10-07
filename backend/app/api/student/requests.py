from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import require_roles
from app.models.exceptions import LeaveRequest
from app.models.user import User, UserRole
from app.schemas.exceptions import RequestCreate, RequestResponse
from app.services.exceptions import RequestRuleError, create_request

router = APIRouter(prefix="/student/requests", tags=["student requests"])
Student = Depends(require_roles(UserRole.STUDENT.value))


@router.post("", response_model=RequestResponse, status_code=201)
def submit_request(
    payload: RequestCreate, student: User = Student, db: Session = Depends(get_db)
) -> LeaveRequest:
    try:
        return create_request(db, student, payload.lecture_id, payload.request_type, payload.reason)
    except RequestRuleError as error:
        raise HTTPException(404 if "not found" in str(error).lower() else 403, str(error)) from None


@router.get("", response_model=list[RequestResponse])
def list_requests(student: User = Student, db: Session = Depends(get_db)) -> list[LeaveRequest]:
    return list(
        db.scalars(
            select(LeaveRequest)
            .where(LeaveRequest.student_id == student.id)
            .order_by(LeaveRequest.created_at.desc())
        )
    )


@router.get("/{request_id}", response_model=RequestResponse)
def read_request(
    request_id: UUID, student: User = Student, db: Session = Depends(get_db)
) -> LeaveRequest:
    request = db.get(LeaveRequest, request_id)
    if not request or request.student_id != student.id:
        raise HTTPException(404, "Request not found")
    return request
