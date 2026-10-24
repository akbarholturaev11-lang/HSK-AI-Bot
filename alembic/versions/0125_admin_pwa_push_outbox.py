"""Pending Apple Web Push notification outbox, default-off and content-free."""
from alembic import op
import sqlalchemy as sa

revision = "0125_admin_pwa_push_outbox"
down_revision = "0124_admin_pwa_push_subscriptions"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "admin_pwa_push_outbox",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("subscription_id", sa.String(36),
                  sa.ForeignKey("admin_pwa_push_subscriptions.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("event_key", sa.String(64), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("triage_revision", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("lease_owner", sa.String(36)),
        sa.Column("last_http_status", sa.Integer()),
        sa.UniqueConstraint("subscription_id", "event_key",
                            name="uq_admin_pwa_push_outbox_event_device"),
        sa.CheckConstraint("source IN ('bot', 'release', 'android')",
                           name="ck_admin_pwa_push_outbox_source"),
        sa.CheckConstraint("state IN ('pending', 'leased', 'retry', 'accepted', 'dead', 'cancelled')",
                           name="ck_admin_pwa_push_outbox_state"),
        sa.CheckConstraint("attempts BETWEEN 0 AND 4", name="ck_admin_pwa_push_outbox_attempts"),
        sa.CheckConstraint("triage_revision >= 1", name="ck_admin_pwa_push_outbox_revision"),
    )
    op.create_index("ix_admin_pwa_push_outbox_due", "admin_pwa_push_outbox",
                    ["state", "next_attempt_at"])
    op.create_index("ix_admin_pwa_push_outbox_subscription", "admin_pwa_push_outbox",
                    ["subscription_id", "created_at"])


def downgrade():
    if op.get_bind().execute(sa.text("SELECT count(*) FROM admin_pwa_push_outbox")).scalar_one():
        raise RuntimeError("Archive push delivery evidence before destructive downgrade")
    op.drop_index("ix_admin_pwa_push_outbox_subscription",
                  table_name="admin_pwa_push_outbox")
    op.drop_index("ix_admin_pwa_push_outbox_due",
                  table_name="admin_pwa_push_outbox")
    op.drop_table("admin_pwa_push_outbox")
