"""Sticky study routing ownership; no learner enrollment or provider calls."""
from alembic import op
import sqlalchemy as sa

revision = "0135_smart_reminder_routing"
down_revision = "0134_smart_reminder_mutations"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "smart_reminder_routing",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(16), nullable=False, server_default="held"),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("preference_revision", sa.Integer(), nullable=False),
        sa.Column("grant_epoch", sa.Integer(), nullable=False),
        sa.Column("telegram_binding", sa.String(64), nullable=False),
        sa.Column("inventory_sha256", sa.String(64)),
        sa.Column("held_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("verified_until", sa.DateTime(timezone=True)),
        sa.Column("evidence_sha256", sa.String(64)),
        sa.CheckConstraint("state IN ('held', 'telegram')", name=op.f("ck_smart_reminder_routing_state")),
        sa.CheckConstraint("generation >= 1 AND preference_revision >= 0 AND grant_epoch >= 0", name=op.f("ck_smart_reminder_routing_versions")),
        sa.CheckConstraint("length(telegram_binding) = 64", name=op.f("ck_smart_reminder_routing_transport_binding")),
        sa.CheckConstraint("inventory_sha256 IS NULL OR length(inventory_sha256) = 64", name=op.f("ck_smart_reminder_routing_inventory_binding")),
        sa.CheckConstraint("(verified_at IS NULL AND verified_until IS NULL AND evidence_sha256 IS NULL) OR (verified_at IS NOT NULL AND verified_until IS NOT NULL AND evidence_sha256 IS NOT NULL AND length(evidence_sha256) = 64 AND held_at <= verified_at AND verified_at < verified_until)", name=op.f("ck_smart_reminder_routing_review_window")),
        sa.CheckConstraint("state != 'telegram' OR (verified_at IS NOT NULL AND inventory_sha256 IS NOT NULL)", name=op.f("ck_smart_reminder_routing_review_required")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name=op.f("fk_smart_reminder_routing_user_id_users")),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_smart_reminder_routing")),
    )


def downgrade():
    if op.get_bind().execute(sa.text("SELECT 1 FROM smart_reminder_routing LIMIT 1")).first():
        raise RuntimeError("Retain routing ownership and review a safe rollback before destructive downgrade")
    op.drop_table("smart_reminder_routing")
