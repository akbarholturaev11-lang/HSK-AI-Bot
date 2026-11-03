"""Canonical feedback ownership for linked Telegram and browser-only learners.

Historical feedback rows retain their genuine Telegram transport; only matching
existing users are backfilled. Unlinked legacy Telegram rows remain nullable
rather than fabricating a users.id. Both old Telegram and canonical uniqueness
are kept, and a downgrade refuses to discard provider-only feedback.

The isolated QA initializer creates the latest empty ORM schema before
replaying migrations from its reviewed baseline. This upgrade must accept
both that already-current empty schema and the real historical 0145 layout
without weakening ownership constraints or backfill.
"""
from alembic import op
import sqlalchemy as sa


revision = "0146_pwa_feedback_owner"
down_revision = "0145_smart_baseline_outcomes"
branch_labels = None
depends_on = None

RELEASE_TABLES = ("release_feedback_deliveries", "release_feedback_responses")


def _columns(table):
    return {column["name"]: column for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade():
    if not _columns("bot_feedbacks")["telegram_id"]["nullable"]:
        with op.batch_alter_table("bot_feedbacks") as batch:
            batch.alter_column("telegram_id", existing_type=sa.BigInteger(), nullable=True)

    for table in RELEASE_TABLES:
        columns = _columns(table)
        if "user_id" not in columns or not columns["user_telegram_id"]["nullable"]:
            with op.batch_alter_table(table) as batch:
                if "user_id" not in columns:
                    batch.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
                if not columns["user_telegram_id"]["nullable"]:
                    batch.alter_column("user_telegram_id", existing_type=sa.BigInteger(), nullable=True)

        # Even if the latest ORM schema already exists, repair legitimate
        # historical Telegram-only rows without touching canonical ownership.
        op.execute(sa.text(
            f"UPDATE {table} SET user_id = "
            f"(SELECT users.id FROM users WHERE users.telegram_id = "
            f"{table}.user_telegram_id) "
            f"WHERE user_id IS NULL AND user_telegram_id IS NOT NULL"
        ))

        constraints = sa.inspect(op.get_bind()).get_foreign_keys(table)
        if not any(
            fk.get("constrained_columns") == ["user_id"]
            and fk.get("referred_table") == "users"
            and fk.get("referred_columns") == ["id"]
            for fk in constraints
        ):
            with op.batch_alter_table(table) as batch:
                batch.create_foreign_key(
                    f"fk_{table}_user_id_users", "users", ["user_id"], ["id"],
                    ondelete="CASCADE",
                )

        unique_name = f"uq_{table}_campaign_account"
        existing_unique = {
            item["name"] for item in sa.inspect(op.get_bind()).get_unique_constraints(table)
        }
        if unique_name not in existing_unique:
            with op.batch_alter_table(table) as batch:
                batch.create_unique_constraint(unique_name, ["campaign_id", "user_id"])

        index_name = f"ix_{table}_user_id"
        existing_indexes = {
            item["name"] for item in sa.inspect(op.get_bind()).get_indexes(table)
        }
        if index_name not in existing_indexes:
            with op.batch_alter_table(table) as batch:
                batch.create_index(index_name, ["user_id"])


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
