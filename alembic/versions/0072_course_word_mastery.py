"""so'z darajasidagi o'zlashtirish — interval takrori uchun

Mashq bo'limlari (Ieroglif tanish, Talaffuz) so'zlarni TASODIFIY tanlardi:
`shuffle(pool).slice(0,10)`. Ya'ni o'quvchi bir so'zni o'nlab marta noto'g'ri
qilsa ham keyingi mashq baribir tasodifiy so'z berardi. Signal bor edi
(`course_mistakes` to'lardi), lekin uni hech kim o'qimasdi.

Bu jadval shu halqani yopadi: har bir (o'quvchi, ko'nikma, so'z) uchun
qachon qaytarish kerakligi saqlanadi.

NEGA ALOHIDA JADVAL — `course_mistakes` ni kengaytirish YETMAYDI:

1. `course_mistakes` da faqat XATOLAR bor. Interval takrori esa aynan
   TO'G'RI javoblarni rejalashtiradi (1 -> 3 -> 7 -> 21 kun). To'g'ri
   javoblarni xatolar jadvaliga yozish "Xatolarim" ekranini, kunlik reja
   zaiflik vektorini va `LearningSignals` ni buzardi.
2. `course_mistakes` qatorlari SAVOL bo'yicha kalitlanadi
   (`mistake_key` = `material_ref` yoki `category|prompt|correct_answer`),
   shuning uchun bitta ieroglif 4+ qatorga ega bo'lishi mumkin. Muddatni
   savolga emas, SO'ZGA bog'lash kerak.
3. `last_reviewed_at` bor, lekin u faqat YOZILADI — hech qayerda tanlash
   uchun o'qilmaydi, ya'ni kengaytiriladigan mexanizm yo'q.

USTUNLAR HAQIDA:

- `skill` kalit ichida: bir so'zni TANISH va TALAFFUZ QILISH boshqa-boshqa
  ko'nikmalar. Keyin voice/memorize shu ustunga yangi qiymat sifatida
  qo'shiladi va migratsiya kerak bo'lmaydi.
- `level` ATAYLAB YO'Q: band almashganda (hsk1 -> hsk2)
  `completed_lessons_count` nolga tushadi, lekin o'quvchi hsk1 so'zlarini
  unutmaydi. O'zlashtirish bandga bog'lanmasligi kerak.
- `due_on` — o'quvchining MAHALLIY kuni (`course_daily_window.local_day_key`),
  UTC emas. Aks holda UTC+5 dagi o'quvchiga so'z ertalab 05:00 da qaytardi.
- `correct_streak` yo'q: `box` ning o'zi cheklangan ketma-ketlik.

Revision ID: 0072_course_word_mastery
Revises: 0071_course_daily_plan
Create Date: 2026-09-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0072_course_word_mastery"
down_revision: Union[str, None] = "0071_course_daily_plan"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE = "course_word_mastery"


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("skill", sa.String(length=24), nullable=False),
        sa.Column("zh", sa.String(length=16), nullable=False),
        sa.Column("box", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("due_on", sa.Date(), nullable=False),
        sa.Column("correct_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wrong_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_result_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_course_word_mastery_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_course_word_mastery"),
        sa.UniqueConstraint(
            "user_id", "skill", "zh", name="uq_course_word_mastery_user_skill_zh"
        ),
        # CHECK nomlari QISQA: metadata konvensiyasi `ck_%(table_name)s_`
        # prefiksini o'zi qo'shadi (0071 da ham shunday).
        sa.CheckConstraint("box >= 0 AND box <= 4", name="box"),
        sa.CheckConstraint(
            "skill IN ('recognition', 'pronunciation')",
            name="skill",
        ),
    )
    op.create_index(
        "ix_course_word_mastery_user_id", TABLE, ["user_id"], unique=False
    )
    # Tanlashning issiq yo'li: "shu o'quvchining shu ko'nikmasi bo'yicha
    # bugun muddati kelgan so'zlar".
    op.create_index(
        "ix_course_word_mastery_due", TABLE, ["user_id", "skill", "due_on"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_course_word_mastery_due", table_name=TABLE)
    op.drop_index("ix_course_word_mastery_user_id", table_name=TABLE)
    op.drop_table(TABLE)
