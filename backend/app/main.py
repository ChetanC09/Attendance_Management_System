from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.admin.academic import router as academic_router
from app.api.admin.operations import router as admin_operations_router
from app.api.admin.users import router as admin_users_router
from app.api.attendance.websocket import router as attendance_websocket_router
from app.api.auth.router import router as auth_router
from app.api.faculty.analytics import router as faculty_analytics_router
from app.api.faculty.attendance import router as faculty_attendance_router
from app.api.faculty.requests import router as faculty_requests_router
from app.api.faculty.timetable import router as faculty_timetable_router
from app.api.student.attendance import router as student_attendance_router
from app.api.student.documents import router as student_documents_router
from app.api.student.face_profile import router as student_face_router
from app.api.student.notifications import router as student_notifications_router
from app.api.student.requests import router as student_requests_router
from app.core.config import settings
from app.core.database import get_db
from app.core.logging import configure_logging

configure_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title="Attendance Management System API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(academic_router, prefix=settings.api_prefix)
app.include_router(faculty_attendance_router, prefix=settings.api_prefix)
app.include_router(faculty_timetable_router, prefix=settings.api_prefix)
app.include_router(faculty_analytics_router, prefix=settings.api_prefix)
app.include_router(student_attendance_router, prefix=settings.api_prefix)
app.include_router(student_requests_router, prefix=settings.api_prefix)
app.include_router(student_documents_router, prefix=settings.api_prefix)
app.include_router(faculty_requests_router, prefix=settings.api_prefix)
app.include_router(student_notifications_router, prefix=settings.api_prefix)
app.include_router(admin_users_router, prefix=settings.api_prefix)
app.include_router(admin_operations_router, prefix=settings.api_prefix)
app.include_router(student_face_router, prefix=settings.api_prefix)
app.include_router(attendance_websocket_router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get(f"{settings.api_prefix}/health", tags=["health"])
def api_health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
def readiness(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ready", "database": "ok"}
