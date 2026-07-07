"""restore missing course promo sections revision

Revision ID: 0064_course_promo_sections
Revises: 0063_course_ad_media_backup
Create Date: 2026-07-07
"""

from typing import Sequence, Union

revision: str = "0064_course_promo_sections"
down_revision: Union[str, None] = "0063_course_ad_media_backup"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # This revision already exists in production DB history.
    # Keep as bridge migration so Alembic can continue from it.
    pass


def downgrade() -> None:
    pass
