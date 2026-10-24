"""Dedicated first-party command audit, no external MCP permissions."""
from alembic import op
import sqlalchemy as sa

revision = "0126_admin_pwa_command_audit"
down_revision = "0125_admin_pwa_push_outbox"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("admin_pwa_command_audit",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("step_up_id", sa.String(36), unique=True, nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=False),
        sa.Column("target_user_id", sa.Integer()),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("target", sa.String(64), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_admin_pwa_command_audit_target_user_id", "admin_pwa_command_audit", ["target_user_id"])


def downgrade():
    if op.get_bind().execute(sa.text("SELECT EXISTS (SELECT 1 FROM admin_pwa_command_audit)")).scalar_one():
        raise RuntimeError("Archive command audit before destructive downgrade")
    op.drop_index("ix_admin_pwa_command_audit_target_user_id", table_name="admin_pwa_command_audit")
    op.drop_table("admin_pwa_command_audit")
