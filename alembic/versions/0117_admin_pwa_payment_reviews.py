"""Atomic PWA payment review audit and post-commit delivery outbox."""
from alembic import op
import sqlalchemy as sa

revision = "0117_admin_pwa_payment_reviews"
down_revision = "0116_admin_pwa_step_ups"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "admin_pwa_payment_reviews",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("step_up_id", sa.String(36), nullable=False, unique=True),
        sa.Column("payment_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=False),
        sa.Column("target_user_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("decision IN ('approve', 'reject')", name="ck_pwa_review_decision"),
        sa.CheckConstraint("status = 'applied'", name="ck_pwa_review_status"),
    )
    op.create_table(
        "admin_pwa_payment_outbox",
        sa.Column("review_id", sa.String(36), sa.ForeignKey(
            "admin_pwa_payment_reviews.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("effects_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('pending', 'attempting', 'attempted', 'uncertain')",
                           name="ck_pwa_payment_outbox_status"),
    )
    op.create_index("ix_admin_pwa_payment_outbox_status", "admin_pwa_payment_outbox", ["status"])


def downgrade():
    # Financial audit must never disappear silently during a rollback.
    connection = op.get_bind()
    if connection.execute(sa.text("SELECT 1 FROM admin_pwa_payment_reviews LIMIT 1")).first():
        raise RuntimeError("admin_pwa_payment_audit_requires_retention_before_downgrade")
    op.drop_index("ix_admin_pwa_payment_outbox_status", table_name="admin_pwa_payment_outbox")
    op.drop_table("admin_pwa_payment_outbox")
    op.drop_table("admin_pwa_payment_reviews")
