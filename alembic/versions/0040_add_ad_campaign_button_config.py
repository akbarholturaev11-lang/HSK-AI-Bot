"""add ad campaign button config

Revision ID: 0040_add_ad_campaign_button_config
Revises: 0039_add_onboarding_tip_events
Create Date: 2026-06-13 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0040_add_ad_campaign_button_config"
down_revision: Union[str, None] = "0039_add_onboarding_tip_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ad_campaigns", sa.Column("button_config", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("ad_campaigns", "button_config")
