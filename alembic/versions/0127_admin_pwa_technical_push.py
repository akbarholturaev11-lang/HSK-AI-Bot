"""Allow privacy-safe Mini App technical markers in opted-in push outbox."""
from alembic import op
import sqlalchemy as sa

revision = "0127_admin_pwa_technical_push"
down_revision = "0126_admin_pwa_command_audit"
branch_labels = None
depends_on = None

TABLE = "admin_pwa_push_outbox"
CONSTRAINT = "ck_admin_pwa_push_outbox_source"


def upgrade():
    op.drop_constraint(CONSTRAINT, TABLE, type_="check")
    op.create_check_constraint(CONSTRAINT, TABLE,
        "source IN ('bot', 'release', 'android', 'payment', 'technical')")


def downgrade():
    if op.get_bind().execute(sa.text(
            "SELECT EXISTS (SELECT 1 FROM admin_pwa_push_outbox "
            "WHERE source = 'technical')")).scalar_one():
        raise RuntimeError("Archive technical notification audit before downgrade")
    op.drop_constraint(CONSTRAINT, TABLE, type_="check")
    op.create_check_constraint(CONSTRAINT, TABLE,
        "source IN ('bot', 'release', 'android', 'payment')")
