"""Track PWA Pro modal interaction stages in existing conversion funnel.

Revision ID: 0153_pwa_inline_funnel
Revises: 0152_pwa_exit_offer
"""
from alembic import op

revision = "0153_pwa_inline_funnel"
down_revision = "0152_pwa_exit_offer"
branch_labels = None
depends_on = None

_BASE = (
    "course_cta_seen", "course_started", "lesson_started", "quiz_completed",
    "ai_explanation_seen", "homework_completed", "paywall_seen", "checkout_opened",
    "payment_screenshot_submitted", "payment_approved", "payment_rejected",
    "onboarding_completed", "plan_choice_seen", "trial_started", "trial_expired",
    "trial_converted", "limit_hit", "paywall_cta_clicked", "ad_shown", "ad_skipped",
)
_NEW = (
    "pwa_pro_opened",
    "pwa_pro_plan_selected",
    "pwa_pro_more_opened",
    "pwa_pro_method_selected",
    "pwa_pro_exit_offered",
    "pwa_pro_exit_claimed",
    "pwa_pro_exit_declined",
    "pwa_pro_dismissed",
    "pwa_pro_checkout_started",
    "pwa_pro_checkout_failed",
    "pwa_pro_checkout_paid",
)


def _check(values):
    return "event_name IN (" + ", ".join("'" + name + "'" for name in values) + ")"


def upgrade():
    op.drop_constraint("ck_conversion_funnel_events_event_name",
                       "conversion_funnel_events", type_="check")
    op.create_check_constraint("ck_conversion_funnel_events_event_name",
                               "conversion_funnel_events", _check(_BASE + _NEW))


def downgrade():
    op.drop_constraint("ck_conversion_funnel_events_event_name",
                       "conversion_funnel_events", type_="check")
    op.create_check_constraint("ck_conversion_funnel_events_event_name",
                               "conversion_funnel_events", _check(_BASE))
