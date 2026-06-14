"""add release feedback campaigns

Revision ID: 0041_add_release_feedback
Revises: 0040_add_ad_campaign_button_config
Create Date: 2026-06-14
"""

from alembic import op
import sqlalchemy as sa


revision = "0041_add_release_feedback"
down_revision = "0040_add_ad_campaign_button_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "release_feedback_campaigns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("message_text", sa.Text(), nullable=True),
        sa.Column("content_type", sa.String(length=16), nullable=False, server_default="text"),
        sa.Column("media_file_id", sa.String(length=512), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="scheduled"),
        sa.Column("send_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("target_languages", sa.String(length=40), nullable=True),
        sa.Column("status_filter", sa.String(length=32), nullable=True),
        sa.Column("level_filter", sa.String(length=32), nullable=True),
        sa.Column("mode_filter", sa.String(length=16), nullable=True),
        sa.Column("payment_status_filter", sa.String(length=16), nullable=True),
        sa.Column("payment_method_filter", sa.String(length=16), nullable=True),
        sa.Column("plan_filter", sa.String(length=32), nullable=True),
        sa.Column("discount_filter", sa.String(length=16), nullable=True),
        sa.Column("course_promo_filter", sa.String(length=16), nullable=True),
        sa.Column("activity_filter", sa.String(length=16), nullable=True),
        sa.Column("discount_percent", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("discount_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("trial_access_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("created_by_telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_release_feedback_campaigns")),
    )
    op.create_index(op.f("ix_release_feedback_campaigns_status"), "release_feedback_campaigns", ["status"], unique=False)
    op.create_index(op.f("ix_release_feedback_campaigns_send_at"), "release_feedback_campaigns", ["send_at"], unique=False)

    op.create_table(
        "release_feedback_deliveries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("user_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=True),
        sa.Column("error", sa.String(length=300), nullable=True),
        sa.Column("try_clicked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_granted_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["release_feedback_campaigns.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_release_feedback_deliveries")),
        sa.UniqueConstraint("campaign_id", "user_telegram_id", name="uq_release_feedback_deliveries_campaign_user"),
    )
    op.create_index(op.f("ix_release_feedback_deliveries_campaign_id"), "release_feedback_deliveries", ["campaign_id"], unique=False)
    op.create_index(op.f("ix_release_feedback_deliveries_user_telegram_id"), "release_feedback_deliveries", ["user_telegram_id"], unique=False)

    op.create_table(
        "release_feedback_responses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("user_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment_text", sa.Text(), nullable=True),
        sa.Column("attachment_file_id", sa.String(length=256), nullable=True),
        sa.Column("attachment_type", sa.String(length=16), nullable=True),
        sa.Column("discount_campaign_id", sa.Integer(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["release_feedback_campaigns.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_release_feedback_responses")),
        sa.UniqueConstraint("campaign_id", "user_telegram_id", name="uq_release_feedback_responses_campaign_user"),
    )
    op.create_index(op.f("ix_release_feedback_responses_campaign_id"), "release_feedback_responses", ["campaign_id"], unique=False)
    op.create_index(op.f("ix_release_feedback_responses_user_telegram_id"), "release_feedback_responses", ["user_telegram_id"], unique=False)
    op.create_index(op.f("ix_release_feedback_responses_discount_campaign_id"), "release_feedback_responses", ["discount_campaign_id"], unique=False)
    op.create_index(op.f("ix_release_feedback_responses_completed_at"), "release_feedback_responses", ["completed_at"], unique=False)

    op.alter_column("release_feedback_campaigns", "content_type", server_default=None)
    op.alter_column("release_feedback_campaigns", "status", server_default=None)
    op.alter_column("release_feedback_campaigns", "sent_count", server_default=None)
    op.alter_column("release_feedback_campaigns", "failed_count", server_default=None)
    op.alter_column("release_feedback_campaigns", "discount_percent", server_default=None)
    op.alter_column("release_feedback_campaigns", "discount_hours", server_default=None)
    op.alter_column("release_feedback_campaigns", "trial_access_minutes", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_release_feedback_responses_completed_at"), table_name="release_feedback_responses")
    op.drop_index(op.f("ix_release_feedback_responses_discount_campaign_id"), table_name="release_feedback_responses")
    op.drop_index(op.f("ix_release_feedback_responses_user_telegram_id"), table_name="release_feedback_responses")
    op.drop_index(op.f("ix_release_feedback_responses_campaign_id"), table_name="release_feedback_responses")
    op.drop_table("release_feedback_responses")

    op.drop_index(op.f("ix_release_feedback_deliveries_user_telegram_id"), table_name="release_feedback_deliveries")
    op.drop_index(op.f("ix_release_feedback_deliveries_campaign_id"), table_name="release_feedback_deliveries")
    op.drop_table("release_feedback_deliveries")

    op.drop_index(op.f("ix_release_feedback_campaigns_send_at"), table_name="release_feedback_campaigns")
    op.drop_index(op.f("ix_release_feedback_campaigns_status"), table_name="release_feedback_campaigns")
    op.drop_table("release_feedback_campaigns")
