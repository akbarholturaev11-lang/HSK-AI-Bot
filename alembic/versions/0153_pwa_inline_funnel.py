"""Extend PWA Pro funnel CHECK without assuming its physical name.

Historical revision 0076 deliberately created the constraint via raw SQL
because SQLAlchemy can double-prefix explicit CHECK names. Follow that
migration contract rather than assuming one particular DB constraint name.
"""
from alembic import op
import sqlalchemy as sa

revision = "0153_pwa_inline_funnel"
down_revision = "0152_pwa_exit_offer"
branch_labels = None
depends_on = None

TABLE = "conversion_funnel_events"
CHECK_NAME = "ck_conversion_funnel_events_event_name"

_BASE = (
    "course_cta_seen", "course_started", "lesson_started", "quiz_completed",
    "ai_explanation_seen", "homework_completed", "paywall_seen", "checkout_opened",
    "payment_screenshot_submitted", "payment_approved", "payment_rejected",
    "onboarding_completed", "plan_choice_seen", "trial_started", "trial_expired",
    "trial_converted", "limit_hit", "paywall_cta_clicked", "ad_shown", "ad_skipped",
)
_NEW = (
    "pwa_pro_opened", "pwa_pro_plan_selected", "pwa_pro_more_opened",
    "pwa_pro_method_selected", "pwa_pro_exit_offered", "pwa_pro_exit_claimed",
    "pwa_pro_exit_declined", "pwa_pro_dismissed",
    "pwa_pro_checkout_started", "pwa_pro_checkout_failed", "pwa_pro_checkout_paid",
)


def _check(names):
    return "event_name IN (" + ", ".join("'" + name + "'" for name in names) + ")"


def _replace(names):
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        # SQLite test databases create the latest model using Base.metadata;
        # earlier ALTER-CHECK migrations already skip SQLite too.
        return

    if bind.dialect.name == "postgresql":
        existing = bind.execute(sa.text(
            "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conrelid = to_regclass(:table) AND contype = 'c'"
        ), {"table": TABLE}).all()
        checks = [name for name, definition in existing
                  if "event_name" in str(definition or "").lower()]
    else:
        checks = [c["name"] for c in sa.inspect(bind).get_check_constraints(TABLE)
                  if c.get("name") and "event_name" in str(c.get("sqltext") or "").lower()]

    if not checks:
        raise RuntimeError("pwa_funnel_event_check_not_found")
    preparer = bind.dialect.identifier_preparer
    for name in checks:
        op.execute(sa.text(
            f"ALTER TABLE {preparer.quote(TABLE)} "
            f"DROP CONSTRAINT {preparer.quote(name)}"
        ))
    op.execute(sa.text(
        f"ALTER TABLE {preparer.quote(TABLE)} "
        f"ADD CONSTRAINT {preparer.quote(CHECK_NAME)} CHECK ({_check(names)})"
    ))


def upgrade():
    _replace(_BASE + _NEW)


def downgrade():
    # New analytics rows cannot satisfy the historical CHECK.
    op.execute(sa.text(
        f"DELETE FROM {TABLE} WHERE event_name IN :names"
    ).bindparams(sa.bindparam("names", value=_NEW, expanding=True)))
    _replace(_BASE)
