"""Canonical feedback ownership for linked Telegram and browser-only learners.

Historical feedback rows retain their genuine Telegram transport; only matching
existing users are backfilled. Unlinked legacy Telegram rows remain nullable
rather than fabricating a users.id. Both old Telegram and canonical uniqueness
are kept, and a downgrade refuses to discard provider-only feedback.
"""
from alembic import op
import sqlalchemy as sa


revision = "0146_pwa_feedback_canonical_owner"
down_revision = "0145_smart_baseline_outcomes"
branch_labels = None
depends_on = None

RELEASE_TABLES = ("release_feedback_deliveries", "release_feedback_responses")


def upgrade():
    with op.batch_alter_table("bot_feedbacks") as batch:
        batch.alter_column("telegram_id", existing_type=sa.BigInteger(), nullable=True)

    for table in RELEASE_TABLES:
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
            batch.alter_column("user_telegram_id", existing_type=sa.BigInteger(), nullable=True)

        op.execute(sa.text(
            f"UPDATE {table} SET user_id = "
            f"(SELECT users.id FROM users WHERE users.telegram_id = "
            f"{table}.user_telegram_id) "
            f"WHERE user_id IS NULL AND user_telegram_id IS NOT NULL"
        ))
        with op.batch_alter_table(table) as batch:
            batch.create_foreign_key(
                f"fk_{table}_user_id_users", "users", ["user_id"], ["id"],
                ondelete="CASCADE",
            )
            batch.create_unique_constraint(
                f"uq_{table}_campaign_account", ["campaign_id", "user_id"]
            )
            batch.create_index(f"ix_{table}_user_id", ["user_id"])


def downgrade():
    bind = op.get_bind()
    for table in (*RELEASE_TABLES, "bot_feedbacks"):
        column = "user_telegram_id" if table in RELEASE_TABLES else "telegram_id"
        if bind.execute(sa.text(
            f"SELECT 1 FROM {table} WHERE {column} IS NULL LIMIT 1"
        )).first():
            raise RuntimeError(
                "Refusing downgrade with provider-only feedback; preserve account data"
            )

    for table in reversed(RELEASE_TABLES):
        with op.batch_alter_table(table) as batch:
            batch.drop_index(f"ix_{table}_user_id")
            batch.drop_constraint(f"uq_{table}_campaign_account", type_="unique")
            batch.drop_constraint(f"fk_{table}_user_id_users", type_="foreignkey")
            batch.drop_column("user_id")
            batch.alter_column("user_telegram_id", existing_type=sa.BigInteger(), nullable=False)

    with op.batch_alter_table("bot_feedbacks") as batch:
        batch.alter_column("telegram_id", existing_type=sa.BigInteger(), nullable=False)
