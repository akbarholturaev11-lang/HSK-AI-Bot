"""Minimal authenticated Smart preference retry receipts, no learner backfill."""
from alembic import op
import sqlalchemy as sa

revision = "0134_smart_reminder_mutations"
down_revision = "0133_smart_reminder_storage"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "smart_reminder_mutations",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column("actor_key", sa.String(64), nullable=False),
        sa.Column("body_sha256", sa.String(64), nullable=False),
        sa.Column("applied_revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("applied_revision >= 1", name=op.f("ck_smart_reminder_mutations_revision")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE",
                                name=op.f("fk_smart_reminder_mutations_user_id_users")),
        sa.PrimaryKeyConstraint("user_id", "request_id", name=op.f("pk_smart_reminder_mutations")),
    )


def downgrade():
    if op.get_bind().execute(sa.text("SELECT 1 FROM smart_reminder_mutations LIMIT 1")).first():
        raise RuntimeError("Archive Smart mutation receipts before destructive downgrade")
    op.drop_table("smart_reminder_mutations")
