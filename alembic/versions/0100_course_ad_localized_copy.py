"""Store localized Tajik-source course ad copy for Russian and Uzbek.

Revision ID: 0100_course_ad_localized_copy
Revises: 0099_hsk30_live_n1_n3
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0100_course_ad_localized_copy"
down_revision: Union[str, None] = "0099_hsk30_live_n1_n3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "course_ad_creatives",
        sa.Column("localized_copy", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("course_ad_creatives", "localized_copy")
