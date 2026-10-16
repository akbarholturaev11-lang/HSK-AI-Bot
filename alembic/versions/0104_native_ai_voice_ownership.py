"""Canonical account ownership for AI budgets/events and voice sessions."""
from alembic import op
import sqlalchemy as sa

revision = "0104_native_ai_voice_ownership"
down_revision = "0103_native_account_foundation"
branch_labels = None
depends_on = None
TABLES = ("ai_usage_budgets", "ai_usage_events", "voice_practice_sessions")


def upgrade():
    for table in TABLES:
        columns = {c["name"]: c for c in sa.inspect(op.get_bind()).get_columns(table)}
        with op.batch_alter_table(table) as batch:
            if "user_id" not in columns:
                batch.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
                batch.create_foreign_key(f"fk_{table}_user_id", "users", ["user_id"], ["id"], ondelete="CASCADE")
                batch.create_index(f"ix_{table}_user_id", ["user_id"])
            if not columns["user_telegram_id"]["nullable"]:
                batch.alter_column("user_telegram_id", existing_type=sa.BigInteger(), nullable=True)
        op.execute(sa.text(f"UPDATE {table} SET user_id = (SELECT users.id FROM users WHERE users.telegram_id = {table}.user_telegram_id) WHERE user_id IS NULL"))


def downgrade():
    # Preflight all tables before any batch DDL, including on SQLite where a
    # later refusal cannot reliably roll back earlier table reconstruction.
    for table in TABLES:
        if op.get_bind().execute(sa.text(f"SELECT 1 FROM {table} WHERE user_telegram_id IS NULL LIMIT 1")).first():
            raise RuntimeError("Provider-only AI/voice data exists; refusing destructive downgrade")
    for table in TABLES:
        inspector = sa.inspect(op.get_bind())
        foreign_keys = [fk for fk in inspector.get_foreign_keys(table) if fk["constrained_columns"] == ["user_id"]]
        indexes = {index["name"] for index in inspector.get_indexes(table)}
        # Bootstrap-created FKs may be unnamed on SQLite or automatically
        # named by PostgreSQL. Reflect the actual constraint, not an assumed
        # name from a migration that did not create that column.
        with op.batch_alter_table(table, naming_convention={"fk": "fk_%(table_name)s_%(column_0_name)s"}) as batch:
            for fk in foreign_keys:
                batch.drop_constraint(fk["name"] or f"fk_{table}_user_id", type_="foreignkey")
            if f"ix_{table}_user_id" in indexes:
                batch.drop_index(f"ix_{table}_user_id")
            batch.drop_column("user_id")
            batch.alter_column("user_telegram_id", existing_type=sa.BigInteger(), nullable=False)
