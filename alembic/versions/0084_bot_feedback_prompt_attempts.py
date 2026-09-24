"""limit repeated bot feedback prompts

Revision ID: 0084_bot_feedback_prompt_attempts
Revises: 0083_course_profile_identity
Create Date: 2026-09-24
"""

from alembic import op
import sqlalchemy as sa


revision = "0084_bot_feedback_prompt_attempts"
down_revision = "0083_course_profile_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "bot_feedbacks" not in set(inspector.get_table_names()):
        return
    columns = {item["name"] for item in inspector.get_columns("bot_feedbacks")}
    if "prompt_attempts" not in columns:
        op.add_column(
            "bot_feedbacks",
            sa.Column(
                "prompt_attempts",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "bot_feedbacks" not in set(inspector.get_table_names()):
        return
    columns = {item["name"] for item in inspector.get_columns("bot_feedbacks")}
    if "prompt_attempts" in columns:
        op.drop_column("bot_feedbacks", "prompt_attempts")
