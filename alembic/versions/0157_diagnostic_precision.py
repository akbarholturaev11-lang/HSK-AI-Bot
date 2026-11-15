"""Privacy-safe debug evidence on diagnostic receipts (design D12).

Additive: four nullable columns holding only server-allowlisted values (an
exception name, a generic reason code, first-party source coordinates and the
deployed commit that verified them) plus two partial indexes for the Admin
"last reported sample" read. The downgrade refuses while any receipt still
holds debug evidence, as 0156 does for its own rows.
"""
from alembic import op
import sqlalchemy as sa

revision = "0157_diagnostic_precision"
down_revision = "0156_diagnostic_monitoring"
branch_labels = None
depends_on = None

TABLE = "diagnostic_receipts"
COLUMNS = ("error_name", "reason_code", "locations", "source_commit")
INDEXES = (
    ("ix_diagnostic_receipts_sample_location", "locations IS NOT NULL"),
    ("ix_diagnostic_receipts_sample_category", "category IS NOT NULL"),
)


def upgrade():
    op.add_column(TABLE, sa.Column("error_name", sa.String(32), nullable=True))
    op.add_column(TABLE, sa.Column("reason_code", sa.String(32), nullable=True))
    op.add_column(TABLE, sa.Column("locations", sa.JSON(none_as_null=True), nullable=True))
    op.add_column(TABLE, sa.Column("source_commit", sa.String(40), nullable=True))
    for name, predicate in INDEXES:
        op.create_index(name, TABLE, ["incident_id", "received_at", "id"],
                        postgresql_where=sa.text(predicate), sqlite_where=sa.text(predicate))


def downgrade():
    bind = op.get_bind()
    held = " OR ".join(f"{column} IS NOT NULL" for column in COLUMNS)
    if bind.execute(sa.text(f"SELECT EXISTS (SELECT 1 FROM {TABLE} WHERE {held})")).scalar_one():
        raise RuntimeError("Archive diagnostic debug evidence before downgrade")
    for name, _predicate in INDEXES:
        op.drop_index(name, table_name=TABLE)
    for column in reversed(COLUMNS):
        op.drop_column(TABLE, column)
