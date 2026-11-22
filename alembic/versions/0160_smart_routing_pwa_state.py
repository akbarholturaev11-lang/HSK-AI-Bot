"""Let a Smart routing row be owned by iPhone PWA Web Push (D34).

Constraint-only: `smart_reminder_routing.state` also allows `pwa` (an account
without a Telegram owner served by Web Push), and the review requirement
applies to every non-`held` state. No data changes. Downgrade refuses while a
`pwa` row exists; such rows hold no consent and only veto legacy senders, so
an operator removes them before rolling back.
"""
from alembic import op
import sqlalchemy as sa

revision = "0160_smart_routing_pwa_state"
down_revision = "0159_smart_reminder_content_key"
branch_labels = None
depends_on = None

TABLE = "smart_reminder_routing"


def _constraints(state, review):
    # Names already include the table prefix; op.f() keeps the production
    # naming convention from adding a second one (see 0148).
    with op.batch_alter_table(TABLE) as batch:
        batch.drop_constraint(op.f(f"ck_{TABLE}_state"), type_="check")
        batch.drop_constraint(op.f(f"ck_{TABLE}_review_required"), type_="check")
        batch.create_check_constraint(op.f(f"ck_{TABLE}_state"), state)
        batch.create_check_constraint(op.f(f"ck_{TABLE}_review_required"), review)


def upgrade():
    _constraints("state IN ('held', 'telegram', 'pwa')",
                 "state = 'held' OR (verified_at IS NOT NULL AND inventory_sha256 IS NOT NULL)")


def downgrade():
    if op.get_bind().execute(sa.text(f"SELECT 1 FROM {TABLE} WHERE state = 'pwa' LIMIT 1")).first():
        raise RuntimeError("Remove PWA-owned Smart routing rows before this downgrade")
    _constraints("state IN ('held', 'telegram')",
                 "state != 'telegram' OR (verified_at IS NOT NULL AND inventory_sha256 IS NOT NULL)")
