"""Durable, private Android report intake, independent of Telegram delivery."""
from alembic import op
import sqlalchemy as sa

revision = "0122_admin_pwa_native_reports"
down_revision = "0121_admin_pwa_mcp_security"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "admin_pwa_native_reports",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("deduplication_key", sa.String(64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("app_version", sa.String(40), nullable=False),
        sa.Column("screen", sa.String(80), nullable=False),
        sa.Column("attachment_bytes", sa.LargeBinary(), nullable=True),
        sa.Column("notification_state", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "deduplication_key", name="uq_admin_pwa_native_report_dedup"),
        sa.CheckConstraint("length(description) BETWEEN 5 AND 2000", name="ck_admin_pwa_native_report_text"),
        sa.CheckConstraint("length(attachment_bytes) <= 563200", name="ck_admin_pwa_native_report_attachment"),
        sa.CheckConstraint("notification_state IN ('pending', 'sent', 'failed')", name="ck_admin_pwa_native_report_delivery"),
    )
    op.create_index("ix_admin_pwa_native_report_user_attempt", "admin_pwa_native_reports", ["user_id", "last_attempt_at"])
    op.create_index("ix_admin_pwa_native_report_expires", "admin_pwa_native_reports", ["expires_at"])


def downgrade():
    if op.get_bind().execute(sa.text("SELECT count(*) FROM admin_pwa_native_reports")).scalar_one():
        raise RuntimeError("Archive private native reports before rolling back the inbox schema")
    op.drop_table("admin_pwa_native_reports")
