"""Add the academic, attendance, request, notification and audit schema."""

from alembic import op

revision = "0002_academic_attendance_domains"
down_revision = "0001_identity_academic_base"
branch_labels = None
depends_on = None

# Frozen PostgreSQL DDL. Historical revisions must not depend on the current ORM models.
UPGRADE_SQL = (
    """CREATE EXTENSION IF NOT EXISTS vector""",
    """ALTER TABLE users ADD COLUMN phone_number VARCHAR(20)""",
    """CREATE TYPE attendance_session_status AS ENUM ('OPEN', 'CLOSED')""",
    """CREATE TYPE attendance_status AS ENUM ('PRESENT', 'LATE', 'ABSENT', 'EXCUSED')""",
    """CREATE TYPE attendance_source AS ENUM ('MANUAL', 'VISION', 'REGULARIZATION')""",
    """CREATE TYPE request_type AS ENUM ('LEAVE', 'REGULARIZATION')""",
    """CREATE TYPE request_status AS ENUM ('PENDING', 'APPROVED', 'REJECTED')""",
    """CREATE TYPE notification_channel AS ENUM ('IN_APP', 'EMAIL', 'SMS')""",
    """CREATE TYPE notification_status AS ENUM ('PENDING', 'SENT', 'FAILED')""",
    """CREATE TYPE lecture_status AS ENUM ('SCHEDULED', 'CONDUCTED', 'CANCELLED', 'RESCHEDULED')""",
    """CREATE TABLE academic_years (
    id UUID NOT NULL, 
    name VARCHAR(32) NOT NULL, 
    starts_on DATE NOT NULL, 
    ends_on DATE NOT NULL, 
    is_active BOOLEAN DEFAULT 'true' NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_academic_year_dates CHECK (ends_on > starts_on), 
    UNIQUE (name)
)""",
    """CREATE TABLE courses (
    id UUID NOT NULL, 
    department_id UUID NOT NULL, 
    code VARCHAR(32) NOT NULL, 
    name VARCHAR(160) NOT NULL, 
    credits INTEGER DEFAULT '0' NOT NULL, 
    is_active BOOLEAN DEFAULT 'true' NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_course_department_code UNIQUE (department_id, code), 
    FOREIGN KEY(department_id) REFERENCES departments (id) ON DELETE RESTRICT
)""",
    """CREATE TABLE classrooms (
    id UUID NOT NULL, 
    code VARCHAR(32) NOT NULL, 
    name VARCHAR(128) NOT NULL, 
    capacity INTEGER, 
    is_active BOOLEAN DEFAULT 'true' NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id)
)""",
    """CREATE UNIQUE INDEX ix_classrooms_code ON classrooms (code)""",
    """CREATE TABLE face_profiles (
    id UUID NOT NULL, 
    student_id UUID NOT NULL, 
    consented_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    revoked_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    UNIQUE (student_id), 
    FOREIGN KEY(student_id) REFERENCES users (id) ON DELETE CASCADE
)""",
    """CREATE TABLE notifications (
    id UUID NOT NULL, 
    user_id UUID NOT NULL, 
    title VARCHAR(160) NOT NULL, 
    message TEXT NOT NULL, 
    channel notification_channel NOT NULL, 
    status notification_status NOT NULL, 
    payload JSON, 
    attempts INTEGER DEFAULT '0' NOT NULL, 
    read_at TIMESTAMP WITH TIME ZONE, 
    sent_at TIMESTAMP WITH TIME ZONE, 
    next_attempt_at TIMESTAMP WITH TIME ZONE, 
    last_error VARCHAR(500), 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)""",
    """CREATE INDEX ix_notifications_user_id ON notifications (user_id)""",
    """CREATE INDEX ix_notifications_next_attempt_at ON notifications (next_attempt_at)""",
    """CREATE TABLE notification_preferences (
    id UUID NOT NULL, 
    user_id UUID NOT NULL, 
    channel notification_channel NOT NULL, 
    enabled BOOLEAN DEFAULT 'true' NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_notification_preference_user_channel UNIQUE (user_id, channel), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)""",
    """CREATE TABLE audit_logs (
    id UUID NOT NULL, 
    actor_id UUID, 
    action VARCHAR(128) NOT NULL, 
    resource_type VARCHAR(128) NOT NULL, 
    resource_id VARCHAR(64), 
    before_state JSON, 
    after_state JSON, 
    reason VARCHAR(500), 
    occurred_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(actor_id) REFERENCES users (id) ON DELETE SET NULL
)""",
    """CREATE INDEX ix_audit_logs_actor_id ON audit_logs (actor_id)""",
    """CREATE INDEX ix_audit_logs_occurred_at ON audit_logs (occurred_at)""",
    """CREATE INDEX ix_audit_logs_action ON audit_logs (action)""",
    """CREATE TABLE system_settings (
    key VARCHAR(128) NOT NULL, 
    value JSON NOT NULL, 
    updated_by UUID, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (key), 
    FOREIGN KEY(updated_by) REFERENCES users (id) ON DELETE SET NULL
)""",
    """CREATE TABLE password_reset_tokens (
    id UUID NOT NULL, 
    user_id UUID NOT NULL, 
    token_digest VARCHAR(64) NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    used_at TIMESTAMP WITH TIME ZONE, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    UNIQUE (token_digest)
)""",
    """CREATE INDEX ix_password_reset_tokens_user_id ON password_reset_tokens (user_id)""",
    """CREATE TABLE semesters (
    id UUID NOT NULL, 
    academic_year_id UUID NOT NULL, 
    number INTEGER NOT NULL, 
    starts_on DATE NOT NULL, 
    ends_on DATE NOT NULL, 
    is_active BOOLEAN DEFAULT 'true' NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_semester_year_number UNIQUE (academic_year_id, number), 
    FOREIGN KEY(academic_year_id) REFERENCES academic_years (id) ON DELETE RESTRICT
)""",
    """CREATE TABLE sections (
    id UUID NOT NULL, 
    department_id UUID NOT NULL, 
    academic_year_id UUID NOT NULL, 
    name VARCHAR(64) NOT NULL, 
    is_active BOOLEAN DEFAULT 'true' NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_section_context_name UNIQUE (department_id, academic_year_id, name), 
    FOREIGN KEY(department_id) REFERENCES departments (id) ON DELETE RESTRICT, 
    FOREIGN KEY(academic_year_id) REFERENCES academic_years (id) ON DELETE RESTRICT
)""",
    """CREATE TABLE face_embeddings (
    id UUID NOT NULL, 
    profile_id UUID NOT NULL, 
    embedding VECTOR(512) NOT NULL, 
    model_version VARCHAR(64) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(profile_id) REFERENCES face_profiles (id) ON DELETE CASCADE
)""",
    """CREATE INDEX ix_face_embeddings_profile_id ON face_embeddings (profile_id)""",
    """CREATE TABLE course_allocations (
    id UUID NOT NULL, 
    course_id UUID NOT NULL, 
    semester_id UUID NOT NULL, 
    section_id UUID NOT NULL, 
    faculty_id UUID NOT NULL, 
    is_active BOOLEAN DEFAULT 'true' NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_course_allocation_scope UNIQUE (course_id, semester_id, section_id), 
    FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE RESTRICT, 
    FOREIGN KEY(semester_id) REFERENCES semesters (id) ON DELETE RESTRICT, 
    FOREIGN KEY(section_id) REFERENCES sections (id) ON DELETE RESTRICT, 
    FOREIGN KEY(faculty_id) REFERENCES users (id) ON DELETE RESTRICT
)""",
    """CREATE TABLE timetable_entries (
    id UUID NOT NULL, 
    allocation_id UUID NOT NULL, 
    classroom_id UUID NOT NULL, 
    weekday INTEGER NOT NULL, 
    starts_at TIME WITHOUT TIME ZONE NOT NULL, 
    ends_at TIME WITHOUT TIME ZONE NOT NULL, 
    effective_from DATE NOT NULL, 
    effective_until DATE, 
    is_active BOOLEAN DEFAULT 'true' NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_timetable_time_range CHECK (ends_at > starts_at), 
    CONSTRAINT ck_timetable_weekday CHECK (weekday >= 0 AND weekday <= 6), 
    FOREIGN KEY(allocation_id) REFERENCES course_allocations (id) ON DELETE RESTRICT, 
    FOREIGN KEY(classroom_id) REFERENCES classrooms (id) ON DELETE RESTRICT
)""",
    """CREATE TABLE lectures (
    id UUID NOT NULL, 
    allocation_id UUID NOT NULL, 
    timetable_entry_id UUID, 
    classroom_id UUID NOT NULL, 
    starts_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    ends_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    status lecture_status NOT NULL, 
    cancellation_reason VARCHAR, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_lecture_time_range CHECK (ends_at > starts_at), 
    CONSTRAINT uq_lecture_allocation_start UNIQUE (allocation_id, starts_at), 
    FOREIGN KEY(allocation_id) REFERENCES course_allocations (id) ON DELETE RESTRICT, 
    FOREIGN KEY(timetable_entry_id) REFERENCES timetable_entries (id), 
    FOREIGN KEY(classroom_id) REFERENCES classrooms (id) ON DELETE RESTRICT
)""",
    """CREATE INDEX ix_lectures_starts_at ON lectures (starts_at)""",
    """CREATE INDEX ix_lectures_allocation_id ON lectures (allocation_id)""",
    """CREATE TABLE attendance_sessions (
    id UUID NOT NULL, 
    lecture_id UUID NOT NULL, 
    opened_by UUID NOT NULL, 
    status attendance_session_status NOT NULL, 
    started_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    closed_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    FOREIGN KEY(lecture_id) REFERENCES lectures (id) ON DELETE RESTRICT, 
    FOREIGN KEY(opened_by) REFERENCES users (id) ON DELETE RESTRICT
)""",
    """CREATE UNIQUE INDEX uq_attendance_sessions_one_open_per_lecture
ON attendance_sessions (lecture_id) WHERE status = 'OPEN'""",
    """CREATE INDEX ix_attendance_sessions_lecture_id ON attendance_sessions (lecture_id)""",
    """CREATE TABLE leave_requests (
    id UUID NOT NULL, 
    student_id UUID NOT NULL, 
    lecture_id UUID, 
    request_type request_type NOT NULL, 
    status request_status NOT NULL, 
    reason TEXT NOT NULL, 
    reviewed_by UUID, 
    review_reason TEXT, 
    reviewed_at TIMESTAMP WITH TIME ZONE, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(student_id) REFERENCES users (id) ON DELETE RESTRICT, 
    FOREIGN KEY(lecture_id) REFERENCES lectures (id) ON DELETE RESTRICT, 
    FOREIGN KEY(reviewed_by) REFERENCES users (id) ON DELETE RESTRICT
)""",
    """CREATE INDEX ix_leave_requests_status ON leave_requests (status)""",
    """CREATE INDEX ix_leave_requests_student_id ON leave_requests (student_id)""",
    """CREATE TABLE attendance (
    id UUID NOT NULL, 
    student_id UUID NOT NULL, 
    lecture_id UUID NOT NULL, 
    session_id UUID, 
    status attendance_status NOT NULL, 
    source attendance_source NOT NULL, 
    marked_by UUID NOT NULL, 
    marked_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    reason VARCHAR(500), 
    recognition_metadata JSON, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_attendance_student_lecture UNIQUE (student_id, lecture_id), 
    FOREIGN KEY(student_id) REFERENCES users (id) ON DELETE RESTRICT, 
    FOREIGN KEY(lecture_id) REFERENCES lectures (id) ON DELETE RESTRICT, 
    FOREIGN KEY(session_id) REFERENCES attendance_sessions (id) ON DELETE SET NULL, 
    FOREIGN KEY(marked_by) REFERENCES users (id) ON DELETE RESTRICT
)""",
    """CREATE INDEX ix_attendance_lecture_id ON attendance (lecture_id)""",
    """CREATE INDEX ix_attendance_student_id ON attendance (student_id)""",
    """CREATE TABLE supporting_documents (
    id UUID NOT NULL, 
    request_id UUID NOT NULL, 
    storage_key VARCHAR(512) NOT NULL, 
    original_filename VARCHAR(255) NOT NULL, 
    content_type VARCHAR(128) NOT NULL, 
    size_bytes INTEGER NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(request_id) REFERENCES leave_requests (id) ON DELETE CASCADE, 
    UNIQUE (storage_key)
)""",
    """CREATE INDEX ix_supporting_documents_request_id ON supporting_documents (request_id)""",
    """ALTER TABLE student_profiles ADD COLUMN section_id UUID""",
    """ALTER TABLE student_profiles ADD CONSTRAINT fk_student_profiles_section_id_sections
FOREIGN KEY(section_id) REFERENCES sections (id)""",
)

NEW_TABLES_REVERSED = (
    "password_reset_tokens",
    "system_settings",
    "audit_logs",
    "notification_preferences",
    "notifications",
    "supporting_documents",
    "leave_requests",
    "face_embeddings",
    "face_profiles",
    "attendance",
    "attendance_sessions",
    "lectures",
    "timetable_entries",
    "classrooms",
    "course_allocations",
    "courses",
    "sections",
    "semesters",
    "academic_years",
)

ENUM_TYPES_REVERSED = (
    "notification_status",
    "notification_channel",
    "request_status",
    "request_type",
    "attendance_source",
    "attendance_status",
    "attendance_session_status",
    "lecture_status",
)


def upgrade() -> None:
    for statement in UPGRADE_SQL:
        op.execute(statement)


def downgrade() -> None:
    op.execute(
        "ALTER TABLE student_profiles DROP CONSTRAINT fk_student_profiles_section_id_sections"
    )
    op.execute("ALTER TABLE student_profiles DROP COLUMN section_id")
    op.execute("ALTER TABLE users DROP COLUMN phone_number")
    for table in NEW_TABLES_REVERSED:
        op.execute(f"DROP TABLE {table}")
    for enum_type in ENUM_TYPES_REVERSED:
        op.execute(f"DROP TYPE {enum_type}")
    op.execute("DROP EXTENSION vector")
