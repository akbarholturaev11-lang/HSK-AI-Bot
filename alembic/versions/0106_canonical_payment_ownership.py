"""Canonical payment owners with retained, non-cascading financial facts."""
from alembic import op
import sqlalchemy as sa


revision = "0106_canonical_payment_ownership"
down_revision = "0105_native_ai_voice_ownership"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    columns = {column["name"]: column for column in sa.inspect(connection).get_columns("payments")}
    indexes = {index["name"] for index in sa.inspect(connection).get_indexes("payments")}
    with op.batch_alter_table("payments") as batch:
        if "user_id" not in columns:
            # No FK: account purge explicitly anonymizes approved accounting
            # facts; an automatic cascade must never remove financial history.
            batch.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        if "ix_payments_user_id" not in indexes:
            batch.create_index("ix_payments_user_id", ["user_id"])
        if not columns["user_telegram_id"]["nullable"]:
            batch.alter_column("user_telegram_id", existing_type=sa.BigInteger(), nullable=True)
    # Negative deletion sentinels and orphaned legacy facts are not identities.
    # Existing canonical ownership is authoritative, including retained keys.
    op.execute(sa.text("""
        UPDATE payments SET user_id = (
            SELECT users.id FROM users
            WHERE users.telegram_id = payments.user_telegram_id
              AND users.telegram_id > 0
        )
        WHERE user_id IS NULL AND user_telegram_id > 0
          AND EXISTS (
            SELECT 1 FROM users
            WHERE users.telegram_id = payments.user_telegram_id
              AND users.telegram_id > 0
          )
    """))
    entry_columns = {column["name"]: column for column in sa.inspect(connection).get_columns("subscription_entry_events")}
    if not entry_columns["telegram_id"]["nullable"]:
        with op.batch_alter_table("subscription_entry_events") as batch:
            batch.alter_column("telegram_id", existing_type=sa.BigInteger(), nullable=True)
    op.execute(sa.text("""
        UPDATE subscription_entry_events SET user_id = (
            SELECT users.id FROM users
            WHERE users.telegram_id = subscription_entry_events.telegram_id
              AND users.telegram_id > 0
        )
        WHERE user_id IS NULL AND telegram_id > 0
          AND EXISTS (
            SELECT 1 FROM users
            WHERE users.telegram_id = subscription_entry_events.telegram_id
              AND users.telegram_id > 0
          )
    """))


def downgrade():
    connection = op.get_bind()
    # Preflight before any DDL, especially SQLite batch reconstruction. A
    # deleted learner's retained canonical key cannot safely be discarded.
    for table, telegram_column in (("payments", "user_telegram_id"), ("subscription_entry_events", "telegram_id")):
        incompatible = connection.execute(sa.text(f"""
            SELECT 1 FROM {table}
            WHERE {telegram_column} IS NULL
               OR (user_id IS NOT NULL AND NOT EXISTS (
                   SELECT 1 FROM users
                   WHERE users.id = {table}.user_id
                     AND users.telegram_id = {table}.{telegram_column}
                     AND users.telegram_id > 0
               ))
            LIMIT 1
        """)).first()
        if incompatible:
            raise RuntimeError(f"Provider-only or unrecoverable canonical {table} data exists; refusing destructive downgrade")
    indexes = {index["name"] for index in sa.inspect(connection).get_indexes("payments")}
    with op.batch_alter_table("payments") as batch:
        if "ix_payments_user_id" in indexes:
            batch.drop_index("ix_payments_user_id")
        batch.drop_column("user_id")
        batch.alter_column("user_telegram_id", existing_type=sa.BigInteger(), nullable=False)
    with op.batch_alter_table("subscription_entry_events") as batch:
        batch.alter_column("telegram_id", existing_type=sa.BigInteger(), nullable=False)
