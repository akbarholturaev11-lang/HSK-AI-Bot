"""Publish HSK 3.0 N1-N3 as the live server level set.

Revision ID: 0099_hsk30_live_n1_n3
Revises: 0098_merge_all_heads
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0099_hsk30_live_n1_n3"
down_revision: Union[str, tuple[str, ...], None] = "0098_merge_all_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SETTING_KEY = "hsk30_live_levels"
_LIVE_VALUE = "nhsk1,nhsk2,nhsk3"


def upgrade() -> None:
    connection = op.get_bind()
    current = connection.execute(
        sa.text("SELECT value FROM bot_settings WHERE key = :key"),
        {"key": _SETTING_KEY},
    ).scalar_one_or_none()
    if current is None:
        connection.execute(
            sa.text(
                "INSERT INTO bot_settings (key, value, updated_at) "
                "VALUES (:key, :value, CURRENT_TIMESTAMP)"
            ),
            {"key": _SETTING_KEY, "value": _LIVE_VALUE},
        )
    elif str(current).strip() != _LIVE_VALUE:
        connection.execute(
            sa.text(
                "UPDATE bot_settings "
                "SET value = :value, updated_at = CURRENT_TIMESTAMP "
                "WHERE key = :key"
            ),
            {"key": _SETTING_KEY, "value": _LIVE_VALUE},
        )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE bot_settings "
            "SET value = 'nhsk1', updated_at = CURRENT_TIMESTAMP "
            "WHERE key = :key"
        ),
        {"key": _SETTING_KEY},
    )
