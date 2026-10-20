"""Allow native provider accounts without Telegram; preserve unique real IDs."""
from alembic import op
import sqlalchemy as sa

revision = "0103_native_identity_accounts"
down_revision = "0102_payment_review_preview"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("users", "desktop_devices"):
        columns = {c["name"]: c for c in sa.inspect(op.get_bind()).get_columns(table)}
        if not columns["telegram_id"]["nullable"]:
            with op.batch_alter_table(table) as batch:
                batch.alter_column("telegram_id", existing_type=sa.BigInteger(), nullable=True)
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("desktop_link_requests")}
    for name, size in (("language", 8), ("bind_session_id", 36), ("approved_identity_id", 36)):
        if name not in columns:
            op.add_column("desktop_link_requests", sa.Column(name, sa.String(size), nullable=True))
    if "bind_session_id" not in columns and {"intent", "status"}.issubset(columns):
        # Old native link proofs cannot prove their initiating session is
        # still valid. A fresh start is safe; never revive such a proof.
        op.execute(sa.text("UPDATE desktop_link_requests SET status = 'expired' WHERE intent = 'link' AND status = 'pending'"))


def downgrade():
    # Refuse a rollback that would discard existing provider-only accounts.
    for table in ("users", "desktop_devices"):
        if op.get_bind().execute(sa.text(f"SELECT 1 FROM {table} WHERE telegram_id IS NULL LIMIT 1")).first():
            raise RuntimeError("Provider-only accounts exist; migrate their identities before downgrade")
    for name in ("approved_identity_id", "bind_session_id", "language"):
        op.drop_column("desktop_link_requests", name)
    for table in ("users", "desktop_devices"):
        with op.batch_alter_table(table) as batch:
            batch.alter_column("telegram_id", existing_type=sa.BigInteger(), nullable=False)
