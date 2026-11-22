"""Smart study reminder message variant key (D33).

Additive only: nullable `smart_reminder_jobs.content_key` (for example
`comeback.v3`). It names the catalog variant chosen for that day's single
reminder so retries, the Android claim and the inbox reuse it. No backfill;
older rows keep NULL and older code ignores the column. Downgrade drops only
this column.
"""

from alembic import op
import sqlalchemy as sa

revision = "0159_smart_reminder_content_key"
down_revision = "0158_course_adaptive_lessons"
branch_labels = None
depends_on = None

JOBS = "smart_reminder_jobs"


def _has_column():
    # Isolated QA runners may replay from metadata that already has it.
    return "content_key" in {c["name"] for c in sa.inspect(op.get_bind()).get_columns(JOBS)}


def upgrade():
    if not _has_column():
        op.add_column(JOBS, sa.Column("content_key", sa.String(length=48), nullable=True))


def downgrade():
    if _has_column():
        op.drop_column(JOBS, "content_key")
