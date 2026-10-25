"""Fixed-grain overall metrics. Call only inside the protected read snapshot."""
import math

from sqlalchemy import and_, func, or_, select

from app.db.models.ai_usage import AIUsageEvent
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.payment import Payment
from app.db.models.user import User
from app.services.admin_analytics_identity import analytics_user_join
from app.services.admin_miniapp_service import _payment_user_join
from app.services.subscription_service import PLAN_DURATIONS


COURSE_EVENTS = ("lesson_started", "android_lesson_started", "lesson_completed", "book_lesson_completed",
                "android_lesson_completed", "test_started", "test_completed", "training_started",
                "training_completed", "android_practice_started", "android_practice_completed")
METRIC_DEFINITIONS = {
    "ai_usage": {
        "source": "ai_usage_events", "date_field": "created_at", "grain": "recorded usage row",
        "cost_unit": "USD", "cost_basis": "stored cost_usd snapshot; estimate, not provider invoice",
        "population": "all recorded usage, including unmatched historical owners",
        "tokens": "sum of stored total_tokens; no prompts or completions exported",
    },
    "course_engagement": {
        "source": "course_miniapp_events", "date_field": "created_at", "grain": "distinct canonical users.id",
        "population": "current canonical accounts resolved by canonical owner first, positive legacy Telegram fallback",
        "started": ["lesson_started", "android_lesson_started"],
        "completed": ["lesson_completed", "book_lesson_completed", "android_lesson_completed"],
        "engaged": list(COURSE_EVENTS),
        "note": "Completion accounts are deduplicated across event names; not lesson totals or a completion rate.",
    },
    "registration_conversion": {
        "source": "users + payments", "date_field": "users.created_at; coalesce(reviewed_at, submitted_at)",
        "grain": "distinct canonical users.id", "denominator": "accounts registered in selected period, through generated_at",
        "numerator": "denominator accounts with an approved Pro-plan payment dated from registration through generated_at",
        "excluded": "HSK 3.0 unlock, unknown plans, orphaned payments, manual/bonus grants",
        "percent": "100 * converted_accounts / registered_accounts; null for empty cohort",
        "note": "Observed cohort to date, not a fixed-duration or mature trial conversion rate. Later approval changes it.",
    },
}


def _window(column, since, now):
    return [column <= now, *([column >= since] if since else [])]


async def overall_activity_metrics(db, *, since, now):
    usage = (await db.execute(select(
        func.count(AIUsageEvent.id), func.coalesce(func.sum(AIUsageEvent.total_tokens), 0),
        func.coalesce(func.sum(AIUsageEvent.cost_usd), 0.0),
    ).where(*_window(AIUsageEvent.created_at, since, now)))).one()
    cost = float(usage[2])
    if not math.isfinite(cost):
        raise ValueError("Non-finite recorded AI cost")
    started = METRIC_DEFINITIONS["course_engagement"]["started"]
    completed = METRIC_DEFINITIONS["course_engagement"]["completed"]
    course = (await db.execute(select(
        func.count(func.distinct(User.id)),
        func.count(func.distinct(User.id)).filter(CourseMiniAppEvent.event_name.in_(started)),
        func.count(func.distinct(User.id)).filter(CourseMiniAppEvent.event_name.in_(completed)),
        func.count(CourseMiniAppEvent.id).filter(User.id.is_(None)),
    ).select_from(CourseMiniAppEvent).outerjoin(User, and_(analytics_user_join(CourseMiniAppEvent),
        or_(CourseMiniAppEvent.user_id.is_not(None), CourseMiniAppEvent.telegram_id > 0)))
      .where(CourseMiniAppEvent.event_name.in_(COURSE_EVENTS), *_window(CourseMiniAppEvent.created_at, since, now)))).one()
    cohort = _window(User.created_at, since, now)
    denominator = int(await db.scalar(select(func.count(User.id)).where(*cohort)) or 0)
    paid_at = func.coalesce(Payment.reviewed_at, Payment.submitted_at)
    numerator = int(await db.scalar(select(func.count(func.distinct(User.id))).select_from(User)
        .join(Payment, _payment_user_join()).where(
            *cohort, Payment.payment_status == "approved", Payment.plan_type.in_(tuple(PLAN_DURATIONS)),
            or_(Payment.user_id.is_not(None), User.telegram_id > 0),
            paid_at >= User.created_at, paid_at <= now,
        )) or 0)
    return {
        "ai_usage": {"recorded_requests": int(usage[0]), "tokens": int(usage[1]),
                     "estimated_cost_usd": round(cost, 8)},
        "course_engagement": {"engaged_accounts": int(course[0]), "started_accounts": int(course[1]),
                              "completed_accounts": int(course[2]), "unmatched_events": int(course[3])},
        "registration_conversion": {"registered_accounts": denominator, "converted_accounts": numerator,
                                    "percent": round(100*numerator/denominator, 2) if denominator else None},
    }
