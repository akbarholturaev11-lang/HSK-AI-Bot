"""Add opt-in learner PWA push subscriptions and content-free outbox.

Revision ID: 0147_learner_pwa_push
Revises: 0146_pwa_feedback_owner
"""
from alembic import op
import sqlalchemy as sa


revision = "0147_learner_pwa_push"
down_revision = "0146_pwa_feedback_owner"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "learner_pwa_push_subscriptions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "device_id", sa.String(length=36),
            sa.ForeignKey("desktop_devices.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("endpoint_hash", sa.String(length=64), nullable=False),
        sa.Column("encrypted_payload", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("endpoint_hash", name="uq_learner_pwa_push_endpoint"),
        sa.UniqueConstraint("device_id", name="uq_learner_pwa_push_device"),
        sa.CheckConstraint("length(endpoint_hash) = 64", name="ck_learner_pwa_push_endpoint_hash"),
    )
    op.create_index(
        "ix_learner_pwa_push_revoked", "learner_pwa_push_subscriptions",
        ["revoked_at", "updated_at"],
    )
    op.create_table(
        "learner_pwa_push_outbox",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "subscription_id", sa.String(length=36),
            sa.ForeignKey("learner_pwa_push_subscriptions.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("event_key", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("language", sa.String(length=8), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_owner", sa.String(length=36), nullable=True),
        sa.Column("last_http_status", sa.Integer(), nullable=True),
        sa.UniqueConstraint(
            "subscription_id", "event_key", name="uq_learner_pwa_push_event_device",
        ),
        sa.CheckConstraint(
            "source IN ('account', 'course', 'payment')", name="ck_learner_pwa_push_source",
        ),
        sa.CheckConstraint(
            "state IN ('pending', 'leased', 'retry', 'accepted', 'dead', 'cancelled')",
            name="ck_learner_pwa_push_state",
        ),
        sa.CheckConstraint("attempts BETWEEN 0 AND 4", name="ck_learner_pwa_push_attempts"),
        sa.CheckConstraint("length(event_key) = 64", name="ck_learner_pwa_push_event_key"),
    )
    op.create_index(
        "ix_learner_pwa_push_due", "learner_pwa_push_outbox", ["state", "next_attempt_at"],
    )
    op.create_index(
        "ix_learner_pwa_push_outbox_subscription", "learner_pwa_push_outbox",
        ["subscription_id", "created_at"],
    )


def downgrade():
    bind = op.get_bind()
    for table in ("learner_pwa_push_outbox", "learner_pwa_push_subscriptions"):
        if bind.execute(sa.text(f"SELECT 1 FROM {table} LIMIT 1")).first():
            raise RuntimeError("Refusing downgrade with learner PWA push consent or delivery history")
    op.drop_index("ix_learner_pwa_push_outbox_subscription", table_name="learner_pwa_push_outbox")
    op.drop_index("ix_learner_pwa_push_due", table_name="learner_pwa_push_outbox")
    op.drop_table("learner_pwa_push_outbox")
    op.drop_index("ix_learner_pwa_push_revoked", table_name="learner_pwa_push_subscriptions")
    op.drop_table("learner_pwa_push_subscriptions")
