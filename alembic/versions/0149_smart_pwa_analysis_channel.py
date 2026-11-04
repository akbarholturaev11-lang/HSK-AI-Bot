"""Record the existing Smart Reminder PWA delivery channel in analysis."""
from alembic import op
import sqlalchemy as sa


revision = "0149_smart_pwa_analysis_channel"
down_revision = "0148_smart_reminder_pwa_channel"
branch_labels = None
depends_on = None


def _channel_constraint(table, definition):
    name = f"ck_{table}_channel"
    with op.batch_alter_table(table) as batch:
        batch.drop_constraint(name, type_="check")
        batch.create_check_constraint(name, definition)


def upgrade():
    for table in ("smart_reminder_analysis_events", "smart_reminder_analysis_monthly"):
        _channel_constraint(table, "channel IN ('none', 'telegram', 'android', 'pwa')")


def downgrade():
    bind = op.get_bind()
    for table in ("smart_reminder_analysis_events", "smart_reminder_analysis_monthly"):
        if bind.execute(sa.text(f"SELECT 1 FROM {table} WHERE channel = 'pwa' LIMIT 1")).first():
            raise RuntimeError("Refusing Smart PWA analysis downgrade with retained PWA evidence")
    for table in ("smart_reminder_analysis_events", "smart_reminder_analysis_monthly"):
        _channel_constraint(table, "channel IN ('none', 'telegram', 'android')")
