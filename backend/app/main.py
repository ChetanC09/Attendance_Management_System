import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError
from sqlalchemy.orm import Session

from app.api.admin.academic import router as academic_router
from app.api.admin.operations import router as admin_operations_router
from app.api.admin.users import router as admin_users_router
from app.api.attendance.websocket import router as attendance_websocket_router
from app.api.auth.router import router as auth_router
from app.api.faculty.analytics import router as faculty_analytics_router
from app.api.faculty.announcements import router as faculty_announcements_router
from app.api.faculty.attendance import router as faculty_attendance_router
from app.api.faculty.requests import router as faculty_requests_router
from app.api.faculty.timetable import router as faculty_timetable_router
from app.api.student.announcements import router as student_announcements_router
from app.api.student.attendance import router as student_attendance_router
from app.api.student.documents import router as student_documents_router
from app.api.student.face_profile import router as student_face_router
from app.api.student.notifications import router as student_notifications_router
from app.api.student.requests import router as student_requests_router
from app.core.config import settings
from app.core.database import get_db
from app.core.logging import configure_logging

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title="Attendance Management System API", version="0.1.0", lifespan=lifespan)
request_limiter = asyncio.Semaphore(settings.http_request_concurrency)


@app.exception_handler(SQLAlchemyTimeoutError)
async def database_pool_timeout_handler(_request, _error: SQLAlchemyTimeoutError):
    logger.warning("Database connection pool checkout timed out")
    return JSONResponse(
        status_code=503,
        content={"detail": "Database capacity is temporarily unavailable"},
        headers={"Retry-After": "1"},
    )


@app.middleware("http")
async def limit_database_backed_http_concurrency(request, call_next):
    async with request_limiter:
        return await call_next(request)


@app.middleware("http")
async def validate_browser_origin(request, call_next):
    """Reject cross-site writes; deployed Vercel cookies use SameSite=None."""
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        if origin and origin not in settings.cors_origins:
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=403, content={"detail": "Request origin is not allowed"}
            )
    return await call_next(request)


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy", "camera=(self), microphone=(), geolocation=()"
    )
    if settings.env == "production":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(academic_router, prefix=settings.api_prefix)
app.include_router(faculty_attendance_router, prefix=settings.api_prefix)
app.include_router(faculty_timetable_router, prefix=settings.api_prefix)
app.include_router(faculty_analytics_router, prefix=settings.api_prefix)
app.include_router(faculty_announcements_router, prefix=settings.api_prefix)
app.include_router(student_attendance_router, prefix=settings.api_prefix)
app.include_router(student_announcements_router, prefix=settings.api_prefix)
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
