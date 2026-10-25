"""Bounded indexed lookup for immutable operator command evidence."""
from alembic import op
import sqlalchemy as sa

revision = "0128_admin_pwa_command_lookup"
down_revision = "0127_admin_pwa_technical_push"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("admin_pwa_payment_outbox", sa.Column("reconciled_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_pwa_payment_outbox_unreconciled", "admin_pwa_payment_outbox", ["status", "review_id"],
        postgresql_where=sa.text("reconciled_at IS NULL"), sqlite_where=sa.text("reconciled_at IS NULL"))
    op.create_index("ix_admin_pwa_command_action_target", "admin_pwa_command_audit", ["action", "target"])


def downgrade():
    if op.get_bind().execute(sa.text(
            "SELECT EXISTS (SELECT 1 FROM admin_pwa_payment_outbox WHERE reconciled_at IS NOT NULL)")).scalar_one():
        raise RuntimeError("Archive operator reconciliation metadata before destructive downgrade")
    op.drop_index("ix_admin_pwa_command_action_target", table_name="admin_pwa_command_audit")
    op.drop_index("ix_pwa_payment_outbox_unreconciled", table_name="admin_pwa_payment_outbox")
    op.drop_column("admin_pwa_payment_outbox", "reconciled_at")
