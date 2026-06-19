"""release feedback feature target and trial window

Revision ID: 0042_release_feedback_feature_trial
Revises: 0041_add_release_feedback
Create Date: 2026-06-19
"""

from alembic import op
import sqlalchemy as sa


revision = "0042_release_feedback_feature_trial"
down_revision = "0041_add_release_feedback"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "release_feedback_campaigns",
        sa.Column("feature_key", sa.String(length=32), nullable=False, server_default="general"),
    )
    op.alter_column("release_feedback_campaigns", "feature_key", server_default=None)


def downgrade() -> None:
    op.drop_column("release_feedback_campaigns", "feature_key")
