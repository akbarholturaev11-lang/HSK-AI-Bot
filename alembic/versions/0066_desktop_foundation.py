"""desktop auth foundation

Revision ID: 0066_desktop_foundation
Revises: 0065_course_progress_parts
Create Date: 2026-07-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0066_desktop_foundation"
down_revision: Union[str, None] = "0065_course_progress_parts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "desktop_link_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("display_code_hash", sa.String(length=64), nullable=False),
        sa.Column("polling_secret_hash", sa.String(length=64), nullable=False),
        sa.Column("installation_key_hash", sa.String(length=64), nullable=False),
        sa.Column("platform", sa.String(length=16), nullable=False),
        sa.Column("app_version", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("approved_user_id", sa.Integer(), nullable=True),
        sa.Column("approved_telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["approved_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_desktop_link_requests_display_code_hash",
        "desktop_link_requests",
        ["display_code_hash"],
        unique=True,
    )
    op.create_index(
        "ix_desktop_link_requests_polling_secret_hash",
        "desktop_link_requests",
        ["polling_secret_hash"],
        unique=True,
    )
    op.create_index(
        "ix_desktop_link_requests_status",
        "desktop_link_requests",
        ["status"],
    )
    op.create_index(
        "ix_desktop_link_requests_approved_user_id",
        "desktop_link_requests",
        ["approved_user_id"],
    )
    op.create_index(
        "ix_desktop_link_requests_approved_telegram_id",
        "desktop_link_requests",
        ["approved_telegram_id"],
    )
    op.create_index(
        "ix_desktop_link_requests_expires_at",
        "desktop_link_requests",
        ["expires_at"],
    )
    op.create_index(
        "ix_desktop_link_requests_created_at",
        "desktop_link_requests",
        ["created_at"],
    )

    op.create_table(
        "desktop_devices",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("installation_key_hash", sa.String(length=64), nullable=False),
        sa.Column("platform", sa.String(length=16), nullable=False),
        sa.Column("app_version", sa.String(length=40), nullable=False),
        sa.Column("first_open_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_desktop_devices_user_id", "desktop_devices", ["user_id"])
    op.create_index(
        "ix_desktop_devices_telegram_id", "desktop_devices", ["telegram_id"]
    )
    op.create_index(
        "ix_desktop_devices_installation_key_hash",
        "desktop_devices",
        ["installation_key_hash"],
        unique=True,
    )
    op.create_index(
        "ix_desktop_devices_revoked_at", "desktop_devices", ["revoked_at"]
    )

    op.create_table(
        "desktop_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("device_id", sa.String(length=36), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=64), nullable=False),
        sa.Column("previous_refresh_token_hash", sa.String(length=64), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["device_id"], ["desktop_devices.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_desktop_sessions_device_id", "desktop_sessions", ["device_id"]
    )
    op.create_index(
        "ix_desktop_sessions_refresh_token_hash",
        "desktop_sessions",
        ["refresh_token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_desktop_sessions_previous_refresh_token_hash",
        "desktop_sessions",
        ["previous_refresh_token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_desktop_sessions_expires_at", "desktop_sessions", ["expires_at"]
    )
    op.create_index(
        "ix_desktop_sessions_revoked_at", "desktop_sessions", ["revoked_at"]
    )


def downgrade() -> None:
    op.drop_table("desktop_sessions")
    op.drop_table("desktop_devices")
    op.drop_table("desktop_link_requests")
