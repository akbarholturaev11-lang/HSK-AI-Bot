"""course mini app: preferensiya fokusi va kunlik reja holati

Daily Plan uchun to'rtta nullable ustun. Yangi jadval ataylab qurilmadi —
qarang ARCHITECTURE_DECISION.md.

`preferred_focus` — o'quvchi ONBOARDINGDA "nimaga ko'proq urg'u beraylik"
degan savolga bergan javobi. Bu o'z-o'zini tashxis emas, PREFERENSIYA: reja
qurishda faqat BOSHLANG'ICH taxmin (prior) sifatida ishlatiladi va real
natijalar to'plangach ta'siri so'nadi. Kuzatilgan zaiflik (`course_mistakes`)
undan ustun turadi. NULL = hali so'ralmagan; 'none' = "farqi yo'q" deb javob
bergan (ikkalasi ham prior=0, lekin onboarding oqimi uchun farqi bor).

`daily_goal_xp` — kunlik XP maqsadi. Ilgari bu Mini App ichida oddiy JS
o'zgaruvchi edi (`dailyGoal=50`) va hech qayerga saqlanmasdi: foydalanuvchi
profilda tanlagan maqsad ilova qayta ochilganda yo'qolardi. Endi server
saqlaydi. NULL bo'lsa `daily_minutes` dan chiqariladi.

`daily_plan_key` / `daily_plan_json` — kun barqarorligi. Reja kuniga ATIGI
bir marta quriladi va uning TASK IDENTITY'si muzlatiladi; bajarilgan/ochiq
holati esa har so'rovda qayta hisoblanadi (saqlanmaydi). Busiz ertalab
ko'rilgan reja kechqurun boshqa tasklarga almashib qolardi, chunki
`course_mistakes` upsert jadvali — zaiflikning kun boshidagi holatini
qayta tiklab bo'lmaydi.

Kalit formati: "v1:<level>:<mahalliy sana>", masalan "v1:hsk1:2026-09-05".
- `v1` — sxema versiyasi: task shakli o'zgarsa kalit mos kelmaydi va eski
  JSON avtomatik bekor bo'ladi (migratsiya ham, crash ham kerak emas);
- `<level>` — band almashganda (hsk1 -> hsk2) reja qayta quriladi, aks holda
  mavjud bo'lmagan qism raqamlari qolib ketardi;
- sana — o'quvchining MAHALLIY kuni (`course_daily_window.local_day_key`).

Hammasi nullable: eski qatorlar o'zgarishsiz qoladi va birinchi ochilishda
o'zi to'ladi.

Revision ID: 0071_course_daily_plan
Revises: 0070_course_notification_params
Create Date: 2026-09-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0071_course_daily_plan"
down_revision: Union[str, None] = "0070_course_notification_params"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PROFILE_TABLE = "course_miniapp_profiles"
# Metadata naming convention "ck_%(table_name)s_" prefiksini o'zi qo'shadi,
# shuning uchun bu yerda faqat qisqa nom turadi. Bazadagi yakuniy nom:
# ck_course_miniapp_profiles_preferred_focus — modeldagi nom bilan bir xil.
PREFERRED_FOCUS_CONSTRAINT = "preferred_focus"
PREFERRED_FOCUS_VALUES = "'speaking', 'listening', 'vocabulary', 'grammar', 'none'"


def upgrade() -> None:
    op.add_column(
        PROFILE_TABLE,
        sa.Column("preferred_focus", sa.String(length=24), nullable=True),
    )
    op.add_column(
        PROFILE_TABLE,
        sa.Column("daily_goal_xp", sa.Integer(), nullable=True),
    )
    op.add_column(
        PROFILE_TABLE,
        sa.Column("daily_plan_key", sa.String(length=48), nullable=True),
    )
    op.add_column(
        PROFILE_TABLE,
        sa.Column("daily_plan_json", sa.Text(), nullable=True),
    )
    # NULL qiymat CHECK'dan o'tadi (NULL -> NULL), ya'ni "hali so'ralmagan"
    # holati cheklovni buzmaydi.
    op.create_check_constraint(
        PREFERRED_FOCUS_CONSTRAINT,
        PROFILE_TABLE,
        f"preferred_focus IN ({PREFERRED_FOCUS_VALUES})",
    )


def downgrade() -> None:
    op.drop_constraint(PREFERRED_FOCUS_CONSTRAINT, PROFILE_TABLE, type_="check")
    op.drop_column(PROFILE_TABLE, "daily_plan_json")
    op.drop_column(PROFILE_TABLE, "daily_plan_key")
    op.drop_column(PROFILE_TABLE, "daily_goal_xp")
    op.drop_column(PROFILE_TABLE, "preferred_focus")
