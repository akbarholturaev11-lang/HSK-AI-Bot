"""Automatic diagnostic incidents and receipts; `diagnostic` Inbox source.

Additive (design D2). Content-free tables: catalog codes, versions, times and
counts only. The downgrade refuses while diagnostic triage or outbox rows
exist, as 0127 does for `technical`.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.schema import conv

revision = "0156_diagnostic_monitoring"
down_revision = "0155_subscription_entry_client"
branch_labels = None
depends_on = None

OLD_SOURCES = "source IN ('bot', 'release', 'android', 'payment', 'technical')"
NEW_SOURCES = "source IN ('bot', 'release', 'android', 'payment', 'technical', 'diagnostic')"
CHECKS = (
    ("admin_pwa_push_outbox", "ck_admin_pwa_push_outbox_source"),
    ("admin_pwa_inbox_triage", "ck_admin_pwa_inbox_triage_source"),
    ("admin_pwa_inbox_triage_audit", "ck_admin_pwa_inbox_audit_source"),
)


def upgrade():
    op.create_table(
        "diagnostic_incidents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("platform", sa.String(16), nullable=False),
        sa.Column("feature_code", sa.String(40), nullable=False),
        sa.Column("failure_code", sa.String(40), nullable=False),
        sa.Column("site_code", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("occurrence_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("refused_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("first_version", sa.String(40), nullable=True),
        sa.Column("last_version", sa.String(40), nullable=True),
        sa.Column("last_build", sa.BigInteger(), nullable=True),
        sa.Column("resolved_version", sa.String(40), nullable=True),
        sa.Column("resolved_build", sa.BigInteger(), nullable=True),
        sa.Column("reopened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reopened_version", sa.String(40), nullable=True),
        sa.Column("alert_epoch", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_alerted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_alert_reason", sa.String(16), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_diagnostic_incidents"),
        sa.UniqueConstraint("fingerprint", name="uq_diagnostic_incidents_fingerprint"),
        sa.CheckConstraint("platform IN ('android', 'iphone_pwa', 'telegram', 'server')",
                           name="ck_diagnostic_incidents_platform"),
        sa.CheckConstraint("severity IN ('normal', 'high', 'critical')", name="ck_diagnostic_incidents_severity"),
        sa.CheckConstraint("occurrence_count >= 0 AND refused_count >= 0", name="ck_diagnostic_incidents_counts"),
        sa.CheckConstraint("last_alert_reason IS NULL OR last_alert_reason IN ('new', 'escalated', 'reopened')",
                           name="ck_diagnostic_incidents_alert_reason"),
    )
    op.create_index("ix_diagnostic_incidents_last_seen", "diagnostic_incidents", ["last_seen_at", "id"])

    op.create_table(
        "diagnostic_receipts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("event_id", sa.String(36), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("client_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("client_time_untrusted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("app_version", sa.String(40), nullable=True),
        sa.Column("build", sa.BigInteger(), nullable=True),
        sa.Column("channel", sa.String(8), nullable=True),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("category", sa.String(24), nullable=True),
        sa.Column("occurrences", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("id", name="pk_diagnostic_receipts"),
        sa.ForeignKeyConstraint(["incident_id"], ["diagnostic_incidents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "event_id", name="uq_diagnostic_receipts_owner_event"),
        sa.CheckConstraint("channel IS NULL OR channel IN ('play', 'direct')", name="ck_diagnostic_receipts_channel"),
        sa.CheckConstraint("outcome IN ('failed', 'recovered')", name="ck_diagnostic_receipts_outcome"),
        sa.CheckConstraint("occurrences BETWEEN 1 AND 10000", name="ck_diagnostic_receipts_occurrences"),
    )
    op.create_index("uq_diagnostic_receipts_server_event", "diagnostic_receipts", ["event_id"], unique=True,
                    postgresql_where=sa.text("user_id IS NULL"), sqlite_where=sa.text("user_id IS NULL"))
    op.create_index("ix_diagnostic_receipts_owner_received", "diagnostic_receipts", ["user_id", "received_at"])
    op.create_index("ix_diagnostic_receipts_incident_received", "diagnostic_receipts",
                    ["incident_id", "received_at"])
    op.create_index("ix_diagnostic_receipts_received", "diagnostic_receipts", ["received_at"])

    for table, name in CHECKS:
        _replace_source_check(table, name, NEW_SOURCES)
    op.add_column("admin_pwa_push_outbox", sa.Column("diagnostic_kind", sa.String(16), nullable=True))
    op.create_check_constraint(op.f("ck_admin_pwa_outbox_diagnostic_kind"), "admin_pwa_push_outbox",
        "(source = 'diagnostic' AND diagnostic_kind IS NOT NULL AND diagnostic_kind IN ('new','escalated','reopened')) OR "
        "(source <> 'diagnostic' AND diagnostic_kind IS NULL)")
    op.create_index("ix_admin_pwa_outbox_diag_cap", "admin_pwa_push_outbox",
                    ["source", "diagnostic_kind", "created_at"])


def downgrade():
    bind = op.get_bind()
    for table in ("diagnostic_receipts", "diagnostic_incidents"):
        if bind.execute(sa.text(f"SELECT EXISTS (SELECT 1 FROM {table})")).scalar_one():
            raise RuntimeError(f"Archive diagnostic rows in {table} before downgrade")
    for table, _name in CHECKS:
        if bind.execute(sa.text(
                f"SELECT EXISTS (SELECT 1 FROM {table} WHERE source = 'diagnostic')")).scalar_one():
            raise RuntimeError(f"Archive diagnostic rows in {table} before downgrade")
    for table, name in CHECKS:
        _replace_source_check(table, name, OLD_SOURCES, restore=True)
    op.drop_index("ix_admin_pwa_outbox_diag_cap", table_name="admin_pwa_push_outbox")
    op.drop_constraint(op.f("ck_admin_pwa_outbox_diagnostic_kind"), "admin_pwa_push_outbox", type_="check")
    op.drop_column("admin_pwa_push_outbox", "diagnostic_kind")
    op.drop_table("diagnostic_receipts")
    op.drop_table("diagnostic_incidents")


def _replace_source_check(table, name, predicate, *, restore=False):
    # The historical migration can run with or without Base's naming
    # convention. Resolve only the two exact allowed names, then freeze it.
    context = op.get_context()
    legacy_name = context.dialect.identifier_preparer.truncate_and_render_constraint_name(
        conv(f"ck_{table}_{name}"), _alembic_quote=False)
    historical = legacy_name if context.opts.get("target_metadata") is not None else name
    target = historical if restore else name
    if context.as_sql:
        op.drop_constraint(op.f(name if restore else historical), table, type_="check")
        op.create_check_constraint(op.f(target), table, predicate)
        return
    bind = op.get_bind()
    candidates = [row["name"] for row in sa.inspect(bind).get_check_constraints(table)
                  if row["name"] in (name, legacy_name)]
    if len(candidates) != 1:
        raise RuntimeError(f"Expected one existing source CHECK on {table}")
    op.drop_constraint(op.f(candidates[0]), table, type_="check")
    op.create_check_constraint(op.f(target), table, predicate)
