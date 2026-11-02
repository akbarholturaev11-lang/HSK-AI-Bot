"""Explicit temporal verified-study stages, never causal attribution."""
from alembic import op
import sqlalchemy as sa

revision = "0141_smart_study_analysis"
down_revision = "0140_smart_open_analysis"
branch_labels = None
depends_on = None

OLD = "'reserved', 'in_flight', 'provider_accepted', 'client_posted_unverified', 'confirmed_not_displayed', 'outcome_unknown', 'cancelled', 'expired', 'definite_failure', 'shadow_candidate', 'shadow_suppressed', 'client_reported_open'"
NEW = "'verified_study_after_attempt', 'verified_study_after_report'"
TABLES = {"smart_reminder_analysis_events": OLD,
          "smart_reminder_analysis_monthly": OLD + ", 'shadow_reserved', 'shadow_refused'"}


def _stages(table, values):
    with op.batch_alter_table(table) as batch:
        name = op.f("ck_" + table + "_stage")
        batch.drop_constraint(name, type_="check")
        batch.create_check_constraint(name, "stage IN (" + values + ")")


def upgrade():
    for table, old in TABLES.items():
        _stages(table, old + ", " + NEW)


def downgrade():
    for table in TABLES:
        if op.get_bind().execute(sa.text(f"SELECT 1 FROM {table} WHERE stage IN (" + NEW + ") LIMIT 1")).first():
            raise RuntimeError("Refusing populated study analysis downgrade; preserve observed facts")
    for table, old in TABLES.items():
        _stages(table, old)
