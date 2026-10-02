"""Merge course targeting and subscription currency migration branches.

Revision ID: 0097_merge_course_and_currency
Revises: 0096_ad_campaign_course_target, 0095_subscription_currency_preference
"""

from typing import Sequence, Union


revision: str = "0097_merge_course_and_currency"
down_revision: Union[str, tuple[str, ...], None] = (
    "0096_ad_campaign_course_target",
    "0095_subscription_currency_preference",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
