"""maqsad ATAYLAB tanlanganmi degan belgi

Maqsad savoli onboardingga endi qo'shildi. Undan OLDIN ro'yxatdan o'tgan
o'quvchilarda `goal` ustuni bor, lekin uning qiymati — jadval defaulti
(`hsk_exam`), foydalanuvchi tanlovi emas. Ikkalasini farqlab bo'lmasdi,
shuning uchun mavjud o'quvchilardan maqsadni qayta so'rash imkoni yo'q edi
va ular uchun kunlik reja doim imtihon rejimida qolardi.

`goal_chosen_at` shu farqni beradi: NULL = hali so'ralmagan. Birinchi dars
tugagach o'quvchidan so'raladi (kunlik vaqt va fokus bilan bir oqimda).

Nega alohida ustun: `goal` ning o'zi NOT NULL va CHECK bilan cheklangan,
ya'ni "hali tanlanmagan" holatini u yerda ifodalab bo'lmaydi.

Revision ID: 0073_course_goal_chosen
Revises: 0072_course_word_mastery
Create Date: 2026-09-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0073_course_goal_chosen"
down_revision: Union[str, None] = "0072_course_word_mastery"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "course_miniapp_profiles",
        sa.Column("goal_chosen_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("course_miniapp_profiles", "goal_chosen_at")
