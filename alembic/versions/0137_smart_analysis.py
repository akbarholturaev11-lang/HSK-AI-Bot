"""Minimal disposable Smart delivery analysis; no delivery authority."""
from alembic import op
import sqlalchemy as sa

revision = "0137_smart_analysis"
down_revision = "0136_smart_android_grants"
branch_labels = None
depends_on = None

STAGES = "stage IN ('reserved', 'in_flight', 'provider_accepted', 'client_posted_unverified', 'confirmed_not_displayed', 'outcome_unknown', 'cancelled', 'expired', 'definite_failure')"


def upgrade():
    op.create_table("smart_reminder_analysis_events",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("event_key", sa.String(64), nullable=False),
        sa.Column("job_id", sa.String(36), nullable=False),
        sa.Column("stage", sa.String(32), nullable=False),
        sa.Column("channel", sa.String(16), nullable=False),
        sa.Column("reason_code", sa.String(64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id", "event_key", name=op.f("pk_smart_reminder_analysis_events")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name=op.f("fk_smart_reminder_analysis_events_user_id_users")),
        sa.ForeignKeyConstraint(["job_id"], ["smart_reminder_jobs.id"], ondelete="CASCADE", name=op.f("fk_smart_reminder_analysis_events_job_id_smart_reminder_jobs")),
        sa.CheckConstraint(STAGES, name=op.f("ck_smart_reminder_analysis_events_stage")),
        sa.CheckConstraint("channel IN ('none', 'telegram', 'android')", name=op.f("ck_smart_reminder_analysis_events_channel")),
        sa.CheckConstraint("length(event_key) = 64", name=op.f("ck_smart_reminder_analysis_events_event_key")),
        sa.CheckConstraint("expires_at > occurred_at", name=op.f("ck_smart_reminder_analysis_events_expiry")))
    op.create_index("ix_smart_analysis_expiry", "smart_reminder_analysis_events", ["expires_at", "user_id", "event_key"])
    op.create_index("ix_smart_analysis_job", "smart_reminder_analysis_events", ["job_id"])
    op.create_table("smart_reminder_analysis_monthly",
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("stage", sa.String(32), nullable=False),
        sa.Column("channel", sa.String(16), nullable=False),
        sa.Column("fact_count", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("month", "stage", "channel", name=op.f("pk_smart_reminder_analysis_monthly")),
        sa.CheckConstraint(STAGES, name=op.f("ck_smart_reminder_analysis_monthly_stage")),
        sa.CheckConstraint("channel IN ('none', 'telegram', 'android')", name=op.f("ck_smart_reminder_analysis_monthly_channel")),
        sa.CheckConstraint("fact_count >= 0", name=op.f("ck_smart_reminder_analysis_monthly_fact_count")))


def downgrade():
    for table in ("smart_reminder_analysis_events", "smart_reminder_analysis_monthly"):
        if op.get_bind().execute(sa.text(f"SELECT 1 FROM {table} LIMIT 1")).first():
            raise RuntimeError("Refusing populated Smart analysis downgrade; preserve retained evidence")
    op.drop_table("smart_reminder_analysis_monthly")
    op.drop_index("ix_smart_analysis_job", table_name="smart_reminder_analysis_events")
    op.drop_index("ix_smart_analysis_expiry", table_name="smart_reminder_analysis_events")
    op.drop_table("smart_reminder_analysis_events")
