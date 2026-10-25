"""One-use, exact-action WebAuthn step-up receipt and replay controls."""
from alembic import op
import sqlalchemy as sa

revision = "0116_admin_pwa_step_ups"
down_revision = "0115_admin_pwa_authentication_challenges"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "admin_pwa_step_ups",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("session_id", sa.String(length=36), sa.ForeignKey("admin_pwa_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("target", sa.String(length=128), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("challenge", sa.LargeBinary(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("credential_id", sa.LargeBinary(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_admin_pwa_step_ups_session_id", "admin_pwa_step_ups", ["session_id"])
    op.create_index("ix_admin_pwa_step_ups_created_at", "admin_pwa_step_ups", ["created_at"])
    op.create_index("ix_admin_pwa_step_ups_expires_at", "admin_pwa_step_ups", ["expires_at"])


def downgrade():
    op.drop_index("ix_admin_pwa_step_ups_expires_at", table_name="admin_pwa_step_ups")
    op.drop_index("ix_admin_pwa_step_ups_created_at", table_name="admin_pwa_step_ups")
    op.drop_index("ix_admin_pwa_step_ups_session_id", table_name="admin_pwa_step_ups")
    op.drop_table("admin_pwa_step_ups")
