"""add app ad fields to course ad creatives

App reklamasi ("app" turi) Mini App ochilganda markazda ko'rsatiladi.
Boshqa reklama turlaridan farqli ravishda ikkita qo'shimcha sozlama kerak:

- `skip_after_seconds` — yopish (X) tugmasi necha soniyadan keyin paydo bo'lishi.
- `daily_limit` — bir foydalanuvchiga kuniga necha marta ko'rsatilishi
  (0 yoki NULL — cheklovsiz).

Ikkalasi ham nullable: mavjud reklamalarga (odiy/hamkorlik/bot/dars_yakuni)
ta'sir qilmaydi, ular bu maydonlarni ishlatmaydi.

Revision ID: 0068_course_ad_app_type
Revises: 0067_course_user_notifications
Create Date: 2026-08-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0068_course_ad_app_type"
down_revision: Union[str, None] = "0067_course_user_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "course_ad_creatives",
        sa.Column("skip_after_seconds", sa.Integer(), nullable=True),
    )
    op.add_column(
        "course_ad_creatives",
        sa.Column("daily_limit", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("course_ad_creatives", "daily_limit")
    op.drop_column("course_ad_creatives", "skip_after_seconds")
