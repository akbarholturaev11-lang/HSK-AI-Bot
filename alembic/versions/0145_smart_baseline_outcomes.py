"""Durable anonymous mature baseline lower bounds; no new delivery authority."""
from alembic import op
import sqlalchemy as sa

revision = "0145_smart_baseline_outcomes"
down_revision = "0144_smart_baseline"
branch_labels = None
depends_on = None

MEMBER = "smart_reminder_baseline_members"
TOTAL = "smart_reminder_baseline_totals"
MEMBER_COUNTS = ("observed_active_days", "observed_units", "observed_d7", "d1_overlap", "source_limited")
TOTAL_COUNTS = ("observed_accounts", "observed_active_days", "observed_units", "observed_d7_accounts",
                "d1_overlap_accounts", "source_limited_accounts")


def upgrade():
    with op.batch_alter_table(MEMBER) as b:
        b.add_column(sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True))
        for name in MEMBER_COUNTS:
            kind = sa.BigInteger() if name == "observed_units" else sa.Integer()
            b.add_column(sa.Column(name, kind, nullable=False, server_default="0"))
        b.create_check_constraint(op.f("ck_smart_reminder_baseline_members_outcomes"),
            "observed_active_days BETWEEN 0 AND 7 AND observed_units >= 0 "
            "AND observed_d7 IN (0, 1) AND d1_overlap IN (0, 1) AND source_limited IN (0, 1)")
        b.create_check_constraint(op.f("ck_smart_reminder_baseline_members_observation"),
            "observed_at IS NOT NULL OR (observed_active_days = 0 AND observed_units = 0 "
            "AND observed_d7 = 0 AND d1_overlap = 0 AND source_limited = 0)")
    with op.batch_alter_table(TOTAL) as b:
        for name in TOTAL_COUNTS:
            b.add_column(sa.Column(name, sa.BigInteger(), nullable=False, server_default="0"))
        b.create_check_constraint(op.f("ck_smart_reminder_baseline_totals_outcomes"),
            "observed_accounts BETWEEN 0 AND enrolled_accounts "
            "AND observed_active_days BETWEEN 0 AND observed_accounts * 7 AND observed_units >= 0 "
            "AND observed_d7_accounts BETWEEN 0 AND observed_accounts "
            "AND d1_overlap_accounts BETWEEN 0 AND observed_accounts "
            "AND source_limited_accounts BETWEEN 0 AND observed_accounts")


def downgrade():
    bind = op.get_bind()
    populated_totals = " OR ".join(f"{name} <> 0" for name in TOTAL_COUNTS)
    if (bind.execute(sa.text(f"SELECT 1 FROM {MEMBER} WHERE observed_at IS NOT NULL LIMIT 1")).first()
            or bind.execute(sa.text(f"SELECT 1 FROM {TOTAL} WHERE {populated_totals} LIMIT 1")).first()):
        raise RuntimeError("Refusing populated baseline outcomes downgrade; preserve observations")
    with op.batch_alter_table(TOTAL) as b:
        b.drop_constraint(op.f("ck_smart_reminder_baseline_totals_outcomes"), type_="check")
        for name in reversed(TOTAL_COUNTS):
            b.drop_column(name)
    with op.batch_alter_table(MEMBER) as b:
        b.drop_constraint(op.f("ck_smart_reminder_baseline_members_observation"), type_="check")
        b.drop_constraint(op.f("ck_smart_reminder_baseline_members_outcomes"), type_="check")
        for name in reversed(MEMBER_COUNTS):
            b.drop_column(name)
        b.drop_column("observed_at")
