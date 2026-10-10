"""Add scoped faculty course announcements."""

from alembic import op

revision = "0003_course_announcements"
down_revision = "0002_academic_attendance_domains"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE announcements (
            id UUID PRIMARY KEY,
            faculty_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            allocation_id UUID NOT NULL REFERENCES course_allocations(id) ON DELETE CASCADE,
            title VARCHAR(160) NOT NULL,
            body TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )"""
    )
    op.execute("CREATE INDEX ix_announcements_faculty_id ON announcements (faculty_id)")
    op.execute("CREATE INDEX ix_announcements_allocation_id ON announcements (allocation_id)")


def downgrade() -> None:
    op.execute("DROP TABLE announcements")
