"""Minimal job-independent reservation observations; no delivery authority."""
from alembic import op
import sqlalchemy as sa

revision = "0139_smart_reservation_analysis"
down_revision = "0138_smart_shadow_analysis"
branch_labels = None
depends_on = None

OLD = "'reserved', 'in_flight', 'provider_accepted', 'client_posted_unverified', 'confirmed_not_displayed', 'outcome_unknown', 'cancelled', 'expired', 'definite_failure', 'shadow_candidate', 'shadow_suppressed'"
NEW = "'shadow_reserved', 'shadow_refused'"
TABLE = "smart_reminder_reservation_observations"


def _monthly(values):
    with op.batch_alter_table("smart_reminder_analysis_monthly") as batch:
        name = op.f("ck_smart_reminder_analysis_monthly_stage")
        batch.drop_constraint(name, type_="check")
        batch.create_check_constraint(name, "stage IN (" + values + ")")


def upgrade():
    op.create_table(TABLE,
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("event_key", sa.String(64), nullable=False),
        sa.Column("stage", sa.String(32), nullable=False),
        sa.Column("reason_code", sa.String(64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id", "event_key", name=op.f("pk_" + TABLE)),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name=op.f("fk_" + TABLE + "_user_id_users")),
        sa.CheckConstraint("stage IN (" + NEW + ")", name=op.f("ck_" + TABLE + "_stage")),
        sa.CheckConstraint("length(event_key) = 64", name=op.f("ck_" + TABLE + "_event_key")),
        sa.CheckConstraint("expires_at > occurred_at", name=op.f("ck_" + TABLE + "_expiry")))
    op.create_index("ix_smart_reservation_expiry", TABLE, ["expires_at", "user_id", "event_key"])
    _monthly(OLD + ", " + NEW)


def downgrade():
    bind = op.get_bind()
    if (bind.execute(sa.text(f"SELECT 1 FROM {TABLE} LIMIT 1")).first() or
            bind.execute(sa.text("SELECT 1 FROM smart_reminder_analysis_monthly WHERE stage IN (" + NEW + ") LIMIT 1")).first()):
        raise RuntimeError("Refusing populated reservation analysis downgrade; preserve observed facts")
    _monthly(OLD)
    op.drop_index("ix_smart_reservation_expiry", table_name=TABLE)
    op.drop_table(TABLE)
