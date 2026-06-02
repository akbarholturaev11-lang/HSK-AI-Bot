"""add partner payout currency and concurrency safety

Revision ID: 0035_partner_payout_safety
Revises: 0034_partner_signup_bonus_once
Create Date: 2026-06-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0035_partner_payout_safety"
down_revision = "0034_partner_signup_bonus_once"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    return column_name in {column["name"] for column in inspect(bind).get_columns(table_name)}


def _has_index(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    return index_name in {index["name"] for index in inspect(bind).get_indexes(table_name)}


def _find_duplicate_open_payout() -> tuple[int, int] | None:
    bind = op.get_bind()
    return bind.execute(
        sa.text(
            """
            SELECT partner_id, COUNT(*) AS payout_count
            FROM partner_payouts
            WHERE status IN ('pending', 'deadline_set', 'processing')
            GROUP BY partner_id
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).first()


def upgrade() -> None:
    if not _has_column("partner_payouts", "local_currency"):
        op.add_column(
            "partner_payouts",
            sa.Column("local_currency", sa.String(length=8), server_default="TJS", nullable=False),
        )
    if not _has_column("partner_payouts", "processing_by_telegram_id"):
        op.add_column("partner_payouts", sa.Column("processing_by_telegram_id", sa.BigInteger(), nullable=True))
    if not _has_column("partner_payouts", "processing_started_at"):
        op.add_column(
            "partner_payouts",
            sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
        )
    if not _has_index("partner_payouts", "uq_partner_payouts_one_open_per_partner"):
        duplicate = _find_duplicate_open_payout()
        if duplicate:
            raise RuntimeError(
                "Cannot add partner payout safety index: "
                f"partner_id={duplicate[0]} has {duplicate[1]} open payouts. "
                "Review existing payout rows manually before deployment."
            )
        op.create_index(
            "uq_partner_payouts_one_open_per_partner",
            "partner_payouts",
            ["partner_id"],
            unique=True,
            postgresql_where=sa.text("status IN ('pending', 'deadline_set', 'processing')"),
        )


def downgrade() -> None:
    if _has_index("partner_payouts", "uq_partner_payouts_one_open_per_partner"):
        op.drop_index("uq_partner_payouts_one_open_per_partner", table_name="partner_payouts")
    if _has_column("partner_payouts", "processing_started_at"):
        op.drop_column("partner_payouts", "processing_started_at")
    if _has_column("partner_payouts", "processing_by_telegram_id"):
        op.drop_column("partner_payouts", "processing_by_telegram_id")
    if _has_column("partner_payouts", "local_currency"):
        op.drop_column("partner_payouts", "local_currency")
