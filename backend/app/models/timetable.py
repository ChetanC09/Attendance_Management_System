import enum
import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class LectureStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    CONDUCTED = "CONDUCTED"
    CANCELLED = "CANCELLED"
    RESCHEDULED = "RESCHEDULED"


class TimetableEntry(TimestampMixin, Base):
    __tablename__ = "timetable_entries"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="ck_timetable_time_range"),
        CheckConstraint("weekday >= 0 AND weekday <= 6", name="ck_timetable_weekday"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    allocation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("course_allocations.id", ondelete="RESTRICT")
    )
    classroom_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("classrooms.id", ondelete="RESTRICT")
    )
    weekday: Mapped[int] = mapped_column(Integer)
    starts_at: Mapped[time]
    ends_at: Mapped[time]
    effective_from: Mapped[date] = mapped_column(Date)
    effective_until: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class Lecture(TimestampMixin, Base):
    __tablename__ = "lectures"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="ck_lecture_time_range"),
        UniqueConstraint("allocation_id", "starts_at", name="uq_lecture_allocation_start"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    allocation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("course_allocations.id", ondelete="RESTRICT"), index=True
    )
    timetable_entry_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("timetable_entries.id"))
    classroom_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("classrooms.id", ondelete="RESTRICT")
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[LectureStatus] = mapped_column(
        Enum(LectureStatus, name="lecture_status"), default=LectureStatus.SCHEDULED
    )
    cancellation_reason: Mapped[str | None]
