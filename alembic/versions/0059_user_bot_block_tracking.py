"""add Telegram bot block tracking to users

Revision ID: 0059_user_bot_block_tracking
Revises: 0058_course_ad_link_url
Create Date: 2026-06-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0059_user_bot_block_tracking"
down_revision: Union[str, None] = "0058_course_ad_link_url"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("bot_blocked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("bot_unblocked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("last_bot_block_check_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("bot_block_reason", sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "bot_block_reason")
    op.drop_column("users", "last_bot_block_check_at")
    op.drop_column("users", "bot_unblocked_at")
    op.drop_column("users", "bot_blocked_at")
