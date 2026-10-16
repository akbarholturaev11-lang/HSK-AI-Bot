"""Keep native account metadata and deduplication keyed to users.id."""
from alembic import op
import sqlalchemy as sa

revision = "0103_native_account_foundation"
down_revision = "0102_native_identity_accounts"
branch_labels = None
depends_on = None

TABLES = {
    "account_notice_deliveries": "telegram_id",
    "conversion_funnel_events": "telegram_id",
    "course_ad_views": "user_telegram_id",
    "course_miniapp_events": "telegram_id",
    "course_user_notifications": "telegram_id",
    "trial_risk_events": "telegram_id",
}
UNIQUE_KEYS = {
    "course_miniapp_events": ("uq_course_miniapp_events_user_event_dedupe", ["user_id", "event_name", "dedupe_key"]),
    "course_user_notifications": ("uq_course_user_notifications_user_key_dedupe", ["user_id", "key", "dedupe_key"]),
}


def upgrade():
    for table, column in TABLES.items():
        columns = {c["name"]: c for c in sa.inspect(op.get_bind()).get_columns(table)}
        if not columns[column]["nullable"]:
            with op.batch_alter_table(table) as batch:
                batch.alter_column(column, existing_type=sa.BigInteger(), nullable=True)
        op.execute(sa.text(
            f"UPDATE {table} SET user_id = (SELECT users.id FROM users "
            f"WHERE users.telegram_id = {table}.{column}) WHERE user_id IS NULL"
        ))
        if table in UNIQUE_KEYS:
            name, fields = UNIQUE_KEYS[table]
            existing = {c["name"] for c in sa.inspect(op.get_bind()).get_unique_constraints(table)}
            if name not in existing:
                with op.batch_alter_table(table) as batch:
                    batch.create_unique_constraint(name, fields)


def downgrade():
    # Check every table before changing anything; never discard native data.
    for table, column in TABLES.items():
        if op.get_bind().execute(sa.text(f"SELECT 1 FROM {table} WHERE {column} IS NULL LIMIT 1")).first():
            raise RuntimeError("Provider-only account data exists; refusing destructive downgrade")
    for table, column in TABLES.items():
        with op.batch_alter_table(table) as batch:
            if table in UNIQUE_KEYS:
                batch.drop_constraint(UNIQUE_KEYS[table][0], type_="unique")
            batch.alter_column(column, existing_type=sa.BigInteger(), nullable=False)
