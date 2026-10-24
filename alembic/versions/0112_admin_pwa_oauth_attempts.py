"""Persist one-time, browser-bound Admin PWA Google OAuth attempts."""

from alembic import op
import sqlalchemy as sa

revision = "0112_admin_pwa_oauth_attempts"
down_revision = "0111_admin_pwa_approvals"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "admin_pwa_oauth_attempts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("browser_proof_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_admin_pwa_oauth_attempts"),
        sa.UniqueConstraint(
            "browser_proof_hash", name="uq_admin_pwa_oauth_attempts_browser_proof_hash"
        ),
    )
    op.create_index(
        "ix_admin_pwa_oauth_attempts_expires_at",
        "admin_pwa_oauth_attempts", ["expires_at"],
    )


def downgrade():
    op.drop_index(
        "ix_admin_pwa_oauth_attempts_expires_at",
        table_name="admin_pwa_oauth_attempts",
    )
    op.drop_table("admin_pwa_oauth_attempts")
