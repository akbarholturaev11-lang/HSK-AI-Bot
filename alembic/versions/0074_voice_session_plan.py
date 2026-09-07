"""add plan_json to voice practice sessions

AI Voice endi o'quvchiga moslashadi: sessiya boshlanishida uning maqsadi,
zaif tomoni, SRS bo'yicha takrorga tegishli so'zlari va qayta sinaladigan
o'tgan xatosi yig'iladi va shu ustunda MUZLATILADI.

Nega ustun, har navbatda qayta hisoblash emas: `_generate_reply` bitta
sessiyada 7 marta ishlaydi — qayta hisoblash so'rov narxini 7 ga ko'paytirar
va murabbiylik suhbat o'rtasida siljib ketardi. Bir xil naqsh allaqachon
`course_miniapp_profiles.daily_plan_json` da ishlatilgan.

Eski qatorlar `{}` bo'lib qoladi va prompt o'zgarishsiz eski holatiga
qaytadi — bu bir vaqtning o'zida rollback yo'li ham.

Revision ID: 0074_voice_session_plan
Revises: 0073_course_goal_chosen
Create Date: 2026-09-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0074_voice_session_plan"
down_revision: Union[str, None] = "0073_course_goal_chosen"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "voice_practice_sessions",
        sa.Column("plan_json", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("voice_practice_sessions", "plan_json")
