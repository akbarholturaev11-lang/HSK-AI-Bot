"""Durable anonymous Smart Reminder rollout control and routing quiesce time."""
from alembic import op
import sqlalchemy as sa

revision = "0150_smart_reminder_rollout"
down_revision = "0149_smart_pwa_analysis_channel"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "smart_reminder_rollout",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("generation", sa.Integer(), server_default="0", nullable=False),
        sa.Column("stage", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=16), server_default="waiting", nullable=False),
        sa.Column("stage_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=32), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("id = 1", name=op.f("ck_smart_reminder_rollout_singleton")),
        sa.CheckConstraint("generation >= 0 AND stage BETWEEN 0 AND 4", name=op.f("ck_smart_reminder_rollout_versions")),
        sa.CheckConstraint("status IN ('waiting', 'active', 'paused', 'complete')", name=op.f("ck_smart_reminder_rollout_status")),
        sa.CheckConstraint(
            "error_code IS NULL OR error_code IN ('runtime_exception', 'tick_timeout', "
            "'provider_unknown', 'provider_failure', 'native_unknown', 'monitor_stale')",
            name=op.f("ck_smart_reminder_rollout_error_code"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_smart_reminder_rollout")),
    )
    op.execute(sa.text(
        "INSERT INTO smart_reminder_rollout (id, generation, stage, status) "
        "VALUES (1, 0, 0, 'waiting')"
    ))
    op.add_column("smart_reminder_routing",
                  sa.Column("quiesced_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    bind = op.get_bind()
    row = bind.execute(sa.text(
        "SELECT generation, stage, status, error_at FROM smart_reminder_rollout WHERE id = 1"
    )).mappings().one_or_none()
    if row is not None and (row["generation"] != 0 or row["stage"] != 0 or
                            row["status"] != "waiting" or row["error_at"] is not None):
        raise RuntimeError("Refusing to remove an active or observed Smart rollout state")
    if bind.execute(sa.text(
            "SELECT 1 FROM smart_reminder_routing WHERE quiesced_at IS NOT NULL LIMIT 1")).first():
        raise RuntimeError("Refusing to remove recorded Smart routing quiesce evidence")
    op.drop_column("smart_reminder_routing", "quiesced_at")
    op.drop_table("smart_reminder_rollout")
