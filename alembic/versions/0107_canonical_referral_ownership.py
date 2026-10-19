"""Canonical referral owners and signup attribution independent of providers."""
from alembic import op
import sqlalchemy as sa

revision = "0107_canonical_referral_owners"
down_revision = "0106_canonical_payment_ownership"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = {c["name"]: c for c in inspector.get_columns("referrals")}
    indexes = {i["name"] for i in inspector.get_indexes("referrals")}
    foreign_keys = {tuple(fk["constrained_columns"]): fk for fk in inspector.get_foreign_keys("referrals")}
    uniques = {tuple(u["column_names"]) for u in inspector.get_unique_constraints("referrals")}
    uniques.update(tuple(i["column_names"]) for i in inspector.get_indexes("referrals") if i.get("unique"))
    with op.batch_alter_table("referrals") as batch:
        for role in ("referrer", "invited"):
            name = f"{role}_user_id"
            if name not in columns:
                batch.add_column(sa.Column(name, sa.Integer(), nullable=True))
            if (name,) not in foreign_keys:
                batch.create_foreign_key(f"fk_referrals_{name}_users", "users", [name], ["id"], ondelete="CASCADE")
            else:
                fk = foreign_keys[(name,)]
                if fk["referred_table"] != "users" or fk["referred_columns"] != ["id"] or str(fk.get("options", {}).get("ondelete") or "").upper() != "CASCADE":
                    raise RuntimeError(f"Unexpected canonical referral foreign key for {name}; refusing unsafe migration")
            if role == "invited" and (name,) not in uniques:
                batch.create_unique_constraint("uq_referrals_invited_user_id", [name])
            if role == "referrer" and "ix_referrals_referrer_user_id" not in indexes:
                batch.create_index("ix_referrals_referrer_user_id", [name])
        for name in ("referrer_telegram_id", "invited_user_telegram_id"):
            if not columns[name]["nullable"]:
                batch.alter_column(name, existing_type=sa.BigInteger(), nullable=True)
    for role, telegram in (("referrer", "referrer_telegram_id"), ("invited", "invited_user_telegram_id")):
        op.execute(sa.text(f"""
            UPDATE referrals SET {role}_user_id = (
                SELECT users.id FROM users WHERE users.telegram_id = referrals.{telegram} AND users.telegram_id > 0
            ) WHERE {role}_user_id IS NULL AND {telegram} > 0 AND EXISTS (
                SELECT 1 FROM users WHERE users.telegram_id = referrals.{telegram} AND users.telegram_id > 0
            )
        """))
    request_columns = {c["name"] for c in sa.inspect(connection).get_columns("desktop_link_requests")}
    if "referral_code" not in request_columns:
        with op.batch_alter_table("desktop_link_requests") as batch:
            batch.add_column(sa.Column("referral_code", sa.String(64), nullable=True))


def downgrade():
    connection = op.get_bind()
    # A provider account's referral cannot be represented by legacy Telegram
    # columns. Refuse before changing any schema or losing earned rewards.
    for role, telegram in (("referrer", "referrer_telegram_id"), ("invited", "invited_user_telegram_id")):
        incompatible = connection.execute(sa.text(f"""
            SELECT 1 FROM referrals WHERE {telegram} IS NULL OR (
                {role}_user_id IS NOT NULL AND NOT EXISTS (
                    SELECT 1 FROM users WHERE users.id = referrals.{role}_user_id
                    AND users.telegram_id = referrals.{telegram} AND users.telegram_id > 0
                )
            ) LIMIT 1
        """)).first()
        if incompatible:
            raise RuntimeError("Provider-only referral data exists; refusing destructive downgrade")
    if connection.execute(sa.text("SELECT 1 FROM desktop_link_requests WHERE referral_code IS NOT NULL AND status = 'pending' LIMIT 1")).first():
        raise RuntimeError("Pending signup attribution exists; refusing destructive downgrade")
    with op.batch_alter_table("desktop_link_requests") as batch:
        batch.drop_column("referral_code")
    with op.batch_alter_table("referrals") as batch:
        batch.drop_constraint("fk_referrals_referrer_user_id_users", type_="foreignkey")
        batch.drop_constraint("fk_referrals_invited_user_id_users", type_="foreignkey")
        batch.drop_constraint("uq_referrals_invited_user_id", type_="unique")
        batch.drop_index("ix_referrals_referrer_user_id")
        batch.drop_column("referrer_user_id")
        batch.drop_column("invited_user_id")
        batch.alter_column("referrer_telegram_id", existing_type=sa.BigInteger(), nullable=False)
        batch.alter_column("invited_user_telegram_id", existing_type=sa.BigInteger(), nullable=False)
