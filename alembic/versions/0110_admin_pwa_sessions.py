"""Store revocable, hashed Admin PWA browser sessions (no token plaintext)."""

from alembic import op
import sqlalchemy as sa

revision = "0110_admin_pwa_sessions"
down_revision = "0109_public_site_traffic_daily"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "admin_pwa_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("auth_method", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_admin_pwa_sessions"),
        sa.UniqueConstraint("token_hash", name="uq_admin_pwa_sessions_token_hash"),
    )
    op.create_index("ix_admin_pwa_sessions_user_id", "admin_pwa_sessions", ["user_id"])
    op.create_index("ix_admin_pwa_sessions_expires_at", "admin_pwa_sessions", ["expires_at"])


def downgrade():
    op.drop_index("ix_admin_pwa_sessions_expires_at", table_name="admin_pwa_sessions")
    op.drop_index("ix_admin_pwa_sessions_user_id", table_name="admin_pwa_sessions")
    op.drop_table("admin_pwa_sessions")
