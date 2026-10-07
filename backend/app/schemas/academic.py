import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DepartmentCreate(BaseModel):
    code: str = Field(min_length=2, max_length=24)
    name: str = Field(min_length=2, max_length=160)


class DepartmentUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=2, max_length=24)
    name: str | None = Field(default=None, min_length=2, max_length=160)
    is_active: bool | None = None


class AcademicYearUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=4, max_length=32)
    starts_on: date | None = None
    ends_on: date | None = None
    is_active: bool | None = None


class CourseUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=32)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    credits: int | None = Field(default=None, ge=0, le=30)
    is_active: bool | None = None


class ClassroomUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=32)
    name: str | None = Field(default=None, min_length=1, max_length=128)
    capacity: int | None = Field(default=None, ge=1)
    is_active: bool | None = None


class DepartmentResponse(ORMModel):
    id: uuid.UUID
    code: str
    name: str
    is_active: bool


class AcademicYearCreate(BaseModel):
    name: str = Field(min_length=4, max_length=32)
    starts_on: date
    ends_on: date


class AcademicYearResponse(ORMModel):
    id: uuid.UUID
    name: str
    starts_on: date
    ends_on: date
    is_active: bool


class SemesterCreate(BaseModel):
    academic_year_id: uuid.UUID
    number: int = Field(ge=1, le=12)
    starts_on: date
    ends_on: date


class SemesterUpdate(BaseModel):
    number: int | None = Field(default=None, ge=1, le=12)
    starts_on: date | None = None
    ends_on: date | None = None
    is_active: bool | None = None


class SemesterResponse(ORMModel):
    id: uuid.UUID
    academic_year_id: uuid.UUID
    number: int
    starts_on: date
    ends_on: date
    is_active: bool


class SectionCreate(BaseModel):
    department_id: uuid.UUID
    academic_year_id: uuid.UUID
    name: str = Field(min_length=1, max_length=64)


class SectionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    is_active: bool | None = None


class SectionResponse(ORMModel):
    id: uuid.UUID
    department_id: uuid.UUID
    academic_year_id: uuid.UUID
    name: str
    is_active: bool


class CourseCreate(BaseModel):
    department_id: uuid.UUID
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=160)
    credits: int = Field(default=0, ge=0, le=30)


class CourseResponse(ORMModel):
    id: uuid.UUID
    department_id: uuid.UUID
    code: str
    name: str
    credits: int
    is_active: bool


class ClassroomCreate(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=128)
    capacity: int | None = Field(default=None, ge=1)


class ClassroomResponse(ORMModel):
    id: uuid.UUID
    code: str
    name: str
    capacity: int | None
    is_active: bool


class AllocationCreate(BaseModel):
    course_id: uuid.UUID
    semester_id: uuid.UUID
    section_id: uuid.UUID
    faculty_id: uuid.UUID


class AllocationUpdate(BaseModel):
    faculty_id: uuid.UUID | None = None
    is_active: bool | None = None


class AllocationResponse(ORMModel):
    id: uuid.UUID
    course_id: uuid.UUID
    semester_id: uuid.UUID
    section_id: uuid.UUID
    faculty_id: uuid.UUID
    is_active: bool


class TimetableEntryCreate(BaseModel):
    allocation_id: uuid.UUID
    classroom_id: uuid.UUID
    weekday: int = Field(ge=0, le=6)
    starts_at: time
    ends_at: time
    effective_from: date
    effective_until: date | None = None


class TimetableEntryUpdate(BaseModel):
    allocation_id: uuid.UUID | None = None
    classroom_id: uuid.UUID | None = None
    weekday: int | None = Field(default=None, ge=0, le=6)
    starts_at: time | None = None
    ends_at: time | None = None
    effective_from: date | None = None
    effective_until: date | None = None
    is_active: bool | None = None


class TimetableEntryResponse(ORMModel):
    id: uuid.UUID
    allocation_id: uuid.UUID
    classroom_id: uuid.UUID
    weekday: int
    starts_at: time
    ends_at: time
    effective_from: date
    effective_until: date | None
    is_active: bool


class LectureResponse(ORMModel):
    id: uuid.UUID
    allocation_id: uuid.UUID
    timetable_entry_id: uuid.UUID | None
    classroom_id: uuid.UUID
    starts_at: datetime
    ends_at: datetime
    status: str
    cancellation_reason: str | None


class LectureReschedule(BaseModel):
    starts_at: datetime
    ends_at: datetime
    classroom_id: uuid.UUID


class LectureCancellation(BaseModel):
    reason: str = Field(min_length=5, max_length=500)


class CreatedResponse(ORMModel):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
