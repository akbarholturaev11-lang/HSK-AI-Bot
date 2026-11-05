"""lava.top automated Pro subscriptions: invoice ownership and webhook ledger.

Adds two new tables only; existing payment/user tables are unchanged. The
downgrade refuses to drop recorded financial evidence.
"""
from alembic import op
import sqlalchemy as sa

revision = "0151_lava_top_payments"
down_revision = "0150_smart_reminder_rollout"
branch_labels = None
depends_on = None

_INVOICE_STATUSES = (
    "created", "paid", "failed", "expired", "refunded",
    "chargeback_open", "chargeback_won", "chargeback_lost", "unmatched",
)
_INVOICE_KINDS = ("first", "renewal", "external")
_EVENT_RESULTS = (
    "received", "queued", "applied", "duplicate", "ignored", "unmatched",
    "needs_review", "retry", "error",
)


def _in(values) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade():
    op.create_table(
        "lava_invoices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("contract_id", sa.String(length=36), nullable=False),
        sa.Column("parent_contract_id", sa.String(length=36), nullable=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("plan_type", sa.String(length=32), nullable=True),
        sa.Column("offer_id", sa.String(length=36), nullable=True),
        sa.Column("periodicity", sa.String(length=24), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("expected_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("paid_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("buyer_email", sa.String(length=254), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("promo_code", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("review_reason", sa.String(length=48), nullable=True),
        sa.Column("subscription_status", sa.String(length=16), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("will_expire_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payment_id", sa.Integer(), nullable=True),
        sa.Column("granted_days", sa.Integer(), nullable=True),
        sa.Column("granted_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("granted_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(f"status IN ({_in(_INVOICE_STATUSES)})", name=op.f("ck_lava_invoices_status")),
        sa.CheckConstraint(f"kind IN ({_in(_INVOICE_KINDS)})", name=op.f("ck_lava_invoices_kind")),
        sa.CheckConstraint("granted_days IS NULL OR granted_days > 0", name=op.f("ck_lava_invoices_granted_days")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lava_invoices")),
        sa.UniqueConstraint("contract_id", name=op.f("uq_lava_invoices_contract_id")),
        sa.UniqueConstraint("payment_id", name=op.f("uq_lava_invoices_payment_id")),
    )
    op.create_index(op.f("ix_lava_invoices_parent_contract_id"), "lava_invoices", ["parent_contract_id"])
    op.create_index(op.f("ix_lava_invoices_user_id"), "lava_invoices", ["user_id"])
    op.create_index("ix_lava_invoices_status_created", "lava_invoices", ["status", "created_at"])

    op.create_table(
        "lava_webhook_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dedupe_key", sa.String(length=160), nullable=False),
        sa.Column("event_type", sa.String(length=48), nullable=False),
        sa.Column("contract_id", sa.String(length=36), nullable=True),
        sa.Column("parent_contract_id", sa.String(length=36), nullable=True),
        sa.Column("provider_status", sa.String(length=32), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("product_id", sa.String(length=36), nullable=True),
        sa.Column("tier_id", sa.String(length=36), nullable=True),
        sa.Column("refund_type", sa.String(length=16), nullable=True),
        sa.Column("email_sha256", sa.String(length=64), nullable=True),
        sa.Column("payload_sha256", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column("result", sa.String(length=24), nullable=False),
        sa.Column("error_code", sa.String(length=48), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("invoice_id", sa.Integer(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(f"result IN ({_in(_EVENT_RESULTS)})", name=op.f("ck_lava_webhook_events_result")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lava_webhook_events")),
        sa.UniqueConstraint("dedupe_key", name=op.f("uq_lava_webhook_events_dedupe_key")),
    )
    op.create_index(op.f("ix_lava_webhook_events_contract_id"), "lava_webhook_events", ["contract_id"])
    op.create_index("ix_lava_webhook_events_result_received", "lava_webhook_events", ["result", "received_at"])


def downgrade():
    bind = op.get_bind()
    for table in ("lava_invoices", "lava_webhook_events"):
        if bind.execute(sa.text(f"SELECT 1 FROM {table} LIMIT 1")).first():
            raise RuntimeError(f"Refusing to drop non-empty {table} financial evidence")
    op.drop_index("ix_lava_webhook_events_result_received", table_name="lava_webhook_events")
    op.drop_index(op.f("ix_lava_webhook_events_contract_id"), table_name="lava_webhook_events")
    op.drop_table("lava_webhook_events")
    op.drop_index("ix_lava_invoices_status_created", table_name="lava_invoices")
    op.drop_index(op.f("ix_lava_invoices_user_id"), table_name="lava_invoices")
    op.drop_index(op.f("ix_lava_invoices_parent_contract_id"), table_name="lava_invoices")
    op.drop_table("lava_invoices")
