from datetime import date, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import require_roles
from app.models.academic import (
    AcademicYear,
    Classroom,
    Course,
    CourseAllocation,
    Department,
    Section,
    Semester,
)
from app.models.attendance import AttendanceSession, AttendanceSessionStatus
from app.models.timetable import Lecture, LectureStatus, TimetableEntry
from app.models.user import User, UserRole
from app.schemas.academic import (
    AcademicYearCreate,
    AcademicYearResponse,
    AcademicYearUpdate,
    AllocationCreate,
    AllocationResponse,
    AllocationUpdate,
    ClassroomCreate,
    ClassroomResponse,
    ClassroomUpdate,
    CourseCreate,
    CourseResponse,
    CourseUpdate,
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
    LectureCancellation,
    LectureReschedule,
    LectureResponse,
    SectionCreate,
    SectionResponse,
    SectionUpdate,
    SemesterCreate,
    SemesterResponse,
    SemesterUpdate,
    TimetableEntryCreate,
    TimetableEntryResponse,
    TimetableEntryUpdate,
)
from app.services.audit import record_audit
from app.services.timetable import (
    ScheduleConflict,
    cancel_lecture,
    generate_lectures,
    validate_timetable_entry,
)

router = APIRouter(prefix="/admin", tags=["academic administration"])
Admin = Depends(require_roles(UserRole.ADMIN.value))


def _commit(db: Session, user: User, obj: Any, action: str, resource: str) -> Any:
    db.add(obj)
    try:
        db.flush()
        record_audit(
            db,
            actor_id=user.id,
            action=action,
            resource_type=resource,
            resource_id=str(getattr(obj, "id", "")),
            after={"id": str(getattr(obj, "id", ""))},
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Conflicting or invalid academic record"
        ) from None
    db.refresh(obj)
    return obj


@router.get("/departments", response_model=list[DepartmentResponse])
def list_departments(_: User = Admin, db: Session = Depends(get_db)) -> list[Department]:
    return list(db.scalars(select(Department).order_by(Department.code)))


@router.post("/departments", response_model=DepartmentResponse, status_code=201)
def create_department(
    payload: DepartmentCreate, user: User = Admin, db: Session = Depends(get_db)
) -> Department:
    return _commit(db, user, Department(**payload.model_dump()), "CREATE", "department")


def _patch(
    db: Session, user: User, model: Any, record_id: UUID, payload: Any, resource: str
) -> Any:
    obj = db.get(model, record_id)
    if not obj:
        raise HTTPException(404, f"{resource.replace('_', ' ').title()} not found")
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(422, "At least one field must be provided")
    before = {key: getattr(obj, key) for key in changes}
    for key, value in changes.items():
        setattr(obj, key, value)
    if isinstance(obj, AcademicYear) and obj.ends_on <= obj.starts_on:
        raise HTTPException(422, "Academic year end must follow its start")
    if isinstance(obj, Semester):
        year = db.get(AcademicYear, obj.academic_year_id)
        if (
            obj.ends_on <= obj.starts_on
            or not year
            or obj.starts_on < year.starts_on
            or obj.ends_on > year.ends_on
        ):
            raise HTTPException(
                422, "Semester dates must be valid and fall within its academic year"
            )
    try:
        db.flush()
        record_audit(
            db,
            actor_id=user.id,
            action="UPDATE",
            resource_type=resource,
            resource_id=str(record_id),
            before={k: str(v) for k, v in before.items()},
            after={k: str(getattr(obj, k)) for k in changes},
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Conflicting or invalid academic record") from None
    db.refresh(obj)
    return obj


@router.patch("/departments/{record_id}", response_model=DepartmentResponse)
def patch_department(
    record_id: UUID, payload: DepartmentUpdate, user: User = Admin, db: Session = Depends(get_db)
) -> Department:
    return _patch(db, user, Department, record_id, payload, "department")


@router.get("/academic-years", response_model=list[AcademicYearResponse])
def list_academic_years(_: User = Admin, db: Session = Depends(get_db)) -> list[AcademicYear]:
    return list(db.scalars(select(AcademicYear).order_by(AcademicYear.starts_on.desc())))


@router.post("/academic-years", response_model=AcademicYearResponse, status_code=201)
def create_academic_year(
    payload: AcademicYearCreate, user: User = Admin, db: Session = Depends(get_db)
) -> AcademicYear:
    if payload.ends_on <= payload.starts_on:
        raise HTTPException(422, "Academic year end must follow its start")
    return _commit(db, user, AcademicYear(**payload.model_dump()), "CREATE", "academic_year")


@router.patch("/academic-years/{record_id}", response_model=AcademicYearResponse)
def patch_academic_year(
    record_id: UUID, payload: AcademicYearUpdate, user: User = Admin, db: Session = Depends(get_db)
) -> AcademicYear:
    return _patch(db, user, AcademicYear, record_id, payload, "academic_year")


@router.get("/semesters", response_model=list[SemesterResponse])
def list_semesters(_: User = Admin, db: Session = Depends(get_db)) -> list[Semester]:
    return list(db.scalars(select(Semester).order_by(Semester.number)))


@router.patch("/semesters/{record_id}", response_model=SemesterResponse)
def patch_semester(
    record_id: UUID, payload: SemesterUpdate, user: User = Admin, db: Session = Depends(get_db)
) -> Semester:
    return _patch(db, user, Semester, record_id, payload, "semester")


@router.post("/semesters", response_model=SemesterResponse, status_code=201)
def create_semester(
    payload: SemesterCreate, user: User = Admin, db: Session = Depends(get_db)
) -> Semester:
    if payload.ends_on <= payload.starts_on:
        raise HTTPException(422, "Semester end must follow its start")
    year = db.get(AcademicYear, payload.academic_year_id)
    if not year or not year.is_active:
        raise HTTPException(404, "Academic year not found")
    if payload.starts_on < year.starts_on or payload.ends_on > year.ends_on:
        raise HTTPException(422, "Semester dates must fall within the academic year")
    return _commit(db, user, Semester(**payload.model_dump()), "CREATE", "semester")


@router.get("/sections", response_model=list[SectionResponse])
def list_sections(_: User = Admin, db: Session = Depends(get_db)) -> list[Section]:
    return list(db.scalars(select(Section).order_by(Section.name)))


@router.patch("/sections/{record_id}", response_model=SectionResponse)
def patch_section(
    record_id: UUID, payload: SectionUpdate, user: User = Admin, db: Session = Depends(get_db)
) -> Section:
    return _patch(db, user, Section, record_id, payload, "section")


@router.post("/sections", response_model=SectionResponse, status_code=201)
def create_section(
    payload: SectionCreate, user: User = Admin, db: Session = Depends(get_db)
) -> Section:
    department = db.get(Department, payload.department_id)
    year = db.get(AcademicYear, payload.academic_year_id)
    if not department or not department.is_active or not year or not year.is_active:
        raise HTTPException(404, "Department or academic year not found")
    return _commit(db, user, Section(**payload.model_dump()), "CREATE", "section")


@router.get("/courses", response_model=list[CourseResponse])
def list_courses(_: User = Admin, db: Session = Depends(get_db)) -> list[Course]:
    return list(db.scalars(select(Course).order_by(Course.code)))


@router.post("/courses", response_model=CourseResponse, status_code=201)
def create_course(
    payload: CourseCreate, user: User = Admin, db: Session = Depends(get_db)
) -> Course:
    department = db.get(Department, payload.department_id)
    if not department or not department.is_active:
        raise HTTPException(404, "Department not found")
    return _commit(db, user, Course(**payload.model_dump()), "CREATE", "course")


@router.patch("/courses/{record_id}", response_model=CourseResponse)
def patch_course(
    record_id: UUID, payload: CourseUpdate, user: User = Admin, db: Session = Depends(get_db)
) -> Course:
    return _patch(db, user, Course, record_id, payload, "course")


@router.get("/classrooms", response_model=list[ClassroomResponse])
def list_classrooms(_: User = Admin, db: Session = Depends(get_db)) -> list[Classroom]:
    return list(db.scalars(select(Classroom).order_by(Classroom.code)))


@router.post("/classrooms", response_model=ClassroomResponse, status_code=201)
def create_classroom(
    payload: ClassroomCreate, user: User = Admin, db: Session = Depends(get_db)
) -> Classroom:
    return _commit(db, user, Classroom(**payload.model_dump()), "CREATE", "classroom")


@router.patch("/classrooms/{record_id}", response_model=ClassroomResponse)
def patch_classroom(
    record_id: UUID, payload: ClassroomUpdate, user: User = Admin, db: Session = Depends(get_db)
) -> Classroom:
    return _patch(db, user, Classroom, record_id, payload, "classroom")


@router.get("/allocations", response_model=list[AllocationResponse])
def list_allocations(_: User = Admin, db: Session = Depends(get_db)) -> list[CourseAllocation]:
    return list(db.scalars(select(CourseAllocation).order_by(CourseAllocation.created_at.desc())))


@router.patch("/allocations/{record_id}", response_model=AllocationResponse)
def patch_allocation(
    record_id: UUID, payload: AllocationUpdate, user: User = Admin, db: Session = Depends(get_db)
) -> CourseAllocation:
    allocation = db.get(CourseAllocation, record_id)
    if not allocation:
        raise HTTPException(404, "Allocation not found")
    if payload.faculty_id:
        faculty = db.get(User, payload.faculty_id)
        if not faculty or faculty.role != UserRole.FACULTY or not faculty.is_active:
            raise HTTPException(422, "Allocation faculty must be an active faculty account")
    return _patch(db, user, CourseAllocation, record_id, payload, "course_allocation")


@router.post("/allocations", response_model=AllocationResponse, status_code=201)
def create_allocation(
    payload: AllocationCreate, user: User = Admin, db: Session = Depends(get_db)
) -> CourseAllocation:
    from app.models.user import UserRole

    faculty = db.get(User, payload.faculty_id)
    if not faculty or faculty.role != UserRole.FACULTY or not faculty.is_active:
        raise HTTPException(422, "Allocation faculty must be an active faculty account")
    course = db.get(Course, payload.course_id)
    semester = db.get(Semester, payload.semester_id)
    section = db.get(Section, payload.section_id)
    if (
        not course
        or not course.is_active
        or not semester
        or not semester.is_active
        or not section
        or not section.is_active
    ):
        raise HTTPException(404, "Active course, semester, and section are required")
    if (
        course.department_id != section.department_id
        or semester.academic_year_id != section.academic_year_id
    ):
        raise HTTPException(422, "Course allocation academic relationships do not match")
    return _commit(
        db, user, CourseAllocation(**payload.model_dump()), "CREATE", "course_allocation"
    )


@router.get("/timetable", response_model=list[TimetableEntryResponse])
def list_timetable(_: User = Admin, db: Session = Depends(get_db)) -> list[TimetableEntry]:
    return list(
        db.scalars(
            select(TimetableEntry).order_by(TimetableEntry.weekday, TimetableEntry.starts_at)
        )
    )


@router.post("/timetable", response_model=TimetableEntryResponse, status_code=201)
def create_timetable_entry(
    payload: TimetableEntryCreate, user: User = Admin, db: Session = Depends(get_db)
) -> TimetableEntry:
    allocation = db.get(CourseAllocation, payload.allocation_id)
    classroom = db.get(Classroom, payload.classroom_id)
    if not allocation or not allocation.is_active or not classroom or not classroom.is_active:
        raise HTTPException(404, "Course allocation or classroom not found")
    entry = TimetableEntry(**payload.model_dump())
    try:
        validate_timetable_entry(db, entry)
    except ScheduleConflict as error:
        raise HTTPException(409, str(error)) from None
    except ValueError as error:
        raise HTTPException(422, str(error)) from None
    return _commit(db, user, entry, "CREATE", "timetable_entry")


@router.patch("/timetable/{entry_id}", response_model=TimetableEntryResponse)
def update_timetable_entry(
    entry_id: UUID,
    payload: TimetableEntryUpdate,
    user: User = Admin,
    db: Session = Depends(get_db),
) -> TimetableEntry:
    entry = db.get(TimetableEntry, entry_id)
    if not entry:
        raise HTTPException(404, "Timetable entry not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(entry, key, value)
    try:
        validate_timetable_entry(db, entry)
        db.flush()
        record_audit(
            db,
            actor_id=user.id,
            action="UPDATE",
            resource_type="timetable_entry",
            resource_id=str(entry.id),
            after={key: str(getattr(entry, key)) for key in payload.model_dump(exclude_unset=True)},
        )
        db.commit()
    except ScheduleConflict as error:
        db.rollback()
        raise HTTPException(409, str(error)) from None
    except ValueError as error:
        db.rollback()
        raise HTTPException(422, str(error)) from None
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Conflicting timetable data") from None
    db.refresh(entry)
    return entry


@router.post("/timetable/{entry_id}/generate", status_code=201)
def generate_entry_lectures(
    entry_id: UUID,
    through: date,
    user: User = Admin,
    db: Session = Depends(get_db),
) -> dict[str, int]:
    entry = db.get(TimetableEntry, entry_id)
    if not entry:
        raise HTTPException(404, "Timetable entry not found")
    try:
        count = generate_lectures(db, entry, through)
        record_audit(
            db,
            actor_id=user.id,
            action="GENERATE_LECTURES",
            resource_type="timetable_entry",
            resource_id=str(entry_id),
            after={"created_count": count, "through": through.isoformat()},
        )
        db.commit()
    except ValueError as error:
        db.rollback()
        raise HTTPException(422, str(error)) from None
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Lectures already exist for part of this schedule") from None
    return {"created_count": count}


@router.get("/lectures", response_model=list[LectureResponse])
def list_lectures(
    starts_after: datetime | None = None,
    starts_before: datetime | None = None,
    _: User = Admin,
    db: Session = Depends(get_db),
) -> list[Lecture]:
    statement = select(Lecture).order_by(Lecture.starts_at)
    if starts_after:
        statement = statement.where(Lecture.starts_at >= starts_after)
    if starts_before:
        statement = statement.where(Lecture.starts_at <= starts_before)
    return list(db.scalars(statement.limit(500)))


@router.post("/lectures/{lecture_id}/cancel", response_model=LectureResponse)
def cancel_scheduled_lecture(
    lecture_id: UUID,
    payload: LectureCancellation,
    admin: User = Admin,
    db: Session = Depends(get_db),
) -> Lecture:
    lecture = db.get(Lecture, lecture_id)
    if not lecture:
        raise HTTPException(404, "Lecture not found")
    if db.scalar(
        select(AttendanceSession.id).where(
            AttendanceSession.lecture_id == lecture.id,
            AttendanceSession.status == AttendanceSessionStatus.OPEN,
        )
    ):
        raise HTTPException(409, "A lecture with an open attendance session cannot be cancelled")
    try:
        cancel_lecture(db, lecture, payload.reason)
    except ValueError as error:
        raise HTTPException(409, str(error)) from None
    record_audit(
        db,
        actor_id=admin.id,
        action="CANCEL",
        resource_type="lecture",
        resource_id=str(lecture.id),
        after={"status": lecture.status.value},
        reason=payload.reason,
    )
    db.commit()
    db.refresh(lecture)
    return lecture


@router.patch("/lectures/{lecture_id}/reschedule", response_model=LectureResponse)
def reschedule_lecture(
    lecture_id: UUID,
    payload: LectureReschedule,
    admin: User = Admin,
    db: Session = Depends(get_db),
) -> Lecture:
    lecture = db.get(Lecture, lecture_id)
    if not lecture:
        raise HTTPException(404, "Lecture not found")
    if lecture.status != LectureStatus.SCHEDULED:
        raise HTTPException(409, "Only scheduled lectures can be rescheduled")
    if db.scalar(
        select(AttendanceSession.id).where(
            AttendanceSession.lecture_id == lecture.id,
            AttendanceSession.status == AttendanceSessionStatus.OPEN,
        )
    ):
        raise HTTPException(409, "A lecture with an open attendance session cannot be rescheduled")
    if payload.ends_at <= payload.starts_at:
        raise HTTPException(422, "Lecture end must follow its start")
    if payload.starts_at.tzinfo is None or payload.ends_at.tzinfo is None:
        raise HTTPException(422, "Rescheduled lecture times must include a timezone")
    classroom = db.get(Classroom, payload.classroom_id)
    if not classroom or not classroom.is_active:
        raise HTTPException(404, "Active classroom not found")
    allocation = db.get(CourseAllocation, lecture.allocation_id)
    if not allocation or not allocation.is_active:
        raise HTTPException(409, "The lecture course allocation is no longer active")
    conflicts = db.scalars(
        select(Lecture)
        .join(CourseAllocation, CourseAllocation.id == Lecture.allocation_id)
        .where(
            Lecture.id != lecture.id,
            Lecture.status == LectureStatus.SCHEDULED,
            Lecture.starts_at < payload.ends_at,
            Lecture.ends_at > payload.starts_at,
            or_(
                Lecture.classroom_id == payload.classroom_id,
                CourseAllocation.faculty_id == allocation.faculty_id,
            ),
        )
    ).first()
    if conflicts:
        raise HTTPException(409, "The classroom or faculty member has a conflicting lecture")
    before = {
        "starts_at": lecture.starts_at.isoformat(),
        "ends_at": lecture.ends_at.isoformat(),
        "classroom_id": str(lecture.classroom_id),
    }
    lecture.starts_at = payload.starts_at
    lecture.ends_at = payload.ends_at
    lecture.classroom_id = payload.classroom_id
    record_audit(
        db,
        actor_id=admin.id,
        action="RESCHEDULE",
        resource_type="lecture",
        resource_id=str(lecture.id),
        before=before,
        after={
            "starts_at": lecture.starts_at.isoformat(),
            "ends_at": lecture.ends_at.isoformat(),
            "classroom_id": str(lecture.classroom_id),
        },
    )
    db.commit()
    db.refresh(lecture)
    return lecture
