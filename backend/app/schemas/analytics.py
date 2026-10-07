import uuid

from pydantic import BaseModel


class CourseAttendanceSummary(BaseModel):
    course_id: uuid.UUID
    course_code: str
    course_name: str
    conducted_lectures: int
    attended_lectures: int
    attendance_percentage: float


class RecoveryPlan(BaseModel):
    attended_lectures: int
    conducted_lectures: int
    current_percentage: float
    target_percentage: float
    required_lectures: int
    projected_percentage: float
    achievable: bool


class AttendanceProjection(BaseModel):
    current_percentage: float
    projected_percentage: float
    potential_absences: int
    threshold_percentage: float
    at_risk: bool


class OverallAttendanceSummary(BaseModel):
    attended_lectures: int
    conducted_lectures: int
    attendance_percentage: float


class Defaulter(BaseModel):
    student_id: uuid.UUID
    institutional_id: str
    full_name: str
    attended_lectures: int
    conducted_lectures: int
    attendance_percentage: float


class AttendanceHistoryItem(BaseModel):
    lecture_id: uuid.UUID
    course_code: str
    course_name: str
    starts_at: str
    status: str | None
