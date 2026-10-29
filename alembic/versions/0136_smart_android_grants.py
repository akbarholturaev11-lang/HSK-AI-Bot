"""Retained Android study issuance and truthful client receipts; no dispatch."""
from alembic import op
import sqlalchemy as sa

revision = "0136_smart_android_grants"
down_revision = "0135_smart_reminder_routing"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "smart_reminder_android_grants",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.String(36), nullable=False),
        sa.Column("attempt_id", sa.String(36), nullable=False),
        sa.Column("device_id", sa.String(36)),
        sa.Column("session_id", sa.String(36)),
        sa.Column("local_epoch", sa.String(36), nullable=False),
        sa.Column("claim_request_id", sa.String(36), nullable=False),
        sa.Column("policy_version", sa.String(64), nullable=False),
        sa.Column("admission_sha256", sa.String(64), nullable=False),
        sa.Column("grant_epoch", sa.Integer(), nullable=False),
        sa.Column("preference_revision", sa.Integer(), nullable=False),
        sa.Column("capability_generation", sa.Integer(), nullable=False),
        sa.Column("cohort_generation", sa.Integer(), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("receipt_id", sa.String(36)),
        sa.Column("receipt_outcome", sa.String(32)),
        sa.Column("received_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_smart_reminder_android_grants")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name=op.f("fk_smart_reminder_android_grants_user_id_users")),
        sa.ForeignKeyConstraint(["job_id"], ["smart_reminder_jobs.id"], ondelete="CASCADE", name=op.f("fk_smart_reminder_android_grants_job_id_smart_reminder_jobs")),
        sa.ForeignKeyConstraint(["attempt_id"], ["smart_reminder_attempts.id"], ondelete="CASCADE", name=op.f("fk_smart_reminder_android_grants_attempt_id_smart_reminder_attempts")),
        sa.ForeignKeyConstraint(["device_id"], ["desktop_devices.id"], ondelete="SET NULL", name=op.f("fk_smart_reminder_android_grants_device_id_desktop_devices")),
        sa.ForeignKeyConstraint(["session_id"], ["desktop_sessions.id"], ondelete="SET NULL", name=op.f("fk_smart_reminder_android_grants_session_id_desktop_sessions")),
        sa.UniqueConstraint("job_id", name="uq_smart_android_grant_job"),
        sa.UniqueConstraint("attempt_id", name="uq_smart_android_grant_attempt"),
        sa.UniqueConstraint("user_id", "claim_request_id", name="uq_smart_android_grant_request"),
        sa.CheckConstraint("grant_epoch >= 0 AND preference_revision >= 0 AND capability_generation >= 1 AND cohort_generation >= 1", name=op.f("ck_smart_reminder_android_grants_versions")),
        sa.CheckConstraint("expires_at > issued_at", name=op.f("ck_smart_reminder_android_grants_expiry")),
        sa.CheckConstraint("length(admission_sha256) = 64", name=op.f("ck_smart_reminder_android_grants_admission_binding")),
        sa.CheckConstraint("receipt_outcome IS NULL OR receipt_outcome IN ('client_declined_before_post', 'client_posted_unverified', 'client_outcome_unknown')", name=op.f("ck_smart_reminder_android_grants_receipt_outcome")),
        sa.CheckConstraint("(receipt_id IS NULL AND receipt_outcome IS NULL AND received_at IS NULL) OR (receipt_id IS NOT NULL AND receipt_outcome IS NOT NULL AND received_at IS NOT NULL AND received_at >= issued_at)", name=op.f("ck_smart_reminder_android_grants_receipt_pair")),
    )
    op.create_index("ix_smart_android_grant_user", "smart_reminder_android_grants", ["user_id"])


def downgrade():
    if op.get_bind().execute(sa.text("SELECT 1 FROM smart_reminder_android_grants LIMIT 1")).first():
        raise RuntimeError("Retain Android issuance/outcome evidence before destructive downgrade")
    op.drop_index("ix_smart_android_grant_user", table_name="smart_reminder_android_grants")
    op.drop_table("smart_reminder_android_grants")
