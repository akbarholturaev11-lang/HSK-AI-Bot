"""Ad campaign course track and level targeting.

Revision ID: 0096_ad_campaign_course_target
Revises: 0095_course_track_states
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0096_ad_campaign_course_target"
down_revision: Union[str, None] = "0095_course_track_states"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ad_campaigns",
        sa.Column("target_track", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "ad_campaigns",
        sa.Column("target_level", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ad_campaigns", "target_level")
    op.drop_column("ad_campaigns", "target_track")
