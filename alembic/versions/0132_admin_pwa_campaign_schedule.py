"""Indexed short-window due jobs; no session or payload lifetime extension."""
from alembic import op
import sqlalchemy as sa

revision = '0132_admin_pwa_campaign_schedule'
down_revision = '0131_admin_pwa_campaign_assets'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('admin_pwa_outbound_jobs', sa.Column('not_before', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_pwa_outbound_due', 'admin_pwa_outbound_jobs', ['status', 'not_before', 'id'])


def downgrade():
    if op.get_bind().execute(sa.text('SELECT EXISTS (SELECT 1 FROM admin_pwa_outbound_jobs WHERE not_before IS NOT NULL)')).scalar_one():
        raise RuntimeError('Archive scheduled job state before destructive downgrade')
    op.drop_index('ix_pwa_outbound_due', table_name='admin_pwa_outbound_jobs')
    op.drop_column('admin_pwa_outbound_jobs', 'not_before')
