"""Empty additive Smart storage; no backfill, enrollment or dispatch."""
from alembic import op
import sqlalchemy as sa

revision = "0133_smart_reminder_storage"
down_revision = "0132_admin_pwa_campaign_schedule"
branch_labels = None
depends_on = None

TABLES = (
    "smart_reminder_attempts", "smart_reminder_jobs",
    "smart_reminder_capabilities", "smart_reminder_consents",
    "smart_reminder_preferences",
)


def upgrade():
    op.create_table('smart_reminder_preferences',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('master_enabled', sa.Boolean(), nullable=True),
    sa.Column('revision', sa.Integer(), server_default='0', nullable=False),
    sa.Column('grant_epoch', sa.Integer(), server_default='0', nullable=False),
    sa.Column('migration_version', sa.Integer(), server_default='0', nullable=False),
    sa.Column('time_mode', sa.String(length=16), server_default='auto', nullable=False),
    sa.Column('manual_time_local', sa.Time(), nullable=True),
    sa.Column('timezone_name', sa.String(length=64), nullable=True),
    sa.Column('legacy_time_local', sa.Time(), nullable=True),
    sa.Column('legacy_offset_minutes', sa.Integer(), nullable=True),
    sa.Column('channel_mode', sa.String(length=16), server_default='auto', nullable=False),
    sa.Column('preferred_channel', sa.String(length=16), nullable=True),
    sa.Column('quiet_start', sa.Time(), nullable=True),
    sa.Column('quiet_end', sa.Time(), nullable=True),
    sa.Column('pause_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('action_source', sa.String(length=32), nullable=True),
    sa.Column('action_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.CheckConstraint("channel_mode != 'manual_locked' OR preferred_channel IS NOT NULL", name=op.f('ck_smart_reminder_preferences_manual_channel')),
    sa.CheckConstraint("channel_mode IN ('auto', 'manual_locked')", name=op.f('ck_smart_reminder_preferences_channel_mode')),
    sa.CheckConstraint("preferred_channel IS NULL OR preferred_channel IN ('telegram', 'android')", name=op.f('ck_smart_reminder_preferences_channel')),
    sa.CheckConstraint("time_mode != 'manual_locked' OR (manual_time_local IS NOT NULL AND timezone_name IS NOT NULL)", name=op.f('ck_smart_reminder_preferences_manual_time')),
    sa.CheckConstraint("time_mode IN ('auto', 'manual_locked')", name=op.f('ck_smart_reminder_preferences_time_mode')),
    sa.CheckConstraint('(quiet_start IS NULL AND quiet_end IS NULL) OR (quiet_start IS NOT NULL AND quiet_end IS NOT NULL)', name=op.f('ck_smart_reminder_preferences_quiet_pair')),
    sa.CheckConstraint('legacy_offset_minutes IS NULL OR legacy_offset_minutes BETWEEN -720 AND 840', name=op.f('ck_smart_reminder_preferences_legacy_offset')),
    sa.CheckConstraint('revision >= 0 AND grant_epoch >= 0 AND migration_version >= 0', name=op.f('ck_smart_reminder_preferences_versions')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_smart_reminder_preferences_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', name=op.f('pk_smart_reminder_preferences'))
    )
    op.create_table('smart_reminder_capabilities',
    sa.Column('device_id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('protocol_version', sa.Integer(), server_default='0', nullable=False),
    sa.Column('generation', sa.Integer(), server_default='0', nullable=False),
    sa.Column('autonomous_study_disabled', sa.Boolean(), nullable=True),
    sa.Column('study_notifications_allowed', sa.Boolean(), nullable=True),
    sa.Column('observed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint('(observed_at IS NULL AND expires_at IS NULL) OR (observed_at IS NOT NULL AND expires_at IS NOT NULL AND expires_at > observed_at)', name=op.f('ck_smart_reminder_capabilities_observation_window')),
    sa.CheckConstraint('protocol_version >= 0 AND generation >= 0', name=op.f('ck_smart_reminder_capabilities_versions')),
    sa.ForeignKeyConstraint(['device_id'], ['desktop_devices.id'], name=op.f('fk_smart_reminder_capabilities_device_id_desktop_devices'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_smart_reminder_capabilities_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('device_id', name=op.f('pk_smart_reminder_capabilities'))
    )
    op.create_index('ix_smart_capability_user', 'smart_reminder_capabilities', ['user_id'], unique=False)
    op.create_table('smart_reminder_consents',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('channel', sa.String(length=16), nullable=False),
    sa.Column('source_key', sa.String(length=96), nullable=False),
    sa.Column('device_id', sa.String(length=36), nullable=True),
    sa.Column('state', sa.String(length=16), server_default='unknown', nullable=False),
    sa.Column('source', sa.String(length=32), nullable=False),
    sa.Column('evidence_version', sa.Integer(), server_default='1', nullable=False),
    sa.Column('revision', sa.Integer(), server_default='0', nullable=False),
    sa.Column('action_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('observed_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.CheckConstraint("channel IN ('telegram', 'android')", name=op.f('ck_smart_reminder_consents_channel')),
    sa.CheckConstraint("device_id IS NULL OR channel = 'android'", name=op.f('ck_smart_reminder_consents_device_channel')),
    sa.CheckConstraint("state IN ('unknown', 'on', 'off')", name=op.f('ck_smart_reminder_consents_state')),
    sa.CheckConstraint('revision >= 0 AND evidence_version >= 1', name=op.f('ck_smart_reminder_consents_versions')),
    sa.ForeignKeyConstraint(['device_id'], ['desktop_devices.id'], name=op.f('fk_smart_reminder_consents_device_id_desktop_devices'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_smart_reminder_consents_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_smart_reminder_consents')),
    sa.UniqueConstraint('user_id', 'channel', 'source_key', name='uq_smart_consent_source')
    )
    op.create_index('ix_smart_consent_device', 'smart_reminder_consents', ['device_id'], unique=False)
    op.create_index('ix_smart_consent_user_channel', 'smart_reminder_consents', ['user_id', 'channel'], unique=False)
    op.create_table('smart_reminder_jobs',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('category', sa.String(length=16), server_default='study', nullable=False),
    sa.Column('local_day', sa.Date(), nullable=False),
    sa.Column('timezone_name', sa.String(length=64), nullable=False),
    sa.Column('day_start_utc', sa.DateTime(timezone=True), nullable=False),
    sa.Column('day_end_utc', sa.DateTime(timezone=True), nullable=False),
    sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('state', sa.String(length=24), server_default='shadow', nullable=False),
    sa.Column('preference_revision', sa.Integer(), server_default='0', nullable=False),
    sa.Column('grant_epoch', sa.Integer(), server_default='0', nullable=False),
    sa.Column('policy_version', sa.String(length=32), nullable=False),
    sa.Column('selected_channel', sa.String(length=16), nullable=True),
    sa.Column('selected_device_id', sa.String(length=36), nullable=True),
    sa.Column('lease_token', sa.String(length=36), nullable=True),
    sa.Column('lease_expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('reason_code', sa.String(length=64), nullable=True),
    sa.Column('course_key', sa.String(length=32), nullable=True),
    sa.Column('lesson_order', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.CheckConstraint("category = 'study'", name=op.f('ck_smart_reminder_jobs_category')),
    sa.CheckConstraint("selected_channel IS NULL OR selected_channel IN ('telegram', 'android')", name=op.f('ck_smart_reminder_jobs_channel')),
    sa.CheckConstraint("selected_device_id IS NULL OR (selected_channel IS NOT NULL AND selected_channel = 'android')", name=op.f('ck_smart_reminder_jobs_device_channel')),
    sa.CheckConstraint("state IN ('shadow', 'pending', 'claimed', 'provider_accepted', 'unknown', 'cancelled', 'expired', 'completed')", name=op.f('ck_smart_reminder_jobs_state')),
    sa.CheckConstraint('(lease_token IS NULL AND lease_expires_at IS NULL) OR (lease_token IS NOT NULL AND lease_expires_at IS NOT NULL)', name=op.f('ck_smart_reminder_jobs_lease_pair')),
    sa.CheckConstraint('day_start_utc <= scheduled_at AND scheduled_at < expires_at AND expires_at <= day_end_utc', name=op.f('ck_smart_reminder_jobs_day_window')),
    sa.CheckConstraint('grant_epoch >= 0 AND preference_revision >= 0', name=op.f('ck_smart_reminder_jobs_versions')),
    sa.CheckConstraint('lesson_order IS NULL OR lesson_order >= 1', name=op.f('ck_smart_reminder_jobs_lesson_order')),
    sa.ForeignKeyConstraint(['selected_device_id'], ['desktop_devices.id'], name=op.f('fk_smart_reminder_jobs_selected_device_id_desktop_devices'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_smart_reminder_jobs_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_smart_reminder_jobs')),
    sa.UniqueConstraint('user_id', 'local_day', 'category', name='uq_smart_job_account_day_category')
    )
    op.create_index('ix_smart_job_account_window', 'smart_reminder_jobs', ['user_id', 'day_start_utc', 'day_end_utc'], unique=False)
    op.create_index('ix_smart_job_device', 'smart_reminder_jobs', ['selected_device_id'], unique=False)
    op.create_index('ix_smart_job_due', 'smart_reminder_jobs', ['state', 'scheduled_at', 'expires_at', 'id'], unique=False)
    op.create_table('smart_reminder_attempts',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('job_id', sa.String(length=36), nullable=False),
    sa.Column('attempt_key', sa.String(length=64), nullable=False),
    sa.Column('channel', sa.String(length=16), nullable=False),
    sa.Column('device_id', sa.String(length=36), nullable=True),
    sa.Column('grant_epoch', sa.Integer(), server_default='0', nullable=False),
    sa.Column('state', sa.String(length=32), server_default='prepared', nullable=False),
    sa.Column('prepared_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('reason_code', sa.String(length=64), nullable=True),
    sa.CheckConstraint("channel IN ('telegram', 'android')", name=op.f('ck_smart_reminder_attempts_channel')),
    sa.CheckConstraint("device_id IS NULL OR channel = 'android'", name=op.f('ck_smart_reminder_attempts_device_channel')),
    sa.CheckConstraint("state IN ('prepared', 'in_flight', 'provider_accepted', 'client_posted_unverified', 'verified_shown', 'confirmed_not_displayed', 'definite_failure', 'unknown', 'cancelled')", name=op.f('ck_smart_reminder_attempts_state')),
    sa.CheckConstraint('expires_at > prepared_at', name=op.f('ck_smart_reminder_attempts_expiry')),
    sa.CheckConstraint('grant_epoch >= 0', name=op.f('ck_smart_reminder_attempts_epoch')),
    sa.ForeignKeyConstraint(['device_id'], ['desktop_devices.id'], name=op.f('fk_smart_reminder_attempts_device_id_desktop_devices'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['job_id'], ['smart_reminder_jobs.id'], name=op.f('fk_smart_reminder_attempts_job_id_smart_reminder_jobs'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_smart_reminder_attempts')),
    sa.UniqueConstraint('attempt_key', name='uq_smart_attempt_key')
    )
    op.create_index('ix_smart_attempt_device', 'smart_reminder_attempts', ['device_id'], unique=False)
    op.create_index('ix_smart_attempt_job', 'smart_reminder_attempts', ['job_id'], unique=False)


def downgrade():
    # Application rollback retains all consent/OFF/unknown-attempt state.
    # Check every table BEFORE dropping any object, including on SQLite DDL.
    connection = op.get_bind()
    for table in TABLES:
        if connection.execute(sa.text(f"SELECT 1 FROM {table} LIMIT 1")).first():
            raise RuntimeError("Archive Smart Reminder state before destructive downgrade")
    for table in TABLES:
        op.drop_table(table)
