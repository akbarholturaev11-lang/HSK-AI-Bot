"""add referral trial activation counter

Revision ID: 0028_referral_trial_activation
Revises: 0027_add_ad_campaigns
Create Date: 2026-05-24
"""

from alembic import op
import sqlalchemy as sa


revision = "0028_referral_trial_activation"
down_revision = "0027_add_ad_campaigns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("referral_trial_count_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE users "
            "SET referral_trial_count_started_at = CURRENT_TIMESTAMP "
            "WHERE referral_trial_count_started_at IS NULL"
        )
    )


def downgrade() -> None:
    op.drop_column("users", "referral_trial_count_started_at")
