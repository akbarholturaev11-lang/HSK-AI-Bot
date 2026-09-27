"""Bind Android FCM tokens to native devices.

Revision ID: 0089_android_push_tokens
Revises: 0088_client_presence_promo
"""

from alembic import op
import sqlalchemy as sa


revision = "0089_android_push_tokens"
down_revision = "0088_client_presence_promo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "android_push_tokens",
        sa.Column("device_id", sa.String(length=36), nullable=False),
        sa.Column("token", sa.String(length=4096), nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["desktop_devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("device_id"),
        sa.UniqueConstraint("token"),
    )


def downgrade() -> None:
    op.drop_table("android_push_tokens")
