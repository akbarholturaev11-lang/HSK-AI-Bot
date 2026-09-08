"""widen the conversion funnel event names

Voronka jadvalidagi `event_name` CHECK cheklovi 11 ta nom bilan qotirilgan
edi. Trial hayot sikli (boshlandi / tugadi / to'lovga o'tdi), limitga urilish
va reklama ko'rsatkichlari o'sha ro'yxatga sig'maydi.

Nega YANGI jadval emas: loyihada allaqachon beshta event jadvali bor
(`course_miniapp_events`, `course_pilot_events`, `subscription_entry_events`,
`onboarding_tip_events`, `course_xp_events`). Oltinchisini qo'shish tahlilni
yana bir joyga bo'lib yuborardi.

Cheklov nomi ATAYLAB qattiq yozilmagan. `Base.metadata` da `ck` uchun
`ck_%(table_name)s_%(constraint_name)s` konventsiyasi bor va model unga
allaqachon `ck_...` bilan boshlanadigan nom beradi — natijada haqiqiy nom
ikki karra prefiksli bo'lib chiqadi. Qaysi nom bazada turganiga tayanish
o'rniga u ishga tushirish paytida topiladi.

Revision ID: 0076_conversion_funnel_events_v2
Revises: 0075_entitlement_shadow_events
Create Date: 2026-09-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0076_conversion_funnel_events_v2"
down_revision: Union[str, None] = "0075_entitlement_shadow_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE = "conversion_funnel_events"
#: Modeldagi nom. Konventsiya buni yana bir marta prefikslaydi.
DECLARED_NAME = "ck_conversion_funnel_events_event_name"

OLD_NAMES = (
    "course_cta_seen",
    "course_started",
    "lesson_started",
    "quiz_completed",
    "ai_explanation_seen",
    "homework_completed",
    "paywall_seen",
    "checkout_opened",
    "payment_screenshot_submitted",
    "payment_approved",
    "payment_rejected",
)

NEW_NAMES = OLD_NAMES + (
    "onboarding_completed",
    "plan_choice_seen",
    "trial_started",
    "trial_expired",
    "trial_converted",
    "limit_hit",
    "paywall_cta_clicked",
    "ad_shown",
    "ad_skipped",
)


def _condition(names: Sequence[str]) -> str:
    joined = ", ".join(f"'{name}'" for name in names)
    return f"event_name IN ({joined})"


def _existing_check_names(bind) -> list[str]:
    """Jadvaldagi CHECK cheklovlarining HAQIQIY nomlari."""
    if bind.dialect.name == "postgresql":
        rows = bind.execute(
            sa.text(
                "SELECT conname FROM pg_constraint "
                "WHERE conrelid = :table ::regclass AND contype = 'c'"
            ),
            {"table": TABLE},
        )
        return [row[0] for row in rows]
    inspector = sa.inspect(bind)
    return [
        item["name"]
        for item in inspector.get_check_constraints(TABLE)
        if item.get("name")
    ]


def _replace_constraint(names: Sequence[str]) -> None:
    bind = op.get_bind()

    if bind.dialect.name == "sqlite":
        # SQLite CHECK ni ALTER qila olmaydi va uning cheklov reflektsiyasi
        # ishonchsiz — `batch_alter_table` nomni konventsiya bilan qayta
        # prefikslab, mavjud bo'lmagan cheklovni qidiradi.
        #
        # Bu yerda uni majburlashning ma'nosi yo'q: SQLite faqat testlarda
        # ishlatiladi, testlar esa sxemani `Base.metadata.create_all` bilan
        # quradi va YANGI cheklovni allaqachon oladi. Zanjirning oldingi
        # qismi ham SQLite'da yurmaydi (`ALTER CONSTRAINT` qo'llanmaydi).
        return

    # Xom SQL ATAYLAB: `op.drop_constraint` va `op.create_check_constraint`
    # berilgan nomni `Base.metadata` konventsiyasi orqali o'tkazadi va uni
    # yana bir marta prefikslaydi — natijada mavjud bo'lmagan cheklov
    # qidiriladi. Bu yerda nom aynan bazadagidek qolishi kerak.
    for name in _existing_check_names(bind):
        op.execute(sa.text(f'ALTER TABLE {TABLE} DROP CONSTRAINT "{name}"'))
    op.execute(
        sa.text(
            f'ALTER TABLE {TABLE} ADD CONSTRAINT "{DECLARED_NAME}" '
            f"CHECK ({_condition(names)})"
        )
    )


def upgrade() -> None:
    _replace_constraint(NEW_NAMES)


def downgrade() -> None:
    # Eski CHECK yangi nomlarni rad etadi, shuning uchun avval o'sha qatorlar
    # olib tashlanadi. Ular analitik yozuv — yo'qolsa mahsulot buzilmaydi.
    added = tuple(name for name in NEW_NAMES if name not in OLD_NAMES)
    op.execute(
        sa.text(f"DELETE FROM {TABLE} WHERE event_name IN :names").bindparams(
            sa.bindparam("names", value=added, expanding=True)
        )
    )
    _replace_constraint(OLD_NAMES)
