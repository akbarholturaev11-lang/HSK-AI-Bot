"""make partner signup bonus lifetime one-time

Revision ID: 0034_partner_signup_bonus_once
Revises: 0033_partner_payout_recipient_qr
Create Date: 2026-06-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0034_partner_signup_bonus_once"
down_revision = "0033_partner_payout_recipient_qr"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    return column_name in {column["name"] for column in inspect(bind).get_columns(table_name)}


def upgrade() -> None:
    if not _has_column("partners", "signup_bonus_granted_at"):
        op.add_column("partners", sa.Column("signup_bonus_granted_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE partners AS partner
            SET signup_bonus_granted_at = bonus.first_granted_at
            FROM (
                SELECT partner_id, MIN(created_at) AS first_granted_at
                FROM partner_credits
                WHERE credit_type = 'signup_bonus'
                GROUP BY partner_id
            ) AS bonus
            WHERE partner.id = bonus.partner_id
              AND partner.signup_bonus_granted_at IS NULL
            """
        )
    )


def downgrade() -> None:
    if _has_column("partners", "signup_bonus_granted_at"):
        op.drop_column("partners", "signup_bonus_granted_at")
