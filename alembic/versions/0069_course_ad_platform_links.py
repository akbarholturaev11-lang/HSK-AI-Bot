"""add manual platform link overrides to course ad creatives

App reklamasidagi platforma tugmalari (MacBook / Windows, keyinchalik
iPhone / Android) havolani IKKI manbadan oladi:

1. Reliz tizimidan avtomatik (`DesktopReleaseConfig.public_transfer_url`).
2. Adminning qo'lda kiritgan havolasidan — u bo'lsa avtomatikni bosib o'tadi.

Qo'lda kiritilgan havolalar shu ustunda JSON sifatida saqlanadi:
`{"macos": "https://...", "windows": "https://..."}`.
Bo'sh yoki NULL — faqat avtomatik havola ishlatiladi.

Bitta JSON ustun tanlandi (4 ta alohida ustun emas): iOS/Android qo'shilganda
yangi migratsiya kerak bo'lmaydi.

Revision ID: 0069_course_ad_platform_links
Revises: 0068_course_ad_app_type
Create Date: 2026-08-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0069_course_ad_platform_links"
down_revision: Union[str, None] = "0068_course_ad_app_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "course_ad_creatives",
        sa.Column("platform_links", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("course_ad_creatives", "platform_links")
