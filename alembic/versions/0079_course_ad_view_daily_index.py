"""index ad views by learner, placement and time

Ekran markazidagi reklama kuniga ikki marta ko'rsatiladi va bu chegara
SERVERDA sanaladi — qurilmada emas. Ya'ni har ko'rsatishdan oldin
`course_ad_views` dan "shu o'quvchi, shu joyda, bugun nechta ko'rgan" so'raladi.

Bu indekssiz o'sha so'rov jadval o'sgan sari sekinlashadi va u eng issiq
yo'lda — Mini App har ochilganda.

Mavjud `ix_course_ad_views_user_lesson_placement` bu so'rovga to'g'ri
kelmaydi: u `lesson_order` ni ikkinchi ustun qilib oladi, bizga esa vaqt
kerak.

Revision ID: 0079_course_ad_view_daily_index
Revises: 0078_course_ad_placements
Create Date: 2026-09-08
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0079_course_ad_view_daily_index"
down_revision: Union[str, None] = "0078_course_ad_placements"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INDEX = "ix_course_ad_views_user_placement_created"


def upgrade() -> None:
    op.create_index(
        INDEX,
        "course_ad_views",
        ["user_telegram_id", "placement", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(INDEX, table_name="course_ad_views")
