"""Store short-lived, single-use PKCE OAuth consent codes for MCP."""
from alembic import op
import sqlalchemy as sa

revision = "0119_admin_pwa_mcp_authorizations"
down_revision = "0118_admin_pwa_mcp_read_grants"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("admin_pwa_mcp_authorizations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("admin_pwa_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", sa.String(128), nullable=False),
        sa.Column("redirect_uri", sa.String(512), nullable=False),
        sa.Column("resource", sa.String(255), nullable=False),
        sa.Column("scope", sa.String(64), nullable=False),
        sa.Column("pkce_challenge", sa.String(43), nullable=False),
        sa.Column("client_state", sa.String(256), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_admin_pwa_mcp_authorizations_user_created",
                    "admin_pwa_mcp_authorizations", ["user_id", "created_at"])
    op.create_index("ix_admin_pwa_mcp_authorizations_expires_at",
                    "admin_pwa_mcp_authorizations", ["expires_at"])


def downgrade():
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT COUNT(*) FROM admin_pwa_mcp_authorizations")).scalar_one()
    if rows:
        raise RuntimeError("MCP OAuth authorizations must expire and be explicitly retired before rollback")
    op.drop_index("ix_admin_pwa_mcp_authorizations_expires_at", table_name="admin_pwa_mcp_authorizations")
    op.drop_index("ix_admin_pwa_mcp_authorizations_user_created", table_name="admin_pwa_mcp_authorizations")
    op.drop_table("admin_pwa_mcp_authorizations")
