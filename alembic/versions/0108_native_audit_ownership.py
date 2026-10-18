"""Complete native ownership for pilot events, shadow samples and personal offers."""
from alembic import op
import sqlalchemy as sa

revision = "0108_native_audit_ownership"
down_revision = "0107_canonical_referral_owners"
branch_labels = None
depends_on = None

OWNERS = {
    "course_pilot_events": ("user_id", "telegram_id", "SET NULL"),
    "entitlement_shadow_events": ("user_id", "telegram_id", "SET NULL"),
    "discount_campaigns": ("target_user_id", "target_telegram_id", "CASCADE"),
}
SHADOW_UNIQUE = "uq_entitlement_shadow_user_daily"


def _columns(table):
    return {column["name"]: column for column in sa.inspect(op.get_bind()).get_columns(table)}


def _preflight_upgrade(bind, tables):
    # Validate the whole change before DDL/backfill. In particular, an old
    # shadow alias must not get partially backfilled before a duplicate fails.
    for table, (owner, _telegram, ondelete) in OWNERS.items():
        if table not in tables:
            continue
        for fk in sa.inspect(bind).get_foreign_keys(table):
            if owner not in fk["constrained_columns"]:
                continue
            if (fk["constrained_columns"] != [owner] or fk["referred_table"] != "users"
                    or fk["referred_columns"] != ["id"]
                    or str(fk.get("options", {}).get("ondelete") or "").upper() != ondelete):
                raise RuntimeError("Unexpected canonical ownership foreign key; refusing unsafe migration")
    if "entitlement_shadow_events" in tables:
        owner = "COALESCE(events.user_id, users.id)" if "user_id" in _columns("entitlement_shadow_events") else "users.id"
        duplicate = bind.execute(sa.text(
            "SELECT 1 FROM entitlement_shadow_events AS events LEFT JOIN users "
            "ON users.telegram_id = events.telegram_id AND events.telegram_id > 0 "
            f"GROUP BY {owner}, events.action, events.client, events.day_key, events.agree "
            f"HAVING {owner} IS NOT NULL AND COUNT(*) > 1 LIMIT 1"
        )).first()
        if duplicate:
            raise RuntimeError("Duplicate canonical shadow samples require reconciliation before upgrade")


def upgrade():
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    _preflight_upgrade(bind, tables)
    for table, (owner, telegram, ondelete) in OWNERS.items():
        if table not in tables:
            continue
        columns = _columns(table)
        if owner not in columns:
            op.add_column(table, sa.Column(owner, sa.Integer(), nullable=True))
        columns = _columns(table)
        if not columns[telegram]["nullable"]:
            with op.batch_alter_table(table) as batch:
                batch.alter_column(telegram, existing_type=sa.BigInteger(), nullable=True)
        # Never overwrite an existing canonical owner with transport metadata.
        bind.execute(sa.text(
            f"UPDATE {table} SET {owner} = (SELECT users.id FROM users "
            f"WHERE users.telegram_id = {table}.{telegram}) "
            f"WHERE {owner} IS NULL AND {telegram} > 0"
        ))
        foreign_keys = sa.inspect(bind).get_foreign_keys(table)
        if not any(fk["constrained_columns"] == [owner] and fk["referred_table"] == "users"
                   for fk in foreign_keys):
            with op.batch_alter_table(table) as batch:
                batch.create_foreign_key(f"fk_{table}_{owner}_users", "users", [owner], ["id"], ondelete=ondelete)
        index_name = f"ix_{table}_{owner}"
        if index_name not in {index["name"] for index in sa.inspect(bind).get_indexes(table)}:
            op.create_index(index_name, table, [owner])

    if "entitlement_shadow_events" in tables:
        constraints = {item["name"] for item in sa.inspect(bind).get_unique_constraints("entitlement_shadow_events")}
        if SHADOW_UNIQUE not in constraints:
            duplicate = bind.execute(sa.text(
                "SELECT 1 FROM entitlement_shadow_events WHERE user_id IS NOT NULL "
                "GROUP BY user_id, action, client, day_key, agree HAVING COUNT(*) > 1 LIMIT 1"
            )).first()
            if duplicate:
                raise RuntimeError("Duplicate canonical shadow samples require reconciliation before upgrade")
            with op.batch_alter_table("entitlement_shadow_events") as batch:
                batch.create_unique_constraint(SHADOW_UNIQUE, ["user_id", "action", "client", "day_key", "agree"])


def downgrade():
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    # A downgrade must not discard native diagnostics or turn a personal offer
    # into a global one. Validate every table before making any schema change.
    for table, (owner, telegram, _ondelete) in OWNERS.items():
        if table not in tables:
            continue
        native_only = f"{telegram} IS NULL"
        if table == "discount_campaigns":
            native_only += f" AND {owner} IS NOT NULL"
        if bind.execute(sa.text(f"SELECT 1 FROM {table} WHERE {native_only} LIMIT 1")).first():
            raise RuntimeError("Native ownership data exists; downgrade would lose its meaning")
        if owner in _columns(table) and bind.execute(sa.text(
            f"SELECT 1 FROM {table} LEFT JOIN users ON users.id = {table}.{owner} "
            f"WHERE {table}.{owner} IS NOT NULL AND "
            f"(users.telegram_id IS NULL OR users.telegram_id != {table}.{telegram}) LIMIT 1"
        )).first():
            raise RuntimeError("Canonical ownership differs from Telegram metadata; downgrade refused")

    for table, (owner, telegram, _ondelete) in reversed(list(OWNERS.items())):
        if table not in tables:
            continue
        if table != "course_pilot_events" and owner in _columns(table):
            with op.batch_alter_table(table) as batch:
                if table == "entitlement_shadow_events":
                    constraints = {item["name"] for item in sa.inspect(bind).get_unique_constraints(table)}
                    if SHADOW_UNIQUE in constraints:
                        batch.drop_constraint(SHADOW_UNIQUE, type_="unique")
                for fk in sa.inspect(bind).get_foreign_keys(table):
                    if fk["constrained_columns"] == [owner]:
                        batch.drop_constraint(fk["name"], type_="foreignkey")
                index_name = f"ix_{table}_{owner}"
                if index_name in {index["name"] for index in sa.inspect(bind).get_indexes(table)}:
                    batch.drop_index(index_name)
                batch.drop_column(owner)
        if table != "discount_campaigns":
            with op.batch_alter_table(table) as batch:
                batch.alter_column(telegram, existing_type=sa.BigInteger(), nullable=False)
