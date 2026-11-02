"""Explicit shadow decision stages, preserving all delivery analysis."""
from alembic import op
import sqlalchemy as sa

revision = "0138_smart_shadow_analysis"
down_revision = "0137_smart_analysis"
branch_labels = None
depends_on = None

OLD = "'reserved', 'in_flight', 'provider_accepted', 'client_posted_unverified', 'confirmed_not_displayed', 'outcome_unknown', 'cancelled', 'expired', 'definite_failure'"
TABLES = ("smart_reminder_analysis_events", "smart_reminder_analysis_monthly")


def _stages(values):
    for table in TABLES:
        with op.batch_alter_table(table) as batch:
            name = op.f("ck_" + table + "_stage")
            batch.drop_constraint(name, type_="check")
            batch.create_check_constraint(name, "stage IN (" + values + ")")


def upgrade():
    _stages(OLD + ", 'shadow_candidate', 'shadow_suppressed'")


def downgrade():
    for table in TABLES:
        if op.get_bind().execute(sa.text(
                f"SELECT 1 FROM {table} WHERE stage IN ('shadow_candidate', 'shadow_suppressed') LIMIT 1")).first():
            raise RuntimeError("Refusing populated shadow analysis downgrade; preserve observed facts")
    _stages(OLD)
