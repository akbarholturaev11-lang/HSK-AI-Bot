"""Allow privacy-safe Mini App technical markers in opted-in push outbox."""
from alembic import op
import sqlalchemy as sa

revision = "0127_admin_pwa_technical_push"
down_revision = "0126_admin_pwa_command_audit"
branch_labels = None
depends_on = None

TABLE = "admin_pwa_push_outbox"
CONSTRAINT = "ck_admin_pwa_push_outbox_source"
_INBOX_CHECKS = (("admin_pwa_inbox_triage", "ck_admin_pwa_inbox_triage_source"),
                 ("admin_pwa_inbox_triage_audit", "ck_admin_pwa_inbox_audit_source"))


def _has_messages():
    # Standalone QA deliberately contains only Admin PWA-owned tables; the
    # existing learner messages table belongs to the full application schema.
    return sa.inspect(op.get_bind()).has_table("messages")


def upgrade():
    if _has_messages():
        op.create_index("ix_messages_admin_pwa_technical_recent", "messages",
            ["created_at", "id"],
            postgresql_where=sa.text("role = 'assistant' AND content_type = 'app_error_context'"),
            sqlite_where=sa.text("role = 'assistant' AND content_type = 'app_error_context'"))
    op.drop_constraint(CONSTRAINT, TABLE, type_="check")
    op.create_check_constraint(CONSTRAINT, TABLE,
        "source IN ('bot', 'release', 'android', 'payment', 'technical')")
    for table, name in _INBOX_CHECKS:
        op.drop_constraint(name, table, type_="check")
        op.create_check_constraint(name, table,
            "source IN ('bot', 'release', 'android', 'payment', 'technical')")


def downgrade():
    if op.get_bind().execute(sa.text(
            "SELECT EXISTS (SELECT 1 FROM admin_pwa_push_outbox "
            "WHERE source = 'technical')")).scalar_one():
        raise RuntimeError("Archive technical notification audit before downgrade")
    for table, name in _INBOX_CHECKS:
        if op.get_bind().execute(sa.text(
            f"SELECT EXISTS (SELECT 1 FROM {table} WHERE source = 'technical')")).scalar_one():
            raise RuntimeError("Archive technical triage evidence before downgrade")
    for table, name in _INBOX_CHECKS:
        op.drop_constraint(name, table, type_="check")
        op.create_check_constraint(name, table,
            "source IN ('bot', 'release', 'android', 'payment')")
    op.drop_constraint(CONSTRAINT, TABLE, type_="check")
    op.create_check_constraint(CONSTRAINT, TABLE,
        "source IN ('bot', 'release', 'android', 'payment')")
    if _has_messages():
        op.drop_index("ix_messages_admin_pwa_technical_recent", table_name="messages")
