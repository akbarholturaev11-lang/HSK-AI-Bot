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


TABLE = "course_miniapp_profiles"
TARGET_CHECK = "streak_target_days IS NULL OR streak_target_days IN (7, 14, 30, 50)"


def upgrade():
    bind = op.get_bind()
    # Some isolated QA runners create the *latest* SQLAlchemy metadata then
    # replay Alembic from an older stamp. Tolerate already-present columns.
    # Production still receives each missing column as an additive ALTER.
    columns = {column["name"] for column in sa.inspect(bind).get_columns(TABLE)}
    if "goals_json" not in columns:
        op.add_column(TABLE, sa.Column("goals_json", sa.Text(), nullable=True))
    if "streak_target_days" not in columns:
        op.add_column(TABLE, sa.Column("streak_target_days", sa.Integer(), nullable=True))

    if bind.dialect.name != "sqlite":
        existing = sa.inspect(bind).get_check_constraints(TABLE)
        if not any("streak_target_days" in str(
                check.get("sqltext") or "").lower() for check in existing):
            op.create_check_constraint(
                op.f("ck_course_miniapp_profiles_streak_target_days"),
                TABLE, TARGET_CHECK,
            )


def downgrade():
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint(
            op.f("ck_course_miniapp_profiles_streak_target_days"),
            "course_miniapp_profiles", type_="check",
        )
    op.drop_column("course_miniapp_profiles", "streak_target_days")
    op.drop_column("course_miniapp_profiles", "goals_json")
