"""Durable deletion requests independent of Telegram identity.

Revision ID: 0101_account_deletion_requests
Revises: 0100_course_ad_localized_copy
"""
from alembic import op
import sqlalchemy as sa

revision = "0101_account_deletion_requests"
down_revision = "0100_course_ad_localized_copy"
branch_labels = None
depends_on = None


def upgrade():
    # Railway init_db/create_all may already have created this new table.
    if sa.inspect(op.get_bind()).has_table("account_deletion_requests"):
        return
    op.create_table(
        "account_deletion_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("active_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), unique=True),
        sa.Column("provider", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("secret_hash", sa.String(64), nullable=False),
        sa.Column("browser_hash", sa.String(64)),
        sa.Column("client_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("requested_at", sa.DateTime(timezone=True)),
        sa.Column("due_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    for column in ("user_id", "status", "client_hash", "created_at", "due_at"):
        op.create_index(f"ix_account_deletion_requests_{column}", "account_deletion_requests", [column])


def downgrade():
    op.drop_table("account_deletion_requests")
