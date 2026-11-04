"""Allow one existing Smart study job to select its eligible PWA endpoint.

Revision ID: 0148_smart_reminder_pwa_channel
Revises: 0147_learner_pwa_push
"""
from alembic import op
import sqlalchemy as sa


revision = "0148_smart_reminder_pwa_channel"
down_revision = "0147_learner_pwa_push"
branch_labels = None
depends_on = None


def _channel_constraint(table, new):
    name = f"ck_{table}_channel"
    with op.batch_alter_table(table) as batch:
        batch.drop_constraint(name, type_="check")
        batch.create_check_constraint(name, new)


def _device_constraint(table, new):
    name = f"ck_{table}_device_channel"
    with op.batch_alter_table(table) as batch:
        batch.drop_constraint(name, type_="check")
        batch.create_check_constraint(name, new)


def upgrade():
    _channel_constraint(
        "smart_reminder_jobs",
        "selected_channel IS NULL OR selected_channel IN ('telegram', 'android', 'pwa')",
    )
    _device_constraint(
        "smart_reminder_jobs",
        "selected_device_id IS NULL OR (selected_channel IS NOT NULL AND selected_channel IN ('android', 'pwa'))",
    )
    _channel_constraint(
        "smart_reminder_attempts",
        "channel IN ('telegram', 'android', 'pwa')",
    )
    _device_constraint(
        "smart_reminder_attempts",
        "device_id IS NULL OR channel IN ('android', 'pwa')",
    )


def downgrade():
    bind = op.get_bind()
    # The base Smart Reminder migration refuses to drop any populated state.
    # Check every table before SQLite batch DDL: rebuilding a referenced jobs
    # table can otherwise cascade-delete attempts before the base guard runs.
    for table in ("smart_reminder_preferences", "smart_reminder_consents",
                  "smart_reminder_capabilities", "smart_reminder_jobs",
                  "smart_reminder_attempts"):
        if bind.execute(sa.text(f"SELECT 1 FROM {table} LIMIT 1")).first():
            raise RuntimeError("Archive Smart Reminder state before PWA channel downgrade")
    _channel_constraint(
        "smart_reminder_jobs",
        "selected_channel IS NULL OR selected_channel IN ('telegram', 'android')",
    )
    _device_constraint(
        "smart_reminder_jobs",
        "selected_device_id IS NULL OR (selected_channel IS NOT NULL AND selected_channel = 'android')",
    )
    _channel_constraint(
        "smart_reminder_attempts",
        "channel IN ('telegram', 'android')",
    )
    _device_constraint(
        "smart_reminder_attempts",
        "device_id IS NULL OR channel = 'android'",
    )
