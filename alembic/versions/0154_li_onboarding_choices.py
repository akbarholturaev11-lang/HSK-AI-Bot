"""Add optional Li onboarding goal selection and aspirational streak target.

No historical progress, XP or legacy scalar goal is rewritten. Old clients
continue using the scalar goal; NULL goals_json means [goal] on reads.
"""
from alembic import op
import sqlalchemy as sa

revision = "0154_li_onboarding_choices"
down_revision = "0153_pwa_inline_funnel"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("course_miniapp_profiles",
                  sa.Column("goals_json", sa.Text(), nullable=True))
    op.add_column("course_miniapp_profiles",
                  sa.Column("streak_target_days", sa.Integer(), nullable=True))
    if op.get_bind().dialect.name != "sqlite":
        op.create_check_constraint(
            "ck_course_miniapp_profiles_streak_target_days",
            "course_miniapp_profiles",
            "streak_target_days IS NULL OR streak_target_days IN (7, 14, 30, 50)",
        )


def downgrade():
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint(
            "ck_course_miniapp_profiles_streak_target_days",
            "course_miniapp_profiles", type_="check",
        )
    op.drop_column("course_miniapp_profiles", "streak_target_days")
    op.drop_column("course_miniapp_profiles", "goals_json")
