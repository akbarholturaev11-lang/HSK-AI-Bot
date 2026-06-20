"""Merge all Alembic heads

Revision ID: 0045_merge_all_alembic_heads
Revises: 0043_add_course_pilot_events, 0044_add_daily_practice_fields, 0044_merge_payment_qr_and_release_feedback_heads
Create Date: 2026-06-20

"""

revision = "0045_merge_all_alembic_heads"
down_revision = (
    "0043_add_course_pilot_events",
    "0044_add_daily_practice_fields",
    "0044_merge_payment_qr_and_release_feedback_heads",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
