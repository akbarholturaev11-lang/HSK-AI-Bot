"""Merge payment QR and release feedback migration heads

Revision ID: 0044_merge_payment_qr_and_release_feedback_heads
Revises: 0036_add_payment_qr_codes, 0043_restore_release_feedback_trial_30_minutes
Create Date: 2026-06-20

"""
from typing import Sequence, Union


revision = "0044_merge_payment_qr_and_release_feedback_heads"
down_revision = (
    "0036_add_payment_qr_codes",
    "0043_restore_release_feedback_trial_30_minutes",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
