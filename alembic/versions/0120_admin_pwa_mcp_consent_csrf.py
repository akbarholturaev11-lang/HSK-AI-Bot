"""CSRF-binding for browser-visible MCP OAuth consent decisions."""
from alembic import op
import sqlalchemy as sa

revision = "0120_admin_pwa_mcp_consent_csrf"
down_revision = "0119_admin_pwa_mcp_authorizations"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("admin_pwa_mcp_authorizations",
                  sa.Column("consent_csrf_hash", sa.String(64), nullable=True))


def downgrade():
    count = op.get_bind().execute(sa.text(
        "SELECT count(*) FROM admin_pwa_mcp_authorizations"
    )).scalar_one()
    if count:
        raise RuntimeError("Retire all MCP OAuth authorization records before rolling back consent CSRF schema")
    op.drop_column("admin_pwa_mcp_authorizations", "consent_csrf_hash")
