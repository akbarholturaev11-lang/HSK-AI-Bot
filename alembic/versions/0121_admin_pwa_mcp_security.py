"""Privacy-minimal MCP audit and distributed quota counters."""
from alembic import op
import sqlalchemy as sa

revision = "0121_admin_pwa_mcp_security"
down_revision = "0120_admin_pwa_mcp_consent_csrf"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "admin_pwa_mcp_audit",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("admin_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_admin_pwa_mcp_audit_created_at", "admin_pwa_mcp_audit", ["created_at"])
    op.create_table(
        "admin_pwa_mcp_quotas",
        sa.Column("key", sa.String(80), primary_key=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("hits", sa.Integer(), nullable=False),
    )


def downgrade():
    # A rollback must not silently erase security evidence.
    if op.get_bind().execute(sa.text("SELECT count(*) FROM admin_pwa_mcp_audit")).scalar_one():
        raise RuntimeError("Archive MCP audit evidence before rolling back the security schema")
    op.drop_table("admin_pwa_mcp_quotas")
    op.drop_index("ix_admin_pwa_mcp_audit_created_at", table_name="admin_pwa_mcp_audit")
    op.drop_table("admin_pwa_mcp_audit")
