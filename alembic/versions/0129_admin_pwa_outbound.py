"""Private bounded outbound jobs; no automatic retry after claiming a recipient."""
from alembic import op
import sqlalchemy as sa

revision='0129_admin_pwa_outbound'
down_revision='0128_admin_pwa_command_lookup'
branch_labels=None
depends_on=None


def upgrade():
    op.create_table('admin_pwa_outbound_jobs',
        sa.Column('id',sa.String(36),sa.ForeignKey('admin_pwa_command_audit.id',ondelete='RESTRICT'),primary_key=True),
        sa.Column('actor_user_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='CASCADE'),nullable=False),
        sa.Column('session_id',sa.String(36),sa.ForeignKey('admin_pwa_sessions.id',ondelete='CASCADE'),nullable=False),
        sa.Column('target_user_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='CASCADE')),
        sa.Column('kind',sa.String(16),nullable=False),sa.Column('status',sa.String(16),nullable=False),
        sa.Column('body_json',sa.Text(),nullable=False),sa.Column('audience_hash',sa.String(64),nullable=False),
        sa.Column('audience_count',sa.Integer(),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('expires_at',sa.DateTime(timezone=True),nullable=False),sa.Column('started_at',sa.DateTime(timezone=True)),
        sa.Column('run_token',sa.String(36)),
        sa.CheckConstraint("kind IN ('direct','broadcast','test')",name='ck_pwa_outbound_kind'),
        sa.CheckConstraint("status IN ('ready','running','complete','closed')",name='ck_pwa_outbound_job_status'),
        sa.CheckConstraint('audience_count BETWEEN 1 AND 1000',name='ck_pwa_outbound_audience'))
    op.create_index('ix_pwa_outbound_actor_created','admin_pwa_outbound_jobs',['actor_user_id','created_at','id'])
    op.create_index('ix_pwa_outbound_expires','admin_pwa_outbound_jobs',['expires_at'])
    op.create_index('ix_admin_pwa_outbound_jobs_session_id','admin_pwa_outbound_jobs',['session_id'])
    op.create_index('ix_admin_pwa_outbound_jobs_target_user_id','admin_pwa_outbound_jobs',['target_user_id'])
    op.create_table('admin_pwa_outbound_recipients',
        sa.Column('job_id',sa.String(36),sa.ForeignKey('admin_pwa_outbound_jobs.id',ondelete='CASCADE'),primary_key=True),
        sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='CASCADE'),primary_key=True),
        sa.Column('snapshot_hash',sa.String(64),nullable=False),sa.Column('language',sa.String(8),nullable=False),
        sa.Column('status',sa.String(16),nullable=False),sa.Column('attempted_at',sa.DateTime(timezone=True)),
        sa.Column('finished_at',sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('pending','attempting','attempted','uncertain','skipped')",name='ck_pwa_outbound_recipient_status'))
    op.create_index('ix_pwa_outbound_pending','admin_pwa_outbound_recipients',['job_id','status','user_id'])
    op.create_index('ix_pwa_outbound_target','admin_pwa_outbound_recipients',['user_id'])
    op.create_table('admin_pwa_outbound_events',
        sa.Column('id',sa.String(36),primary_key=True),sa.Column('job_id',sa.String(36),nullable=False),
        sa.Column('actor_user_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='SET NULL')),
        sa.Column('operation',sa.String(16),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.CheckConstraint("operation = 'stop'",name='ck_pwa_outbound_event_operation'))
    op.create_index('ix_admin_pwa_outbound_events_job_id','admin_pwa_outbound_events',['job_id'])
    op.create_index('ix_admin_pwa_outbound_events_actor_user_id','admin_pwa_outbound_events',['actor_user_id'])


def downgrade():
    for table in ('admin_pwa_outbound_jobs','admin_pwa_outbound_recipients','admin_pwa_outbound_events'):
        if op.get_bind().execute(sa.text(f'SELECT EXISTS (SELECT 1 FROM {table})')).scalar_one():
            raise RuntimeError('Archive private outbound state before destructive downgrade')
    op.drop_table('admin_pwa_outbound_events')
    op.drop_table('admin_pwa_outbound_recipients')
    op.drop_table('admin_pwa_outbound_jobs')
