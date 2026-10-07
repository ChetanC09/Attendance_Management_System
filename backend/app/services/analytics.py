import uuid

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from app.models.academic import Course, CourseAllocation, StudentProfile
from app.models.attendance import Attendance, AttendanceStatus
from app.models.timetable import Lecture, LectureStatus
from app.models.user import User


def course_counts(
    db: Session, student_id: uuid.UUID, course_id: uuid.UUID | None = None
) -> list[dict]:
    statement = (
        select(
            Course.id.label("course_id"),
            Course.code.label("course_code"),
            Course.name.label("course_name"),
            func.count(Lecture.id).label("conducted"),
            func.sum(
                case(
                    (
                        Attendance.status.in_(
                            [
                                AttendanceStatus.PRESENT,
                                AttendanceStatus.LATE,
                                AttendanceStatus.EXCUSED,
                            ]
                        ),
                        1,
                    ),
                    else_=0,
                )
            ).label("attended"),
        )
        .select_from(StudentProfile)
        .join(CourseAllocation, CourseAllocation.section_id == StudentProfile.section_id)
        .join(Course, Course.id == CourseAllocation.course_id)
        .join(
            Lecture,
            and_(
                Lecture.allocation_id == CourseAllocation.id,
                Lecture.status == LectureStatus.CONDUCTED,
            ),
        )
        .outerjoin(
            Attendance,
            and_(Attendance.lecture_id == Lecture.id, Attendance.student_id == student_id),
        )
        .where(StudentProfile.user_id == student_id)
        .group_by(Course.id, Course.code, Course.name)
    )
    if course_id:
        statement = statement.where(Course.id == course_id)
    rows = db.execute(statement).all()
    return [
        {
            "course_id": row.course_id,
            "course_code": row.course_code,
            "course_name": row.course_name,
            "conducted_lectures": row.conducted,
            "attended_lectures": int(row.attended or 0),
            "attendance_percentage": round((int(row.attended or 0) / row.conducted * 100), 2)
            if row.conducted
            else 0.0,
        }
        for row in rows
    ]


def defaulter_list(db: Session, allocation_id: uuid.UUID, threshold: float) -> list[dict]:
    if not 0 <= threshold <= 100:
        raise ValueError("Threshold must be between 0 and 100")
    allocation = db.get(CourseAllocation, allocation_id)
    if not allocation:
        raise ValueError("Course allocation not found")
    conducted = (
        db.scalar(
            select(func.count(Lecture.id)).where(
                Lecture.allocation_id == allocation_id, Lecture.status == LectureStatus.CONDUCTED
            )
        )
        or 0
    )
    if not conducted:
        return []
    students = db.execute(
        select(User.id, User.institutional_id, User.full_name, func.count(Attendance.id))
        .select_from(StudentProfile)
        .join(User, User.id == StudentProfile.user_id)
        .outerjoin(
            Attendance,
            and_(
                Attendance.student_id == User.id,
                Attendance.lecture_id.in_(
                    select(Lecture.id).where(
                        Lecture.allocation_id == allocation_id,
                        Lecture.status == LectureStatus.CONDUCTED,
                    )
                ),
                Attendance.status.in_(
                    [
                        AttendanceStatus.PRESENT,
                        AttendanceStatus.LATE,
                        AttendanceStatus.EXCUSED,
                    ]
                ),
            ),
        )
        .where(StudentProfile.section_id == allocation.section_id)
        .group_by(User.id, User.institutional_id, User.full_name)
    ).all()
    result = []
    for user_id, institutional_id, full_name, attended in students:
        percentage = attended / conducted * 100
        if percentage < threshold:
            result.append(
                {
                    "student_id": user_id,
                    "institutional_id": institutional_id,
                    "full_name": full_name,
                    "attended_lectures": attended,
                    "conducted_lectures": conducted,
                    "attendance_percentage": round(percentage, 2),
                }
            )
    return result
