"""separate an ad's type from where it is shown

Ilgari reklama QAYERDA chiqishini uning TURI belgilardi: `dars_yakuni` faqat
dars oxirida, `app` faqat Mini App ochilganda, qolgani esa mashq bo'limlarida.
Ya'ni admin joyni tanlay olmasdi — u faqat turini tanlardi va joy o'zidan
kelib chiqardi.

Endi ikkalasi ajratilgan. Joylar aynan ikkitaga qisqartirildi:

* `lesson_end`    — dars tugagach,
* `screen_center` — ekran markazida, qaysi bo'limda bo'lishidan qat'i nazar.

Mashq bo'limlaridagi start/middle/end uchligi butunlay olib tashlanadi.

Backfill mavjud reklamalarni bugungi ko'rinishiga eng yaqin joyga qo'yadi:
`dars_yakuni` → `lesson_end`, qolgani → `screen_center`.

Ikkinchi qadam — `course_lesson_access_policy` dagi `ads` rejimi. Uni
to'g'ridan-to'g'ri `subscription` ga o'tkazish deploy kunida aynan admin
saxiy bo'lishni tanlagan o'rnatishlarda barcha darslarni yopib qo'yardi.
Shuning uchun u 7 kunlik `free_until` ga aylantiriladi — yumshoq o'tish
oynasi, keyin o'zi `subscription` ga qaytadi.

Revision ID: 0078_course_ad_placements
Revises: 0077_user_pro_trial
Create Date: 2026-09-08
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0078_course_ad_placements"
down_revision: Union[str, None] = "0077_user_pro_trial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


POLICY_KEY = "course_lesson_access_policy"
ADS_TRANSITION_DAYS = 7


def upgrade() -> None:
    op.add_column(
        "course_ad_creatives",
        sa.Column(
            "placements",
            sa.String(length=64),
            server_default="screen_center",
            nullable=False,
        ),
    )
    op.execute(
        sa.text(
            "UPDATE course_ad_creatives SET placements = 'lesson_end' "
            "WHERE ad_type = 'dars_yakuni'"
        )
    )

    # Reklama bilan dars ochish olib tashlanmoqda. `ads` rejimidagi
    # o'rnatishlar bir kechada yopilib qolmasin.
    bind = op.get_bind()
    raw = bind.execute(
        sa.text("SELECT value FROM bot_settings WHERE key = :key"), {"key": POLICY_KEY}
    ).scalar_one_or_none()
    if not raw:
        return
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError):
        return
    if not isinstance(payload, dict) or payload.get("mode") != "ads":
        return

    payload["legacy_mode"] = "ads"
    payload["mode"] = "free_until"
    payload["free_until"] = (
        datetime.now(timezone.utc) + timedelta(days=ADS_TRANSITION_DAYS)
    ).isoformat()
    bind.execute(
        sa.text("UPDATE bot_settings SET value = :value WHERE key = :key"),
        {
            "key": POLICY_KEY,
            "value": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        },
    )


def downgrade() -> None:
    bind = op.get_bind()
    raw = bind.execute(
        sa.text("SELECT value FROM bot_settings WHERE key = :key"), {"key": POLICY_KEY}
    ).scalar_one_or_none()
    if raw:
        try:
            payload = json.loads(raw)
        except (TypeError, ValueError):
            payload = None
        if isinstance(payload, dict) and payload.pop("legacy_mode", None) == "ads":
            payload["mode"] = "ads"
            payload["free_until"] = None
            bind.execute(
                sa.text("UPDATE bot_settings SET value = :value WHERE key = :key"),
                {
                    "key": POLICY_KEY,
                    "value": json.dumps(
                        payload, ensure_ascii=False, separators=(",", ":")
                    ),
                },
            )

    op.drop_column("course_ad_creatives", "placements")
