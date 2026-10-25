"""Persist short-lived, single-approval Admin PWA passkey enrollment grants."""

from alembic import op
import sqlalchemy as sa

revision = "0113_admin_pwa_enrollment_grants"
down_revision = "0112_admin_pwa_oauth_attempts"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "admin_pwa_enrollment_grants",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("approval_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("browser_proof_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["approval_id"], ["admin_pwa_approvals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_admin_pwa_enrollment_grants"),
        sa.UniqueConstraint("approval_id", name="uq_admin_pwa_enrollment_grants_approval_id"),
        sa.UniqueConstraint("token_hash", name="uq_admin_pwa_enrollment_grants_token_hash"),
    )
    op.create_index(
        "ix_admin_pwa_enrollment_grants_expires_at",
        "admin_pwa_enrollment_grants", ["expires_at"],
    )
    op.create_index(
        "ix_admin_pwa_enrollment_grants_user_id",
        "admin_pwa_enrollment_grants", ["user_id"],
    )


def downgrade():
    op.drop_index(
        "ix_admin_pwa_enrollment_grants_user_id",
        table_name="admin_pwa_enrollment_grants",
    )
    op.drop_index(
        "ix_admin_pwa_enrollment_grants_expires_at",
        table_name="admin_pwa_enrollment_grants",
    )
    op.drop_table("admin_pwa_enrollment_grants")
