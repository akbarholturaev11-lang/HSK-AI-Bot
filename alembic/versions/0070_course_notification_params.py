"""store the template arguments behind a course notification

Bildirishnoma matni yuborilgan paytdagi tilda renderlanib bazaga qotib
qolardi. Foydalanuvchi keyin ilova tilini o'zgartirsa, feed eski tilda
ko'rinaverardi: tojikcha interfeysda o'zbekcha eslatma.

`params` — nullable JSON: shablon nomi va uning argumentlari
(masalan `{"template": "course_reminder_text", "vocab": 12, "dialogues": 3}`).
Shu bilan `payload()` matnni o'quvchi tilida qayta renderlay oladi.

Nullable, chunki eski qatorlarda bu ma'lumot yo'q — ular saqlangan matn
bilan qolaveradi va hech narsa buzilmaydi.

Revision ID: 0070_course_notification_params
Revises: 0069_course_ad_platform_links
Create Date: 2026-08-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0070_course_notification_params"
down_revision: Union[str, None] = "0069_course_ad_platform_links"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "course_user_notifications",
        sa.Column("params", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("course_user_notifications", "params")
