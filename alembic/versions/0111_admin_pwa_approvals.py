"""Add one-time, browser-bound Admin PWA approval request storage."""

from alembic import op
import sqlalchemy as sa

revision = "0111_admin_pwa_approvals"
down_revision = "0110_admin_pwa_sessions"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "admin_pwa_approvals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("browser_proof_hash", sa.String(length=64), nullable=False),
        sa.Column("google_subject_hash", sa.String(length=64), nullable=False),
        sa.Column("google_audience", sa.String(length=190), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("approved_user_id", sa.Integer(), nullable=True),
        sa.Column("approved_telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["approved_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_admin_pwa_approvals"),
        sa.UniqueConstraint("browser_proof_hash", name="uq_admin_pwa_approvals_browser_proof_hash"),
    )
    op.create_index("ix_admin_pwa_approvals_expires_at", "admin_pwa_approvals", ["expires_at"])


def downgrade():
    op.drop_index("ix_admin_pwa_approvals_expires_at", table_name="admin_pwa_approvals")
    op.drop_table("admin_pwa_approvals")
