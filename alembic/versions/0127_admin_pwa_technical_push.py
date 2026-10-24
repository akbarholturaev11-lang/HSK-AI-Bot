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
    op.create_index("ix_messages_admin_pwa_technical_recent", "messages",
        ["created_at", "id"],
        postgresql_where=sa.text("role = 'assistant' AND content_type = 'app_error_context'"),
        sqlite_where=sa.text("role = 'assistant' AND content_type = 'app_error_context'"))
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
    op.drop_index("ix_messages_admin_pwa_technical_recent", table_name="messages")
