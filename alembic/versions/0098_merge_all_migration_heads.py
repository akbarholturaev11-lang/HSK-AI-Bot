"""Merge Android Live Voice with the course and subscription migration heads.

Revision ID: 0098_merge_all_heads
Revises: 0095_android_live_voice, 0097_merge_course_and_currency
"""

from typing import Sequence, Union


revision: str = "0098_merge_all_heads"
down_revision: Union[str, tuple[str, ...], None] = (
    "0095_android_live_voice",
    "0097_merge_course_and_currency",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
