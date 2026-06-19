"""restore release feedback trial to 30 minutes

Revision ID: 0043_restore_release_feedback_trial_30_minutes
Revises: 0042_release_feedback_feature_trial
Create Date: 2026-06-19
"""

from alembic import op


revision = "0043_restore_release_feedback_trial_30_minutes"
down_revision = "0042_release_feedback_feature_trial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE release_feedback_campaigns "
        "SET trial_access_minutes = 30 "
        "WHERE trial_access_minutes = 1440"
    )


def downgrade() -> None:
    pass
