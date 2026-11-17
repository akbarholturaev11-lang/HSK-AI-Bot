"""Record the route-set client of each subscription entry (next-stage R3).

Additive and nullable: PostgreSQL adds the column without rewriting the
table. No backfill; earlier rows keep NULL and stay Overall-only.
"""
from alembic import op
import sqlalchemy as sa

revision = "0155_subscription_entry_client"
down_revision = "0154_li_onboarding_choices"
branch_labels = None
depends_on = None

TABLE = "subscription_entry_events"
INDEX = "ix_subscription_entry_events_client_created_at"


def upgrade():
    bind = op.get_bind()
    # Isolated QA runners may create the latest metadata, then replay from an
    # older stamp. Production receives the missing column and index.
    inspector = sa.inspect(bind)
    if "client" not in {column["name"] for column in inspector.get_columns(TABLE)}:
        op.add_column(TABLE, sa.Column("client", sa.String(length=16), nullable=True))
    if INDEX not in {index["name"] for index in sa.inspect(bind).get_indexes(TABLE)}:
        op.create_index(INDEX, TABLE, ["client", "created_at"])


def downgrade():
    op.drop_index(INDEX, table_name=TABLE)
    op.drop_column(TABLE, "client")
