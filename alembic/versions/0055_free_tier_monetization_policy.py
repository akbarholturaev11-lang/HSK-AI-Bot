"""tighten free-tier limits and course access policy

Revision ID: 0055_free_tier_monetization_policy
Revises: 0054_add_notification_motivation
Create Date: 2026-06-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0055_free_tier_monetization_policy"
down_revision: Union[str, None] = "0054_add_notification_motivation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "question_limit",
        existing_type=sa.Integer(),
        server_default="5",
        existing_nullable=False,
    )
    op.execute(
        sa.text(
            """
            UPDATE users
            SET question_limit = 5
            WHERE question_limit = 10
              AND COALESCE(payment_status, 'none') != 'approved'
              AND COALESCE(status, 'trial') IN ('trial', 'free', 'expired')
            """
        )
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "question_limit",
        existing_type=sa.Integer(),
        server_default="10",
        existing_nullable=False,
    )
