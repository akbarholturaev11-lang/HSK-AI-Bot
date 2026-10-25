"""Inactive, revocable, scope-bound OAuth resource token grants for MCP."""
from alembic import op
import sqlalchemy as sa

revision = "0118_admin_pwa_mcp_read_grants"
down_revision = "0117_admin_pwa_payment_reviews"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "admin_pwa_mcp_access_grants",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("audience", sa.String(length=255), nullable=False),
        sa.Column("client_id", sa.String(length=128), nullable=False),
        sa.Column("consent_event_id", sa.String(length=36), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_admin_pwa_mcp_access_grants_user_id", "admin_pwa_mcp_access_grants", ["user_id"])
    op.create_index("ix_admin_pwa_mcp_access_grants_expires_at", "admin_pwa_mcp_access_grants", ["expires_at"])


def downgrade():
    # Never erase active consent/bearer revocation data silently during
    # migration rollback. The owner must explicitly retire all grants.
    connection = op.get_bind()
    active_count = connection.execute(sa.text(
        "SELECT COUNT(*) FROM admin_pwa_mcp_access_grants"
    )).scalar_one()
    if active_count:
        raise RuntimeError("MCP grant table contains records; revoke and retire grants before downgrade")
    op.drop_index("ix_admin_pwa_mcp_access_grants_expires_at", table_name="admin_pwa_mcp_access_grants")
    op.drop_index("ix_admin_pwa_mcp_access_grants_user_id", table_name="admin_pwa_mcp_access_grants")
    op.drop_table("admin_pwa_mcp_access_grants")
