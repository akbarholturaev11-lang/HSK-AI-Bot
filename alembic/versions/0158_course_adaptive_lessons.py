"""Course adaptive lessons (UIUX-007): per-skill review state and lesson plans.

Additive only:
- `course_mistake_targets.adaptive_state_json` (NOT NULL, server default `{}`)
  and nullable `adaptive_due_on` with a `(user_id, adaptive_due_on)` index.
  PostgreSQL adds both without a table rewrite; no backfill — the service
  derives state lazily from existing verified mistakes.
- new `course_adaptive_plans` table (server snapshot of personal questions).

Downgrade drops only these objects. Lesson progress, attempts, XP, Xatolarim
progress and word mastery are untouched in both directions.
"""

from alembic import op
import sqlalchemy as sa

revision = "0158_course_adaptive_lessons"
down_revision = "0157_diagnostic_precision"
branch_labels = None
depends_on = None

TARGETS = "course_mistake_targets"
TARGET_INDEX = "ix_course_mistake_targets_user_adaptive_due"
PLANS = "course_adaptive_plans"
PLAN_INDEX = "ix_course_adaptive_plans_user_day"


def upgrade():
    bind = op.get_bind()
    # Isolated QA runners may create the latest metadata, then replay from an
    # older stamp. Production receives the missing columns and index.
    columns = {column["name"] for column in sa.inspect(bind).get_columns(TARGETS)}
    if "adaptive_state_json" not in columns:
        op.add_column(
            TARGETS,
            sa.Column("adaptive_state_json", sa.Text(), nullable=False, server_default="{}"),
        )
    if "adaptive_due_on" not in columns:
        op.add_column(TARGETS, sa.Column("adaptive_due_on", sa.Date(), nullable=True))
    if TARGET_INDEX not in {index["name"] for index in sa.inspect(bind).get_indexes(TARGETS)}:
        op.create_index(TARGET_INDEX, TARGETS, ["user_id", "adaptive_due_on"])

    op.create_table(
        PLANS,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("plan_key", sa.String(length=96), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("lesson_order", sa.Integer(), nullable=False),
        sa.Column("local_day", sa.Date(), nullable=False),
        sa.Column("contract_version", sa.SmallInteger(), nullable=False),
        sa.Column("language", sa.String(length=8), nullable=False),
        sa.Column("items_json", sa.Text(), nullable=False),
        sa.Column("answers_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_course_adaptive_plans_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_course_adaptive_plans")),
        sa.UniqueConstraint("user_id", "plan_key", name="uq_course_adaptive_plans_user_key"),
    )
    op.create_index(PLAN_INDEX, PLANS, ["user_id", "local_day"])


def downgrade():
    op.drop_index(PLAN_INDEX, table_name=PLANS)
    op.drop_table(PLANS)
    op.drop_index(TARGET_INDEX, table_name=TARGETS)
    op.drop_column(TARGETS, "adaptive_due_on")
    op.drop_column(TARGETS, "adaptive_state_json")
