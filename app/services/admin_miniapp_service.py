from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import and_, case, func, or_, select

from app.db.models.ad_campaign import AdCampaign, AdCampaignDelivery
from app.db.models.ai_usage import AIUsageEvent
from app.db.models.bot_feedback import BotFeedback
from app.db.models.conversion_funnel_event import ConversionFunnelEvent
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.db.models.course_xp_event import CourseXpEvent
from app.db.models.message import Message
from app.db.models.payment import Payment
from app.db.models.portfolio import PortfolioTransaction
from app.db.models.referral import Referral
from app.db.models.required_channel import RequiredChannel
from app.db.models.subscription_entry_event import SubscriptionEntryEvent
from app.db.models.user import User
from app.db.models.voice_practice_session import VoicePracticeSession
from app.services.admin_stats_service import miniapp_course_stats
from app.services.required_channel_service import RequiredChannelService
from app.services.bot_block_status_service import BotBlockStatusService
from app.services.course_miniapp_admin_analytics_service import CourseMiniAppAdminAnalyticsService
from app.services.subscription_entry_analytics_service import SubscriptionEntryAnalyticsService
from app.services.subscription_price_service import SubscriptionPriceService
from app.services.subscription_currency_service import (
    DEFAULT_USD_CNY_RATE,
    DEFAULT_VISA_LOCAL_RATES,
    format_subscription_price,
)


ADMIN_MINIAPP_TZ = ZoneInfo("Asia/Shanghai")
HOT_LEAD_ACTIVITY_WINDOW = timedelta(days=2)
HOT_LEAD_STATUSES = ("free", "trial", "expired")
HOT_LEAD_PAYMENT_STATUSES = ("none", "draft", "rejected")
SALES_VALUE_EXPERIMENT = "sales_value_v1"
SALES_VALUE_OUTCOME_WINDOW = timedelta(days=7)
SALES_VALUE_D1_START = timedelta(hours=24)
SALES_VALUE_D1_END = timedelta(hours=48)
ADMIN_ADVANCED_DETAIL_WINDOW = timedelta(days=30)
SALES_VALUE_MEANINGFUL_EVENTS = frozenset(
    {
        "section_completed",
        "lesson_completed",
        "book_lesson_completed",
        "test_completed",
        "training_completed",
        "mistake_review_completed",
    }
)


def _pct(part: int, total: int) -> float:
    return round(part / total * 100, 1) if total > 0 else 0.0


def _cohort_retention(
    *,
    created_by_user: dict[int, datetime],
    opens_by_user: dict[int, list[datetime]],
    days: int,
    now: datetime,
) -> dict:
    eligible = 0
    retained = 0
    for telegram_id, created in created_by_user.items():
        window_start = created + timedelta(days=days)
        window_end = window_start + timedelta(days=1)
        if window_end > now:
            continue
        eligible += 1
        if any(window_start <= opened < window_end for opened in opens_by_user.get(telegram_id, ())):
            retained += 1
    return {"eligible": eligible, "retained": retained, "rate": _pct(retained, eligible)}


def _matured_notification_open_proxy(
    sent_rows: list[tuple],
    open_rows: list[tuple],
    *,
    now: datetime,
) -> dict:
    """Attribute reminder opens one-to-one after the full 48h window matures."""
    now = _as_utc(now) or datetime.now(timezone.utc)
    maturity_cutoff = now - timedelta(hours=48)
    matured: list[tuple[int, int, datetime]] = []
    all_sends: list[tuple[int, int, datetime]] = []
    immature = 0
    for index, (telegram_id, sent_at) in enumerate(sent_rows):
        sent = _as_utc(sent_at)
        if not telegram_id or not sent or sent > now:
            continue
        all_sends.append((index, int(telegram_id), sent))
        if sent > maturity_cutoff:
            immature += 1
            continue
        matured.append((index, int(telegram_id), sent))

    opens_by_user: dict[int, list[datetime]] = defaultdict(list)
    for telegram_id, opened_at in open_rows:
        opened = _as_utc(opened_at)
        if telegram_id and opened and opened <= now:
            opens_by_user[int(telegram_id)].append(opened)
    for opens in opens_by_user.values():
        opens.sort()

    credited: set[int] = set()
    for telegram_id, opens in opens_by_user.items():
        user_sends = [row for row in all_sends if row[1] == telegram_id]
        for opened in opens:
            candidates = [
                row
                for row in user_sends
                if row[0] not in credited
                and row[2] <= opened <= row[2] + timedelta(hours=48)
            ]
            if candidates:
                # One CTA open belongs to the nearest preceding reminder only.
                credited.add(max(candidates, key=lambda row: row[2])[0])

    sent = len(matured)
    matured_ids = {row[0] for row in matured}
    opened_after = len(credited & matured_ids)
    return {
        "sent": sent,
        "immature_sent": immature,
        "opened_after": opened_after,
        "open_rate": _pct(opened_after, sent),
    }


def _payment_attempt_funnel(rows: list[tuple]) -> dict:
    attempts: dict[tuple[int, str], dict] = {}
    approvals: dict[int, datetime] = {}

    def payload(raw) -> dict:
        try:
            value = json.loads(raw or "{}")
        except (TypeError, json.JSONDecodeError):
            return {}
        return value if isinstance(value, dict) else {}

    normalized_rows = sorted(rows, key=lambda row: _as_utc(row[4]) or datetime.min.replace(tzinfo=timezone.utc))
    for event_name, telegram_id, payment_id, payload_json, created_at in normalized_rows:
        created = _as_utc(created_at)
        if not created:
            continue
        data = payload(payload_json)
        if event_name == "payment_approved" and payment_id:
            approvals.setdefault(int(payment_id), created)
            continue

        attempt_id = str(data.get("attempt_id") or "").strip()
        if not attempt_id or not telegram_id:
            continue
        attempt_key = (int(telegram_id), attempt_id)
        if event_name == "checkout_opened":
            stage = str(data.get("stage") or "").strip()
            if not stage:
                attempts.setdefault(
                    attempt_key,
                    {
                        "telegram_id": int(telegram_id),
                        "opened_at": created,
                        "stages": {},
                        "payment_id": None,
                    },
                )
                continue
            attempt = attempts.get(attempt_key)
            if attempt and int(telegram_id) == attempt["telegram_id"] and created >= attempt["opened_at"]:
                attempt["stages"].setdefault(stage, created)
            continue

        if event_name == "payment_screenshot_submitted":
            attempt = attempts.get(attempt_key)
            if attempt and int(telegram_id) == attempt["telegram_id"] and created >= attempt["opened_at"]:
                attempt["stages"].setdefault("payment_screenshot_submitted", created)
                attempt["payment_id"] = int(payment_id) if payment_id else None

    reached: dict[str, set[int]] = {
        "checkout_opened": set(),
        "payment_instructions_viewed": set(),
        "payment_receipt_selected": set(),
        "payment_screenshot_submitted": set(),
        "payment_approved": set(),
    }
    for attempt in attempts.values():
        telegram_id = attempt["telegram_id"]
        reached["checkout_opened"].add(telegram_id)
        stages = attempt["stages"]
        screenshot_at = stages.get("payment_screenshot_submitted")
        payment_id = attempt.get("payment_id")
        approved_at = approvals.get(payment_id) if payment_id else None
        approved = bool(screenshot_at and approved_at and approved_at >= screenshot_at)
        screenshot = bool(screenshot_at)
        receipt = bool(stages.get("payment_receipt_selected") or screenshot)
        instructions = bool(stages.get("payment_instructions_viewed") or receipt)
        if instructions:
            reached["payment_instructions_viewed"].add(telegram_id)
        if receipt:
            reached["payment_receipt_selected"].add(telegram_id)
        if screenshot:
            reached["payment_screenshot_submitted"].add(telegram_id)
        if approved:
            reached["payment_approved"].add(telegram_id)

    steps = [
        {"key": "checkout_opened", "label": "Obuna sahifasi", "users": len(reached["checkout_opened"])},
        {"key": "payment_instructions_viewed", "label": "Rekvizitni ko'rdi", "users": len(reached["payment_instructions_viewed"])},
        {"key": "payment_receipt_selected", "label": "Skrinshot tanladi", "users": len(reached["payment_receipt_selected"])},
        {"key": "payment_screenshot_submitted", "label": "Skrinshot yubordi", "users": len(reached["payment_screenshot_submitted"])},
        {"key": "payment_approved", "label": "Tasdiqlandi", "users": len(reached["payment_approved"])},
    ]
    drops = [
        {
            "label": f"{current['label']} → {nxt['label']}",
            "lost": max(int(current["users"]) - int(nxt["users"]), 0),
            "rate": _pct(max(int(current["users"]) - int(nxt["users"]), 0), int(current["users"])),
        }
        for current, nxt in zip(steps, steps[1:])
    ]
    top_drop = max(
        drops,
        key=lambda item: item["lost"],
        default={"label": "Ma'lumot yetarli emas", "lost": 0, "rate": 0.0},
    )
    return {
        "steps": steps if attempts else [],
        "drops": drops if attempts else [],
        "abandon_step": top_drop["label"] if attempts else "Ma'lumot yig'ilmoqda",
        "abandon_count": top_drop["lost"] if attempts else 0,
        "abandon_rate": top_drop["rate"] if attempts else 0.0,
        "attempts": len(attempts),
        "collecting": not bool(attempts),
    }


def _activation_funnel(rows: list[tuple], *, now: datetime) -> dict:
    events_by_user: dict[int, list[tuple[str, datetime, dict]]] = defaultdict(list)
    for row in rows:
        event_name, telegram_id, created_at = row[:3]
        created = _as_utc(created_at)
        if not telegram_id or not created:
            continue
        try:
            payload = json.loads(row[3] or "{}") if len(row) > 3 else {}
        except (TypeError, json.JSONDecodeError):
            payload = {}
        events_by_user[int(telegram_id)].append(
            (str(event_name), created, payload if isinstance(payload, dict) else {})
        )

    def summarize(cohort: dict[int, list[tuple[str, datetime, dict]]]) -> dict:
        result = {
            "onboarded": 0,
            "lesson_started_2m": 0,
            "lesson_started_eligible": 0,
            "section_completed_15m": 0,
            "section_completed_eligible": 0,
            "lesson_completed_24h": 0,
            "lesson_completed_eligible": 0,
        }
        for events in cohort.values():
            events.sort(key=lambda item: item[1])
            onboarding_at = next(
                (at for name, at, _payload in events if name == "onboarding_completed"),
                None,
            )
            if not onboarding_at:
                continue
            result["onboarded"] += 1
            if onboarding_at <= now - timedelta(minutes=2):
                result["lesson_started_eligible"] += 1
                if any(
                    name == "lesson_started" and onboarding_at <= at <= onboarding_at + timedelta(minutes=2)
                    for name, at, _payload in events
                ):
                    result["lesson_started_2m"] += 1
            if onboarding_at <= now - timedelta(minutes=15):
                result["section_completed_eligible"] += 1
                if any(
                    name == "section_completed" and onboarding_at <= at <= onboarding_at + timedelta(minutes=15)
                    for name, at, _payload in events
                ):
                    result["section_completed_15m"] += 1
            if onboarding_at <= now - timedelta(hours=24):
                result["lesson_completed_eligible"] += 1
                if any(
                    name in {"lesson_completed", "book_lesson_completed"}
                    and onboarding_at <= at <= onboarding_at + timedelta(hours=24)
                    for name, at, _payload in events
                ):
                    result["lesson_completed_24h"] += 1
        result["lesson_started_rate"] = _pct(
            result["lesson_started_2m"], result["lesson_started_eligible"]
        )
        result["section_completed_rate"] = _pct(
            result["section_completed_15m"], result["section_completed_eligible"]
        )
        result["lesson_completed_rate"] = _pct(
            result["lesson_completed_24h"], result["lesson_completed_eligible"]
        )
        return result

    variants: dict[str, dict[int, list[tuple[str, datetime, dict]]]] = defaultdict(dict)
    for telegram_id, events in events_by_user.items():
        events.sort(key=lambda item: item[1])
        onboarding = next(
            ((payload, at) for name, at, payload in events if name == "onboarding_completed"),
            None,
        )
        if not onboarding:
            continue
        payload, _at = onboarding
        variant = str(payload.get("activation_variant") or "legacy_or_standard").strip()[:32]
        variants[variant or "legacy_or_standard"][telegram_id] = events

    result = summarize(events_by_user)
    result["variants"] = {name: summarize(cohort) for name, cohort in variants.items()}
    result["explain"] = (
        "Activation = oynasi to'liq tugagan onboarding_completed cohortidan 2 daqiqada dars "
        "boshlagan, 15 daqiqada section va 24 soatda dars tugatgan userlar. Variantlar alohida saqlanadi."
    )
    return result


def _d1_recovery_experiment(
    rows: list[tuple],
    block_rows: list[tuple],
    *,
    now: datetime,
) -> dict:
    experiment_id = "d1_recovery_v1"
    outcome_window = timedelta(hours=48)

    def payload(raw) -> dict:
        try:
            value = json.loads(raw or "{}")
        except (TypeError, json.JSONDecodeError):
            return {}
        return value if isinstance(value, dict) else {}

    events_by_user: dict[int, list[dict]] = defaultdict(list)
    for event_name, telegram_id, source, level, lesson_id, lesson_order, payload_json, created_at in rows:
        created = _as_utc(created_at)
        if not telegram_id or not created:
            continue
        events_by_user[int(telegram_id)].append(
            {
                "name": str(event_name),
                "source": str(source or ""),
                "level": level,
                "lesson_id": lesson_id,
                "lesson_order": lesson_order,
                "payload": payload(payload_json),
                "at": created,
            }
        )
    blocked_at_by_user = {
        int(telegram_id): _as_utc(blocked_at)
        for telegram_id, blocked_at in block_rows
        if telegram_id and _as_utc(blocked_at)
    }

    def blank_arm() -> dict:
        return {
            "assigned": 0,
            "matured": 0,
            "sent": 0,
            "send_failed": 0,
            "opened_any_48h": 0,
            "opened_attributed_48h": 0,
            "lesson_completed_48h": 0,
            "blocked_48h": 0,
        }

    arms = {"treatment": blank_arm(), "control": blank_arm()}
    for telegram_id, events in events_by_user.items():
        events.sort(key=lambda item: item["at"])
        assignment = next(
            (
                event
                for event in events
                if event["name"] == "d1_recovery_assigned"
                and event["source"] == experiment_id
            ),
            None,
        )
        if not assignment:
            continue
        arm = str(assignment["payload"].get("arm") or "")
        if arm not in arms:
            continue
        stats = arms[arm]
        stats["assigned"] += 1
        assigned_at = assignment["at"]
        deadline = assigned_at + outcome_window
        in_window = [event for event in events if assigned_at <= event["at"] < deadline]
        if any(event["name"] == "d1_recovery_sent" for event in in_window):
            stats["sent"] += 1
        if any(event["name"] == "d1_recovery_send_failed" for event in in_window):
            stats["send_failed"] += 1
        if deadline > now:
            continue
        stats["matured"] += 1
        if any(event["name"] == "miniapp_opened" for event in in_window):
            stats["opened_any_48h"] += 1
        if any(
            event["name"] == "miniapp_opened" and event["source"] == experiment_id
            for event in in_window
        ):
            stats["opened_attributed_48h"] += 1

        def same_lesson(event: dict) -> bool:
            if event["name"] not in {"lesson_completed", "book_lesson_completed"}:
                return False
            if assignment["lesson_id"] is not None and event["lesson_id"] is not None:
                return int(event["lesson_id"]) == int(assignment["lesson_id"])
            return (
                event["level"] == assignment["level"]
                and event["lesson_order"] == assignment["lesson_order"]
            )

        if any(same_lesson(event) for event in in_window):
            stats["lesson_completed_48h"] += 1
        blocked_at = blocked_at_by_user.get(telegram_id)
        if blocked_at and assigned_at <= blocked_at < deadline:
            stats["blocked_48h"] += 1

    for arm, stats in arms.items():
        stats["send_rate"] = _pct(stats["sent"], stats["assigned"]) if arm == "treatment" else 0.0
        stats["open_rate"] = _pct(stats["opened_any_48h"], stats["matured"])
        stats["completion_rate"] = _pct(stats["lesson_completed_48h"], stats["matured"])
        stats["block_rate"] = _pct(stats["blocked_48h"], stats["matured"])

    treatment = arms["treatment"]
    control = arms["control"]
    collecting = treatment["matured"] == 0 or control["matured"] == 0
    return {
        "experiment_id": experiment_id,
        "outcome_window_hours": 48,
        "assigned": treatment["assigned"] + control["assigned"],
        "matured": treatment["matured"] + control["matured"],
        "arms": arms,
        "uplift_pp": {
            "open": round(treatment["open_rate"] - control["open_rate"], 1),
            "completion": round(treatment["completion_rate"] - control["completion_rate"], 1),
            "block": round(treatment["block_rate"] - control["block_rate"], 1),
        },
        "collecting": collecting,
        "directional_only": min(treatment["matured"], control["matured"]) < 30,
        "explain": "D1 recovery ITT = assignmentdan keyingi 48 soatda treatment/control Mini App return va ayni dars completion; faqat oynasi tugagan cohort denominatorga kiradi.",
    }


def _sales_payload(raw) -> dict:
    try:
        value = json.loads(raw or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _wilson_interval(successes: int, total: int) -> tuple[float | None, float | None]:
    """95% Wilson score interval as proportions (0..1)."""

    successes = max(0, min(int(successes or 0), int(total or 0)))
    total = int(total or 0)
    if total <= 0:
        return None, None
    z = 1.959963984540054
    z2 = z * z
    proportion = successes / total
    denominator = 1 + z2 / total
    center = (proportion + z2 / (2 * total)) / denominator
    margin = z * math.sqrt(
        proportion * (1 - proportion) / total + z2 / (4 * total * total)
    ) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


def _newcombe_difference_ci(
    treatment_successes: int,
    treatment_total: int,
    control_successes: int,
    control_total: int,
) -> dict[str, float | None]:
    """Newcombe/Wilson 95% CI for treatment-control proportion difference."""

    treatment_low, treatment_high = _wilson_interval(treatment_successes, treatment_total)
    control_low, control_high = _wilson_interval(control_successes, control_total)
    if None in (treatment_low, treatment_high, control_low, control_high):
        return {"low_pp": None, "high_pp": None}
    treatment_rate = treatment_successes / treatment_total
    control_rate = control_successes / control_total
    difference = treatment_rate - control_rate
    lower = difference - math.sqrt(
        (treatment_rate - treatment_low) ** 2
        + (control_high - control_rate) ** 2
    )
    upper = difference + math.sqrt(
        (treatment_high - treatment_rate) ** 2
        + (control_rate - control_low) ** 2
    )
    return {
        "low_pp": round(lower * 100, 2),
        "high_pp": round(upper * 100, 2),
    }


def _sales_srm(
    *,
    treatment_assigned: int,
    control_assigned: int,
    expected_treatment: float,
    expected_control: float,
) -> dict:
    """Two-arm Pearson chi-square SRM check (df=1, p<0.01 warning)."""

    checked = expected_treatment >= 5 and expected_control >= 5
    if not checked:
        return {
            "checked": False,
            "mismatch": False,
            "p_value": None,
            "chi_square": None,
            "expected": {
                "treatment": round(expected_treatment, 2),
                "control": round(expected_control, 2),
            },
        }
    chi_square = (
        (treatment_assigned - expected_treatment) ** 2 / expected_treatment
        + (control_assigned - expected_control) ** 2 / expected_control
    )
    p_value = math.erfc(math.sqrt(chi_square / 2))
    return {
        "checked": True,
        "mismatch": p_value < 0.01,
        "p_value": round(p_value, 6),
        "chi_square": round(chi_square, 4),
        "expected": {
            "treatment": round(expected_treatment, 2),
            "control": round(expected_control, 2),
        },
    }


def _sales_value_experiment(
    course_rows: list[tuple],
    funnel_rows: list[tuple],
    payment_rows: list[tuple],
    *,
    now: datetime,
    error_rows: list[tuple] | None = None,
) -> dict:
    """Evaluate sales_value_v1 as a global, seven-day matured ITT cohort.

    Course row shape: ``(event_name, telegram_id, source, level, lesson_id,
    lesson_order, payload_json, created_at)``. Funnel row shape:
    ``(event_name, telegram_id, payment_id, payload_json, created_at)``.
    Payment row shape: ``(id, telegram_id, status, amount, currency,
    base_amount, reviewed_at, submitted_at)``. Error row shape:
    ``(telegram_id, created_at)``.

    The server-side assignment event is the only arm authority. Approved and
    rejected payments require ``reviewed_at``; a submission timestamp is never
    substituted for approval time.
    """

    now_utc = _as_utc(now) or datetime.now(timezone.utc)
    normalized_course: list[dict] = []
    for row in course_rows:
        if len(row) < 8:
            continue
        created_at = _as_utc(row[7])
        try:
            telegram_id = int(row[1])
        except (TypeError, ValueError):
            continue
        if not created_at or created_at > now_utc:
            continue
        normalized_course.append(
            {
                "name": str(row[0] or ""),
                "telegram_id": telegram_id,
                "source": str(row[2] or ""),
                "level": row[3],
                "lesson_id": row[4],
                "lesson_order": row[5],
                "payload": _sales_payload(row[6]),
                "at": created_at,
            }
        )
    normalized_course.sort(key=lambda item: item["at"])

    assignments: dict[int, dict] = {}
    excluded_assignments = 0
    for event in normalized_course:
        if event["name"] != "sales_offer_assigned" or event["source"] != SALES_VALUE_EXPERIMENT:
            continue
        data = event["payload"]
        mode = str(
            data.get("assigned_mode")
            or data.get("mode")
            or data.get("experiment_mode")
            or "ab"
        ).strip().lower()
        if mode in {"off", "shadow", "treatment"} or data.get("analysis_eligible") is False:
            excluded_assignments += 1
            continue
        arm = str(data.get("arm") or "").strip().lower()
        if arm not in {"treatment", "control"}:
            excluded_assignments += 1
            continue
        try:
            candidate_pct = int(data.get("treatment_percent", data.get("candidate_pct", 50)))
        except (TypeError, ValueError):
            candidate_pct = 50
        candidate_pct = max(0, min(candidate_pct, 100))
        assignments.setdefault(
            event["telegram_id"],
            {
                "arm": arm,
                "at": event["at"],
                "deadline": event["at"] + SALES_VALUE_OUTCOME_WINDOW,
                "candidate_pct": candidate_pct,
                "trigger": str(data.get("trigger") or ""),
            },
        )

    def blank_arm() -> dict:
        return {
            "assigned": 0,
            "matured": 0,
            "bridge_seen": 0,
            "bridge_cta": 0,
            "offer_seen": 0,
            "offer_dismissed": 0,
            "paywall_seen": 0,
            "checkout_opened": 0,
            "payment_submitted": 0,
            "approved_after_submit": 0,
            "approved_users": 0,
            "approved_payments": 0,
            "rejected_users": 0,
            "pending_users": 0,
            "frontend_error_users": 0,
            "foundation_completed": 0,
            "first_checkpoint_completed": 0,
            "d1_meaningful_return": 0,
            "revenue_by_currency": {},
        }

    arms = {"treatment": blank_arm(), "control": blank_arm()}
    for assignment in assignments.values():
        arms[assignment["arm"]]["assigned"] += 1

    course_by_user: dict[int, list[dict]] = defaultdict(list)
    for event in normalized_course:
        if event["telegram_id"] in assignments:
            course_by_user[event["telegram_id"]].append(event)

    funnel_by_user: dict[int, list[dict]] = defaultdict(list)
    for row in funnel_rows:
        if len(row) < 5:
            continue
        created_at = _as_utc(row[4])
        try:
            telegram_id = int(row[1])
        except (TypeError, ValueError):
            continue
        if telegram_id not in assignments or not created_at or created_at > now_utc:
            continue
        funnel_by_user[telegram_id].append(
            {
                "name": str(row[0] or ""),
                "payment_id": int(row[2]) if row[2] else None,
                "payload": _sales_payload(row[3]),
                "at": created_at,
            }
        )
    for events in funnel_by_user.values():
        events.sort(key=lambda item: item["at"])

    payments_by_user: dict[int, list[dict]] = defaultdict(list)
    for row in payment_rows:
        if len(row) < 8:
            continue
        try:
            payment_id = int(row[0])
            telegram_id = int(row[1])
        except (TypeError, ValueError):
            continue
        if telegram_id not in assignments:
            continue
        try:
            amount = int(row[3] or 0)
        except (TypeError, ValueError):
            amount = 0
        payments_by_user[telegram_id].append(
            {
                "id": payment_id,
                "status": str(row[2] or "").strip().lower(),
                "amount": amount,
                "currency": str(row[4] or "unknown").strip().upper() or "UNKNOWN",
                "base_amount": row[5],
                "reviewed_at": _as_utc(row[6]),
                "submitted_at": _as_utc(row[7]),
            }
        )

    errors_by_user: dict[int, list[datetime]] = defaultdict(list)
    for row in error_rows or ():
        if len(row) < 2:
            continue
        try:
            telegram_id = int(row[0])
        except (TypeError, ValueError):
            continue
        created_at = _as_utc(row[1])
        if telegram_id in assignments and created_at and created_at <= now_utc:
            errors_by_user[telegram_id].append(created_at)

    for telegram_id, assignment in assignments.items():
        start = assignment["at"]
        deadline = assignment["deadline"]
        if deadline > now_utc:
            continue
        stats = arms[assignment["arm"]]
        stats["matured"] += 1

        in_window = [
            event
            for event in course_by_user.get(telegram_id, ())
            if start <= event["at"] < deadline
        ]
        if any(event["name"] == "sales_bridge_seen" for event in in_window):
            stats["bridge_seen"] += 1
        if any(event["name"] == "sales_bridge_cta" for event in in_window):
            stats["bridge_cta"] += 1
        if any(event["name"] == "sales_offer_seen" for event in in_window):
            stats["offer_seen"] += 1
        if any(event["name"] == "sales_offer_dismissed" for event in in_window):
            stats["offer_dismissed"] += 1
        if any(event["name"] == "paywall_seen" for event in in_window):
            stats["paywall_seen"] += 1
        if any(event["name"] == "foundation_completed" for event in in_window):
            stats["foundation_completed"] += 1
        if any(
            str(event["level"] or "").strip().lower() == "hsk1"
            and (
                (
                    event["name"] in {"lesson_completed", "book_lesson_completed"}
                    and int(event["lesson_order"] or 0) == 3
                )
                or (
                    event["name"] == "section_completed"
                    and int(event["lesson_order"] or 0) == 1
                    and int(event["payload"].get("section_no") or 0) == 3
                )
            )
            for event in in_window
        ):
            stats["first_checkpoint_completed"] += 1
        if any(
            event["name"] in SALES_VALUE_MEANINGFUL_EVENTS
            and start + SALES_VALUE_D1_START <= event["at"] < start + SALES_VALUE_D1_END
            for event in in_window
        ):
            stats["d1_meaningful_return"] += 1

        attempts: dict[str, datetime] = {}
        submitted_payment_ids: set[int] = set()
        for event in funnel_by_user.get(telegram_id, ()):
            if not start <= event["at"] < deadline:
                continue
            attempt_id = str(event["payload"].get("attempt_id") or "").strip()
            if event["name"] == "checkout_opened":
                stage = str(event["payload"].get("stage") or "").strip()
                if attempt_id and not stage:
                    attempts.setdefault(attempt_id, event["at"])
            elif event["name"] == "payment_screenshot_submitted" and attempt_id in attempts:
                if event["at"] >= attempts[attempt_id] and event["payment_id"]:
                    submitted_payment_ids.add(event["payment_id"])
        if attempts:
            stats["checkout_opened"] += 1
        if submitted_payment_ids:
            stats["payment_submitted"] += 1

        approved: list[dict] = []
        rejected = False
        pending = False
        for payment in payments_by_user.get(telegram_id, ()):
            if payment["status"] == "approved":
                reviewed_at = payment["reviewed_at"]
                if reviewed_at and start <= reviewed_at < deadline:
                    approved.append(payment)
            elif payment["status"] == "rejected":
                reviewed_at = payment["reviewed_at"]
                if reviewed_at and start <= reviewed_at < deadline:
                    rejected = True
            elif payment["status"] == "pending":
                submitted_at = payment["submitted_at"]
                if submitted_at and start <= submitted_at < deadline:
                    pending = True

        if approved:
            stats["approved_users"] += 1
            stats["approved_payments"] += len(approved)
            if any(payment["id"] in submitted_payment_ids for payment in approved):
                stats["approved_after_submit"] += 1
            for payment in approved:
                currency = payment["currency"]
                stats["revenue_by_currency"][currency] = (
                    int(stats["revenue_by_currency"].get(currency, 0)) + payment["amount"]
                )
        if rejected:
            stats["rejected_users"] += 1
        if pending:
            stats["pending_users"] += 1
        if any(start <= created_at < deadline for created_at in errors_by_user.get(telegram_id, ())):
            stats["frontend_error_users"] += 1

    for stats in arms.values():
        matured = stats["matured"]
        stats["approval_rate"] = _pct(stats["approved_users"], matured)
        stats["bridge_seen_rate"] = _pct(stats["bridge_seen"], matured)
        stats["paywall_rate"] = _pct(stats["paywall_seen"], matured)
        stats["checkout_rate"] = _pct(stats["checkout_opened"], matured)
        stats["submitted_rate"] = _pct(stats["payment_submitted"], matured)
        stats["submitted_to_approved_rate"] = _pct(
            stats["approved_after_submit"], stats["payment_submitted"]
        )
        stats["d1_meaningful_return_rate"] = _pct(stats["d1_meaningful_return"], matured)
        stats["foundation_completion_rate"] = _pct(stats["foundation_completed"], matured)
        stats["first_checkpoint_completion_rate"] = _pct(
            stats["first_checkpoint_completed"], matured
        )
        stats["rejected_rate"] = _pct(stats["rejected_users"], matured)
        stats["pending_rate"] = _pct(stats["pending_users"], matured)
        stats["frontend_error_rate"] = _pct(stats["frontend_error_users"], matured)
        stats["revenue_by_currency"] = dict(sorted(stats["revenue_by_currency"].items()))
        stats["revenue_per_matured_by_currency"] = {
            currency: round(amount / matured, 2) if matured else 0.0
            for currency, amount in stats["revenue_by_currency"].items()
        }

    treatment = arms["treatment"]
    control = arms["control"]
    uplift_pp = round(treatment["approval_rate"] - control["approval_rate"], 1)
    relative_lift_pct = (
        round((treatment["approval_rate"] / control["approval_rate"] - 1) * 100, 1)
        if control["approval_rate"] > 0
        else None
    )
    ci_95_pp = _newcombe_difference_ci(
        treatment["approved_users"],
        treatment["matured"],
        control["approved_users"],
        control["matured"],
    )
    expected_treatment = sum(item["candidate_pct"] / 100 for item in assignments.values())
    expected_control = len(assignments) - expected_treatment
    srm = _sales_srm(
        treatment_assigned=treatment["assigned"],
        control_assigned=control["assigned"],
        expected_treatment=expected_treatment,
        expected_control=expected_control,
    )

    learning_delta_pp = round(
        treatment["d1_meaningful_return_rate"] - control["d1_meaningful_return_rate"], 1
    )
    foundation_delta_pp = round(
        treatment["foundation_completion_rate"] - control["foundation_completion_rate"], 1
    )
    checkpoint_delta_pp = round(
        treatment["first_checkpoint_completion_rate"]
        - control["first_checkpoint_completion_rate"],
        1,
    )
    rejection_delta_pp = round(treatment["rejected_rate"] - control["rejected_rate"], 1)
    pending_delta_pp = round(treatment["pending_rate"] - control["pending_rate"], 1)
    frontend_error_delta_pp = round(
        treatment["frontend_error_rate"] - control["frontend_error_rate"], 1
    )
    guardrails = {
        "foundation": {"delta_pp": foundation_delta_pp, "pass": foundation_delta_pp >= -5.0},
        "first_checkpoint": {
            "delta_pp": checkpoint_delta_pp,
            "pass": checkpoint_delta_pp >= -5.0,
        },
        "learning": {"delta_pp": learning_delta_pp, "pass": learning_delta_pp >= -5.0},
        "rejection": {"delta_pp": rejection_delta_pp, "pass": rejection_delta_pp <= 5.0},
        "pending": {"delta_pp": pending_delta_pp, "pass": pending_delta_pp <= 5.0},
        "frontend_error": {
            "delta_pp": frontend_error_delta_pp,
            "pass": frontend_error_delta_pp <= 5.0,
            "available": error_rows is not None,
        },
    }
    guardrails_pass = all(item["pass"] for item in guardrails.values())
    guardrails["pass"] = guardrails_pass

    first_assignment_at = min(
        (item["at"] for item in assignments.values()),
        default=None,
    )
    age_days = (
        round((now_utc - first_assignment_at).total_seconds() / 86400, 1)
        if first_assignment_at
        else 0.0
    )
    total_approved = treatment["approved_users"] + control["approved_users"]
    decision_ready = (
        age_days >= 14
        and treatment["matured"] >= 200
        and control["matured"] >= 200
        and total_approved >= 20
    )
    lift_requirement_met = uplift_pp >= 2.0 or (
        relative_lift_pct is not None and relative_lift_pct >= 20.0
    )
    ci_positive = ci_95_pp["low_pp"] is not None and ci_95_pp["low_pp"] > 0
    winner = bool(decision_ready and lift_requirement_met and ci_positive and guardrails_pass)

    if not assignments or treatment["matured"] == 0 or control["matured"] == 0:
        status = "collecting"
        decision = "keep_testing"
    elif srm["mismatch"]:
        status = "srm_warning"
        decision = "investigate"
    elif not decision_ready:
        status = "inconclusive" if age_days >= 42 else "early_signal"
        decision = "keep_control" if age_days >= 42 else "keep_testing"
    elif not guardrails_pass:
        status = "guardrail_failed"
        decision = "rollback"
    elif winner:
        status = "winner"
        decision = "promote"
    elif age_days >= 42:
        status = "inconclusive"
        decision = "keep_control"
    else:
        status = "keep_testing"
        decision = "keep_testing"

    return {
        "experiment_id": SALES_VALUE_EXPERIMENT,
        "outcome_window_days": 7,
        "first_assignment_at": first_assignment_at.isoformat() if first_assignment_at else None,
        "age_days": age_days,
        "assigned": len(assignments),
        "matured": treatment["matured"] + control["matured"],
        "excluded_assignments": excluded_assignments,
        "arms": arms,
        "uplift_pp": uplift_pp,
        "relative_lift_pct": relative_lift_pct,
        "ci_95_pp": ci_95_pp,
        "srm": srm,
        "guardrails": guardrails,
        "decision_ready": decision_ready,
        "directional_only": not decision_ready,
        "status": status,
        "decision": decision,
        "thresholds": {
            "min_days": 14,
            "max_days": 42,
            "matured_per_arm": 200,
            "approved_total": 20,
            "absolute_lift_pp": 2.0,
            "relative_lift_pct": 20.0,
            "learning_decline_pp": 5.0,
            "error_increase_pp": 5.0,
        },
        "explain": (
            "Sales ITT = server assignmentdan keyingi 7 kun oynasi to'liq tugagan userlar. "
            "Approved/rejected faqat Payment.reviewed_at bilan; checkout va screenshot bir xil "
            "attempt_id/payment_id zanjiri bilan. Shadow va 100% treatment rollout decision cohortiga kirmaydi."
        ),
    }


def _sales_value_card(result: dict) -> dict:
    status = str(result.get("status") or "collecting")
    labels = {
        "collecting": "Yig'ilmoqda",
        "early_signal": "Erta signal",
        "srm_warning": "SRM xato",
        "guardrail_failed": "Guardrail xato",
        "winner": f"{float(result.get('uplift_pp') or 0):+.1f} pp",
        "keep_testing": f"{float(result.get('uplift_pp') or 0):+.1f} pp",
        "inconclusive": "Control saqlansin",
    }
    tones = {
        "winner": "good",
        "srm_warning": "danger",
        "guardrail_failed": "danger",
        "inconclusive": "warn",
        "early_signal": "info",
        "collecting": "info",
        "keep_testing": "info",
    }
    arms = result.get("arms") or {}
    treatment = arms.get("treatment") or {}
    control = arms.get("control") or {}
    ci = result.get("ci_95_pp") or {}
    ci_text = (
        f"CI {float(ci['low_pp']):+.1f}…{float(ci['high_pp']):+.1f} pp"
        if ci.get("low_pp") is not None and ci.get("high_pp") is not None
        else "CI yig'ilmoqda"
    )
    return {
        "label": "Sales A/B · 7d approved",
        "value": labels.get(status, status),
        "note": (
            f"T {treatment.get('approved_users', 0)}/{treatment.get('matured', 0)} · "
            f"C {control.get('approved_users', 0)}/{control.get('matured', 0)} · {ci_text}"
        ),
        "tone": tones.get(status, "info"),
    }


def _usd(value: float) -> str:
    try:
        return f"${float(value or 0):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def _amount_to_usd(amount, currency: str | None, *, base_amount=None) -> float | None:
    key = (currency or "").strip().lower()
    try:
        value = float(amount or 0)
    except (TypeError, ValueError):
        value = 0.0
    if key in {"somoni", "tjs", "сомони"}:
        return value / float(DEFAULT_VISA_LOCAL_RATES["tjs"])
    if key in {"usd", "$"}:
        return value
    if key in {"¥", "cny", "yuan", "юань"}:
        return value / float(DEFAULT_USD_CNY_RATE)
    if base_amount:
        return _amount_to_usd(base_amount, "TJS")
    return None


def _duration_seconds(start: datetime | None, end: datetime | None, *, cap_seconds: int = 8 * 60 * 60) -> int:
    start = _as_utc(start)
    end = _as_utc(end)
    if not start or not end or end < start:
        return 0
    seconds = int((end - start).total_seconds())
    if seconds <= 0 or seconds > cap_seconds:
        return 0
    return seconds


def _lesson_attempt_durations(
    rows: list[tuple],
    *,
    completion_since: datetime | None = None,
) -> list[int]:
    grouped: dict[tuple[int, str], list[tuple[datetime, str, str | None]]] = defaultdict(list)
    for telegram_id, level, lesson_id, lesson_order, session_id, event_name, created_at in rows:
        created = _as_utc(created_at)
        if not telegram_id or not created:
            continue
        lesson_ref = f"{level or 'unknown'}:{lesson_order or lesson_id or 0}"
        grouped[(int(telegram_id), lesson_ref)].append(
            (created, str(event_name), str(session_id) if session_id else None)
        )

    durations: list[int] = []
    completed_names = {"book_lesson_completed", "lesson_completed"}
    for events in grouped.values():
        starts: dict[str | None, datetime] = {}
        last_completion_at: datetime | None = None
        events.sort(key=lambda item: (item[0], 0 if item[1] == "lesson_started" else 1))
        for created, event_name, session_id in events:
            if event_name == "lesson_started":
                starts[session_id] = created
                continue
            if event_name not in completed_names:
                continue
            if completion_since is not None and created < completion_since:
                continue
            if last_completion_at and (created - last_completion_at).total_seconds() <= 5:
                continue
            if session_id is not None:
                if session_id not in starts:
                    continue
                start_key = session_id
            else:
                candidates = [(at, key) for key, at in starts.items() if at <= created]
                if not candidates:
                    continue
                _at, start_key = max(candidates, key=lambda item: item[0])
            start = starts.pop(start_key)
            seconds = _duration_seconds(start, created)
            if seconds > 0:
                durations.append(seconds)
                last_completion_at = created
    return durations


def _miniapp_session_durations(rows: list[tuple], *, idle_minutes: int = 30) -> tuple[int, list[int]]:
    events_by_session: dict[tuple[int, str], list[datetime]] = defaultdict(list)
    for telegram_id, session_id, created_at in rows:
        created = _as_utc(created_at)
        if telegram_id and session_id and created:
            events_by_session[(int(telegram_id), str(session_id))].append(created)

    session_count = 0
    durations: list[int] = []
    idle_gap = timedelta(minutes=idle_minutes)
    for events in events_by_session.values():
        events.sort()
        segment_start = events[0]
        previous = events[0]
        for created in events[1:]:
            if created - previous > idle_gap:
                session_count += 1
                seconds = _duration_seconds(segment_start, previous)
                if seconds > 0:
                    durations.append(seconds)
                segment_start = created
            previous = created
        session_count += 1
        seconds = _duration_seconds(segment_start, previous)
        if seconds > 0:
            durations.append(seconds)
    return session_count, durations


def _duration_text(seconds: int | float | None) -> str:
    seconds = int(seconds or 0)
    if seconds <= 0:
        return "—"
    minutes = seconds // 60
    if minutes < 1:
        return f"{seconds}s"
    if minutes < 60:
        return f"{minutes} min"
    hours = minutes // 60
    rest = minutes % 60
    return f"{hours}h {rest}m" if rest else f"{hours}h"


def _dt(value: datetime | None) -> str | None:
    if not value:
        return None
    try:
        return value.astimezone(ADMIN_MINIAPP_TZ).strftime("%d.%m.%Y %H:%M")
    except Exception:
        return str(value)


def _ago(value: datetime | None, *, now: datetime) -> str:
    value = _as_utc(value)
    now = _as_utc(now) or now
    if not value:
        return "ҳали йўқ"
    delta = now - value
    if delta.total_seconds() < 60:
        return "ҳозир"
    minutes = int(delta.total_seconds() // 60)
    if minutes < 60:
        return f"{minutes} дақиқа олдин"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} соат олдин"
    days = hours // 24
    if days < 30:
        return f"{days} кун олдин"
    return _dt(value) or "ҳали йўқ"


def _level_label(value: str | None) -> str:
    labels = {
        "beginner": "Бошловчи",
        "hsk1": "HSK1",
        "hsk2": "HSK2",
        "hsk3": "HSK3",
        "hsk4": "HSK4",
    }
    return labels.get(str(value or "").lower(), value or "—")


def _language_label(value: str | None) -> str:
    labels = {"uz": "Ўзбекча", "ru": "Русча", "tj": "Тожикча"}
    return labels.get(str(value or "").lower(), value or "—")


def _status_label(value: str | None) -> str:
    labels = {
        "active": "Фаол",
        "trial": "Синов",
        "expired": "Муддати тугаган",
        "blocked": "Блокланган",
        "free": "Бепул",
    }
    return labels.get(str(value or "").lower(), value or "—")


def _payment_label(value: str | None) -> str:
    labels = {
        "approved": "Тасдиқланган",
        "pending": "Текширувда",
        "draft": "Танланган",
        "rejected": "Рад этилган",
        "none": "Тўлов йўқ",
    }
    return labels.get(str(value or "").lower(), value or "—")


def _bot_block_filter():
    return (
        User.bot_blocked_at.is_not(None),
        or_(
            User.bot_unblocked_at.is_(None),
            User.bot_unblocked_at < User.bot_blocked_at,
        ),
    )


def _bot_not_blocked_filter():
    return or_(
        User.bot_blocked_at.is_(None),
        User.bot_unblocked_at >= User.bot_blocked_at,
    )


def _no_pending_payment_filter():
    return ~select(Payment.id).where(
        Payment.user_telegram_id == User.telegram_id,
        Payment.payment_status == "pending",
    ).exists()


def admin_miniapp_today_start(now: datetime) -> datetime:
    return now.astimezone(ADMIN_MINIAPP_TZ).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    ).astimezone(timezone.utc)


def _as_utc(value: datetime | None) -> datetime | None:
    if not value:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _is_at_or_after(value: datetime | None, cutoff: datetime) -> bool:
    value = _as_utc(value)
    return bool(value and value >= cutoff)


def is_admin_active_today(user, today_start: datetime) -> bool:
    return _is_at_or_after(getattr(user, "last_active_at", None), today_start)


def is_admin_hot_lead(user, hot_since: datetime) -> bool:
    return (
        str(getattr(user, "status", "") or "").lower() in HOT_LEAD_STATUSES
        and str(getattr(user, "payment_status", "") or "none").lower() in HOT_LEAD_PAYMENT_STATUSES
        and not BotBlockStatusService.is_bot_blocked(user)
        and _is_at_or_after(getattr(user, "last_active_at", None), hot_since)
    )


def is_admin_course_hot_user(user, profile, hot_start_date) -> bool:
    if not profile or BotBlockStatusService.is_bot_blocked(user):
        return False
    last_day = getattr(profile, "last_activity_date", None)
    return bool(last_day and last_day >= hot_start_date)




def _plan_label(value: str | None) -> str:
    labels = {"10_days": "10 кун", "1_month": "1 ой"}
    return labels.get(str(value or "").lower(), value or "—")


def _method_label(value: str | None) -> str:
    labels = {"visa": "Visa/карта", "alipay": "Alipay", "wechat": "WeChat"}
    return labels.get(str(value or "").lower(), value or "—")


def _currency_total(rows) -> str:
    parts = [
        format_subscription_price(int(row.total_sum or 0), row.currency)
        for row in rows
        if row.total_sum
    ]
    return " · ".join(parts) if parts else "0"


class AdminMiniAppService:
    def __init__(self, session):
        self.session = session

    async def overview(self) -> dict:
        now = datetime.now(timezone.utc)
        today_start = admin_miniapp_today_start(now)
        today_date = now.astimezone(ADMIN_MINIAPP_TZ).date()
        two_day_start_date = today_date - timedelta(days=1)
        last_24h = now - timedelta(hours=24)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        hot_since = now - HOT_LEAD_ACTIVITY_WINDOW

        total = await self._count_users()
        status_counts = await self._group_counts(User.status)
        language_counts = await self._group_counts(User.language)
        level_counts = await self._group_counts(User.level)

        new_today = await self._count_users(User.created_at >= today_start)
        new_week = await self._count_users(User.created_at >= week_ago)
        new_month = await self._count_users(User.created_at >= month_ago)
        active_today = await self._count_users(User.last_active_at >= today_start)
        active_24h = await self._count_users(User.last_active_at >= last_24h)
        active_week = await self._count_users(User.last_active_at >= week_ago)

        pay_by_status = await self._payment_status_counts()
        pay_by_plan = await self._payment_plan_counts()
        approved_totals = await self._approved_currency_totals()
        pending_payments = int(pay_by_status.get("pending", {}).get("count", 0))
        approved_payments = int(pay_by_status.get("approved", {}).get("count", 0))
        rejected_payments = int(pay_by_status.get("rejected", {}).get("count", 0))
        paid_users = await self._paid_user_count(now)
        historical_approved_users = await self._approved_payment_user_count()
        pending_payment_users = await self._pending_payment_user_count()
        bot_blocked_users = await self._count_users(*_bot_block_filter())

        miniapp_course = await miniapp_course_stats(self.session)
        avg_sections = (
            round(miniapp_course.completed_sections / miniapp_course.completed_users, 1)
            if miniapp_course.completed_users > 0
            else 0
        )

        channels_enabled = await RequiredChannelService(self.session).is_enabled()
        channel_rows = await self._required_channels()
        active_channels = await self._count_active_required_channels()
        ad_summary = await self._ad_summary()
        feedback_summary = await self._feedback_summary()
        source_rows = await self._subscription_sources(week_ago)
        price_rows = await self._price_rows()
        course_hot = await self._course_activity_hot_leads(
            today_start=today_start,
            hot_since=hot_since,
            today_date=today_date,
            two_day_start_date=two_day_start_date,
        )
        latest_users = await self._latest_users(
            now,
            today_start=today_start,
            hot_since=hot_since,
        )
        latest_payments = await self._latest_payments()
        data_quality = await self._data_quality(now)

        expired_hot = await self._count_users(
            User.status == "expired",
            User.last_active_at >= week_ago,
        )
        expiring_soon = await self._count_users(
            User.status == "active",
            User.end_date.is_not(None),
            User.end_date > now,
            User.end_date <= now + timedelta(days=3),
        )
        hot_leads = await self._count_users(
            User.status.in_(HOT_LEAD_STATUSES),
            User.payment_status.in_(HOT_LEAD_PAYMENT_STATUSES),
            User.last_active_at >= hot_since,
            _bot_not_blocked_filter(),
            _no_pending_payment_filter(),
        )
        qa_users = await self._qa_user_count()
        conversion = _pct(historical_approved_users, total)
        engagement = _pct(qa_users, total)

        report_text = self._report_text(
            now=now,
            total=total,
            status_counts=status_counts,
            paid_users=paid_users,
            historical_approved_users=historical_approved_users,
            new_today=new_today,
            new_week=new_week,
            new_month=new_month,
            active_today=active_today,
            active_24h=active_24h,
            active_week=active_week,
            level_counts=level_counts,
            language_counts=language_counts,
            pending_payments=pending_payments,
            approved_payments=approved_payments,
            rejected_payments=rejected_payments,
            pay_by_plan=pay_by_plan,
            approved_total_text=_currency_total(approved_totals),
            source_rows=source_rows,
            miniapp_course=miniapp_course,
            avg_sections=avg_sections,
            ad_summary=ad_summary,
            channels_enabled=channels_enabled,
            active_channels=active_channels,
            conversion=conversion,
            qa_users=qa_users,
            engagement=engagement,
        )
        period_reports = await self._period_reports(
            now=now,
            week_ago=week_ago,
            month_ago=month_ago,
            all_course_stats=miniapp_course,
        )
        for report in period_reports:
            if report.get("key") == "all_time":
                report["text"] = report_text + self._advanced_report_text(report.get("advanced") or {})

        return {
            "ok": True,
            "generated_at": _dt(now),
            "data_quality": data_quality,
            "report_text": report_text,
            "statistics_reports": period_reports,
            "summary": [
                {"label": "Фойдаланувчилар", "value": total, "note": f"{active_today} бугун фаол", "tone": "info"},
                {"label": "Фаол обуна", "value": paid_users, "note": "ҳозир тўловли", "tone": "good"},
                {"label": "Тўлов текширувда", "value": pending_payments, "note": "админ кўриши керак", "tone": "warn"},
                {
                    "label": "Иссиқ мижоз",
                    "value": hot_leads,
                    "note": (
                        f"48 соатда фаол, тўламаган · course фаол "
                        f"{course_hot.get('last_2_days_users', 0)}"
                    ),
                    "tone": "danger",
                },
            ],
            "counts": {
                "users_total": total,
                "paid_users": paid_users,
                "pending_payments": pending_payments,
                "pending_payment_users": pending_payment_users,
                "approved_payments": approved_payments,
                "rejected_payments": rejected_payments,
                "new_today": new_today,
                "new_week": new_week,
                "new_month": new_month,
                "active_today": active_today,
                "active_24h": active_24h,
                "active_week": active_week,
                "expired_hot": expired_hot,
                "hot_leads": hot_leads,
                "course_active_today_users": course_hot.get("today_users", 0),
                "course_active_2d_users": course_hot.get("last_2_days_users", 0),
                "course_streak_3_users": course_hot.get("streak_3_users", 0),
                "course_streak_7_users": course_hot.get("streak_7_users", 0),
                "expiring_soon": expiring_soon,
                "bot_blocked_users": bot_blocked_users,
                "conversion": conversion,
                "engagement": engagement,
            },
            "segments": {
                "all": total,
                "active_today": active_today,
                "paid": paid_users,
                "pending": pending_payment_users,
                "wants_pay": hot_leads,
                "trial": int(status_counts.get("trial", 0)),
                "free": int(status_counts.get("free", 0)),
                "expired": int(status_counts.get("expired", 0)),
                "blocked": int(status_counts.get("blocked", 0)),
                "bot_blocked": bot_blocked_users,
            },
            "levels": [{"label": _level_label(key), "value": value} for key, value in sorted(level_counts.items())],
            "languages": [{"label": _language_label(key), "value": value} for key, value in sorted(language_counts.items())],
            "payments": {
                "total_text": _currency_total(approved_totals),
                "by_status": pay_by_status,
                "by_plan": pay_by_plan,
                "latest": latest_payments,
            },
            "course": {
                "opened_users": miniapp_course.opened_users,
                "lesson_users": miniapp_course.lesson_users,
                "completed_users": miniapp_course.completed_users,
                "completed_sections": miniapp_course.completed_sections,
                "completed_book_lessons": miniapp_course.completed_book_lessons,
                "avg_sections": avg_sections,
            },
            "channels": {
                "enabled": channels_enabled,
                "active_count": active_channels,
                "items": channel_rows,
            },
            "ads": ad_summary,
            "feedback": feedback_summary,
            "subscription_sources": source_rows,
            "course_hot_leads": course_hot,
            "prices": price_rows,
            "users": latest_users,
            "queue": self._queue(
                pending_payments=pending_payments,
                expiring_soon=expiring_soon,
                expired_hot=expired_hot,
                ad_summary=ad_summary,
            ),
            "modules": self._modules(),
            "monitor": self._monitor(
                active_week=active_week,
                active_24h=active_24h,
                pending_payments=pending_payments,
                approved_total_text=_currency_total(approved_totals),
                miniapp_course=miniapp_course,
                ad_summary=ad_summary,
                channels_enabled=channels_enabled,
                active_channels=active_channels,
            ),
        }

    async def _count_users(self, *conditions) -> int:
        stmt = select(func.count()).select_from(User)
        if conditions:
            stmt = stmt.where(*conditions)
        return (await self.session.execute(stmt)).scalar() or 0

    async def _group_counts(self, column) -> dict[str, int]:
        rows = (await self.session.execute(
            select(column, func.count().label("cnt")).group_by(column)
        )).fetchall()
        return {str(row[0] or "—"): int(row.cnt or 0) for row in rows}

    async def _payment_status_counts(self, since: datetime | None = None) -> dict[str, dict[str, int]]:
        effective_at = case(
            (
                Payment.payment_status.in_(("approved", "rejected")),
                func.coalesce(Payment.reviewed_at, Payment.submitted_at),
            ),
            else_=Payment.submitted_at,
        )
        stmt = select(
            Payment.payment_status,
            func.count().label("cnt"),
            func.coalesce(func.sum(Payment.amount), 0).label("total_sum"),
        ).group_by(Payment.payment_status)
        if since is not None:
            stmt = stmt.where(effective_at >= since)
        rows = (await self.session.execute(stmt)).fetchall()
        return {
            str(row.payment_status or "—"): {
                "count": int(row.cnt or 0),
                "amount": int(row.total_sum or 0),
            }
            for row in rows
        }

    async def _payment_plan_counts(self, since: datetime | None = None) -> dict[str, int]:
        conditions = [Payment.payment_status == "approved", *self._approved_payment_period_conditions(since)]
        rows = (await self.session.execute(
            select(Payment.plan_type, func.count().label("cnt"))
            .where(*conditions)
            .group_by(Payment.plan_type)
        )).fetchall()
        return {str(row.plan_type or "—"): int(row.cnt or 0) for row in rows}

    async def _approved_currency_totals(self, since: datetime | None = None):
        conditions = [Payment.payment_status == "approved", *self._approved_payment_period_conditions(since)]
        return (await self.session.execute(
            select(Payment.currency, func.sum(Payment.amount).label("total_sum"))
            .where(*conditions)
            .group_by(Payment.currency)
        )).fetchall()

    async def _paid_user_count(self, now: datetime) -> int:
        return await self._count_users(
            User.payment_status == "approved",
            User.status == "active",
            User.end_date.is_not(None),
            User.end_date > now,
        )

    @staticmethod
    def _approved_payment_period_conditions(since: datetime | None = None) -> list:
        if since is None:
            return []
        return [
            or_(
                Payment.reviewed_at >= since,
                and_(Payment.reviewed_at.is_(None), Payment.submitted_at >= since),
            )
        ]

    async def _approved_payment_user_count(self, since: datetime | None = None) -> int:
        conditions = [Payment.payment_status == "approved", *self._approved_payment_period_conditions(since)]
        stmt = select(func.count(func.distinct(Payment.user_telegram_id))).select_from(Payment).where(*conditions)
        return (await self.session.execute(stmt)).scalar() or 0

    async def _pending_payment_user_count(self) -> int:
        stmt = (
            select(func.count(func.distinct(Payment.user_telegram_id)))
            .select_from(Payment)
            .where(Payment.payment_status == "pending")
        )
        return (await self.session.execute(stmt)).scalar() or 0

    async def _qa_user_count(self) -> int:
        stmt = (
            select(func.count(func.distinct(AIUsageEvent.user_telegram_id)))
            .select_from(AIUsageEvent)
            .where(AIUsageEvent.source == "qa")
        )
        return (await self.session.execute(stmt)).scalar() or 0

    async def _data_quality(self, now: datetime) -> dict:
        sources = {
            "users": (
                "User activity",
                (
                    await self.session.execute(select(func.max(User.last_active_at)))
                ).scalar(),
            ),
            "payments": (
                "Payment",
                (
                    await self.session.execute(
                        select(
                            func.max(
                                func.coalesce(Payment.reviewed_at, Payment.submitted_at)
                            )
                        )
                    )
                ).scalar(),
            ),
            "course": (
                "Course event",
                (
                    await self.session.execute(
                        select(func.max(CourseMiniAppEvent.created_at))
                    )
                ).scalar(),
            ),
            "ai": (
                "AI usage",
                (
                    await self.session.execute(select(func.max(AIUsageEvent.created_at)))
                ).scalar(),
            ),
            "subscription_sources": (
                "Subscription source",
                (
                    await self.session.execute(
                        select(func.max(SubscriptionEntryEvent.created_at))
                    )
                ).scalar(),
            ),
            "desktop": (
                "Desktop event",
                (
                    await self.session.execute(
                        select(func.max(CourseMiniAppEvent.created_at)).where(
                            CourseMiniAppEvent.event_name.like("desktop_%")
                        )
                    )
                ).scalar(),
            ),
        }
        rows = []
        for key, (label, raw_at) in sources.items():
            at = _as_utc(raw_at)
            age_hours = (
                round(max((now - at).total_seconds(), 0) / 3600, 1)
                if at
                else None
            )
            rows.append(
                {
                    "key": key,
                    "label": label,
                    "last_at": _dt(at) if at else "—",
                    "age_hours": age_hours,
                    "status": "ok" if at else "no_data",
                }
            )
        return {
            "rows": rows,
            "explain": (
                "Bu vaqtlar har manbadagi oxirgi DB yozuvini ko'rsatadi. "
                "No data yoki kutilmaganda eski vaqt telemetry uzilganini 0 natijadan ajratishga yordam beradi."
            ),
        }

    async def _period_reports(
        self,
        *,
        now: datetime,
        week_ago: datetime,
        month_ago: datetime,
        all_course_stats,
    ) -> list[dict]:
        # Sales A/B is a global experiment cohort. Reusing one snapshot across
        # period tabs avoids truncating a user's seven-day outcome window at a
        # weekly/monthly report boundary and avoids running the same queries
        # three times for one overview response.
        sales_value = await self._sales_value_stats(now=now, since=month_ago)
        return [
            await self._period_report(
                key="weekly",
                title="Ҳафталик",
                note="Охирги 7 кун",
                since=week_ago,
                now=now,
                sales_value=sales_value,
            ),
            await self._period_report(
                key="monthly",
                title="Ойлик",
                note="Охирги 30 кун",
                since=month_ago,
                now=now,
                sales_value=sales_value,
            ),
            await self._period_report(
                key="all_time",
                title="Тўлиқ",
                note="Бутун база",
                since=None,
                now=now,
                course_stats=all_course_stats,
                sales_value=sales_value,
            ),
        ]

    async def _period_report(
        self,
        *,
        key: str,
        title: str,
        note: str,
        since: datetime | None,
        now: datetime,
        course_stats=None,
        sales_value: dict | None = None,
    ) -> dict:
        advanced_since = since
        advanced_scope_note = None
        if since is None:
            user_count = await self._count_users()
            active_users = await self._count_users(
                User.last_active_at >= now - timedelta(days=30)
            )
            bot_blocked = await self._count_users(*_bot_block_filter())
            active_label = "30 кун фаол"
            active_note = "охирги 30 кун"
            advanced_since = now - ADMIN_ADVANCED_DETAIL_WINDOW
            advanced_scope_note = (
                "All-time reportdagi asosiy user/payment/course raqamlari butun baza; "
                "product health detail esa Railway RAM spike oldini olish uchun oxirgi 30 kun."
            )
        else:
            user_count = await self._count_users(User.created_at >= since)
            active_users = await self._count_users(User.last_active_at >= since)
            bot_blocked = await self._count_users(User.bot_blocked_at >= since)
            active_label = "Фаол"
            active_note = "шу даврда"

        payment_status = await self._payment_status_counts(since)
        pending_payments = int(payment_status.get("pending", {}).get("count", 0))
        approved_payments = int(payment_status.get("approved", {}).get("count", 0))
        rejected_payments = int(payment_status.get("rejected", {}).get("count", 0))
        approved_total_text = _currency_total(await self._approved_currency_totals(since))
        approved_users = await self._approved_payment_user_count(since)
        plan_counts = await self._payment_plan_counts(since)
        course = course_stats or await miniapp_course_stats(self.session, since=since)
        advanced = await self._advanced_stats(
            since=advanced_since,
            now=now,
            sales_value=sales_value,
        )
        if advanced_scope_note:
            advanced["scope"] = {
                "key": "rolling_30_days",
                "since": _dt(advanced_since),
                "note": advanced_scope_note,
            }
            advanced["explain"] = f"{advanced.get('explain', '')} {advanced_scope_note}".strip()

        metrics = {
            "user_count": user_count,
            "active_users": active_users,
            "approved_payment_users": approved_users,
            "pending_payments": pending_payments,
            "approved_payments": approved_payments,
            "rejected_payments": rejected_payments,
            "approved_total_text": approved_total_text,
            "bot_blocked": bot_blocked,
            "course_completion": _pct(course.completed_users, course.opened_users),
            "active_label": active_label,
        }
        report = {
            "key": key,
            "title": title,
            "note": note,
            "generated_at": _dt(now),
            "metrics": metrics,
            "cards": [
                {"label": "Фойдаланувчи", "value": user_count, "note": "янги" if since else "жами база", "tone": "info"},
                {"label": active_label, "value": active_users, "note": active_note, "tone": "good"},
                {"label": "Тасдиқланган тўлов", "value": approved_users, "note": approved_total_text, "tone": "good"},
                {"label": "Тўлов текширувда", "value": pending_payments, "note": "шу даврда", "tone": "warn"},
                {"label": "Курс очилди", "value": course.opened_users, "note": "мустақил уникал user", "tone": "info"},
                {"label": "Тўлиқ дарс тугади", "value": course.completed_users, "note": f"{course.completed_book_lessons} уникал user-dars", "tone": "good"},
                {"label": "Бот блок", "value": bot_blocked, "note": "шу даврда" if since else "ҳозир блок", "tone": "danger"},
                {"label": "Рад тўлов", "value": rejected_payments, "note": "қайта сотиш сигнали", "tone": "danger"},
            ],
            "payments": {
                "by_status": payment_status,
                "by_plan": plan_counts,
                "total_text": approved_total_text,
            },
            "course": {
                "opened_users": course.opened_users,
                "lesson_users": course.lesson_users,
                "completed_users": course.completed_users,
                "completed_sections": course.completed_sections,
                "completed_book_lessons": course.completed_book_lessons,
                "completion": metrics["course_completion"],
                "counting_note": (
                    "Opened, lesson va completion mustaqil period user countlari; "
                    "ordered cohort conversion emas."
                ),
            },
            "advanced": advanced,
        }
        report["text"] = self._period_report_text(report)
        return report

    async def _advanced_stats(
        self,
        *,
        since: datetime | None,
        now: datetime,
        sales_value: dict | None = None,
    ) -> dict:
        if since is None:
            since = now - ADMIN_ADVANCED_DETAIL_WINDOW
        retention = await self._retention_stats(since=since, now=now)
        activation = await self._activation_stats(since=since, now=now)
        primary_activation = (activation.get("variants") or {}).get("direct_start_v1") or activation
        d1_recovery = await self._d1_recovery_stats(since=since, now=now)
        d1_open_lift = float((d1_recovery.get("uplift_pp") or {}).get("open", 0) or 0)
        if d1_recovery["collecting"] or d1_recovery["directional_only"] or d1_open_lift == 0:
            d1_tone = "info"
        else:
            d1_tone = "good" if d1_open_lift > 0 else "danger"
        session_time = await self._miniapp_session_time(since=since)
        lesson_time = await self._lesson_time(since=since)
        qa = await self._qa_message_stats(since=since)
        voice = await self._voice_minutes(since=since)
        payment = await self._payment_advanced_stats(since=since)
        feature_adoption = await self._feature_adoption(since=since, now=now)
        notifications = await self._notification_open_proxy(since=since, now=now)
        foundation = await CourseMiniAppAdminAnalyticsService(self.session).foundation_metrics(
            since=since,
            now=now,
        )
        foundation_parts = {int(item["part"]): item for item in foundation["parts"]}
        foundation_first = foundation["first_attempt"]
        checkpoint_paywall = foundation["checkpoint_to_paywall"]
        foundation_d1 = foundation["d1_meaningful_return"]

        return {
            "explain": (
                "Bu blok product health metrikalarini ko'rsatadi: retention, Mini App vaqt, dars vaqti, "
                "Starter 0 mastery, QA/Voice ishlatilishi, payment funnel, revenue/payer, taglangan CAC, paid/free feature adoption "
                "va notification open proxy. Sales A/B esa report davridan mustaqil global 7 kunlik matured cohort. "
                "Qolgan raqamlar tanlangan davr ichida qayta hisoblanadi."
            ),
            "cards": [
                {
                    "label": "Signup → App D1",
                    "value": f"{retention['d1']['rate']}%" if retention["d1"]["eligible"] else "Yig'ilmoqda",
                    "note": f"{retention['d1']['retained']}/{retention['d1']['eligible']} mature user",
                    "tone": "good" if retention["d1"]["eligible"] else "info",
                },
                {
                    "label": "Signup → App D7",
                    "value": f"{retention['d7']['rate']}%" if retention["d7"]["eligible"] else "Yig'ilmoqda",
                    "note": f"{retention['d7']['retained']}/{retention['d7']['eligible']} mature user",
                    "tone": "good" if retention["d7"]["eligible"] else "info",
                },
                {
                    "label": "D1 recovery lift",
                    "value": (
                        "Yig'ilmoqda"
                        if d1_recovery["collecting"]
                        else "Erta signal"
                        if d1_recovery["directional_only"]
                        else f"{d1_recovery['uplift_pp']['open']:+.1f} pp"
                    ),
                    "note": (
                        f"T {d1_recovery['arms']['treatment']['matured']} · "
                        f"C {d1_recovery['arms']['control']['matured']} mature"
                    ),
                    "tone": d1_tone,
                },
                *([_sales_value_card(sales_value)] if sales_value else []),
                {
                    "label": "Direct start → dars ≤2m" if primary_activation is not activation else "Onb → dars ≤2m",
                    "value": f"{primary_activation['lesson_started_rate']}%",
                    "note": f"{primary_activation['lesson_started_2m']}/{primary_activation['lesson_started_eligible']} user",
                    "tone": "good",
                },
                {
                    "label": "Starter start → complete",
                    "value": f"{foundation['completion_rate']}%",
                    "note": f"{foundation['completed_users']}/{foundation['started_users']} unikal user",
                    "tone": "good" if foundation["started_users"] else "info",
                },
                {
                    "label": "Starter first-attempt",
                    "value": f"{foundation_first['accuracy']}%",
                    "note": f"{foundation_first['correct']}/{foundation_first['objectives']} objective",
                    "tone": "good" if foundation_first["objectives"] else "info",
                },
                {
                    "label": "Starter → HSK1 P1/P2/P3",
                    "value": (
                        f"{foundation_parts[1]['rate_from_foundation']}% / "
                        f"{foundation_parts[2]['rate_from_foundation']}% / "
                        f"{foundation_parts[3]['rate_from_foundation']}%"
                    ),
                    "note": (
                        f"{foundation_parts[1]['completed_users']} / "
                        f"{foundation_parts[2]['completed_users']} / "
                        f"{foundation_parts[3]['completed_users']} user"
                    ),
                    "tone": "good" if foundation["completed_users"] else "info",
                },
                {
                    "label": "Checkpoint → paywall",
                    "value": f"{checkpoint_paywall['rate']}%",
                    "note": f"{checkpoint_paywall['paywall_users']}/{checkpoint_paywall['checkpoint_users']} user · 24h",
                    "tone": "info",
                },
                {
                    "label": "Starter D1 learning",
                    "value": f"{foundation_d1['rate']}%" if foundation_d1["eligible"] else "Yig'ilmoqda",
                    "note": f"{foundation_d1['returned']}/{foundation_d1['eligible']} mature user",
                    "tone": "good" if foundation_d1["eligible"] else "info",
                },
                {
                    "label": "Avg session",
                    "value": session_time["avg_text"],
                    "note": f"{session_time['measured_sessions']}/{session_time['sessions']} o'lchandi",
                    "tone": "info",
                },
                {
                    "label": "Lesson time",
                    "value": lesson_time["avg_text"],
                    "note": f"{lesson_time['completed_lessons']} tugagan dars",
                    "tone": "info",
                },
                {
                    "label": "AI chat xabar/user",
                    "value": qa["avg_per_user"],
                    "note": f"{qa['messages']} xabar · {qa['users']} user",
                    "tone": "info",
                },
                {
                    "label": "Voice minutes",
                    "value": voice["minutes_text"],
                    "note": f"{voice['sessions']} yakunlangan session",
                    "tone": "info",
                },
                {
                    "label": "First payment",
                    "value": payment["first_payment_time_text"],
                    "note": f"{payment['first_payment_users']} birinchi to'lov",
                    "tone": "good",
                },
                {
                    "label": "Davr revenue / payer",
                    "value": payment["revenue_per_payer_text"],
                    "note": (
                        f"{payment['paying_users']} payer · LTV emas · "
                        f"{payment['unpriced_payments']} unpriced"
                    ),
                    "tone": "good",
                },
                {
                    "label": "Taglangan CAC",
                    "value": payment["cac_text"],
                    "note": payment["cac_note"],
                    "tone": "warn" if payment["marketing_expense_usd"] else "info",
                },
                {
                    "label": "Unfinished notif",
                    "value": f"{notifications['open_rate']}%" if notifications["sent"] else "Yig'ilmoqda",
                    "note": (
                        f"{notifications['opened_after']} / {notifications['sent']} mature · "
                        f"{notifications['immature_sent']} kutilmoqda"
                    ),
                    "tone": "good" if notifications["sent"] else "info",
                },
            ],
            "retention": retention,
            "activation": activation,
            "d1_recovery": d1_recovery,
            "sales_value": sales_value,
            "session_time": session_time,
            "lesson_time": lesson_time,
            "qa": qa,
            "voice": voice,
            "foundation": foundation,
            "payment": payment,
            "feature_adoption": feature_adoption,
            "notifications": notifications,
        }

    async def _sales_value_stats(
        self,
        *,
        now: datetime,
        since: datetime | None = None,
    ) -> dict:
        assignment_conditions = [
            CourseMiniAppEvent.event_name == "sales_offer_assigned",
            CourseMiniAppEvent.source == SALES_VALUE_EXPERIMENT,
            CourseMiniAppEvent.created_at <= now,
        ]
        if since is not None:
            assignment_conditions.append(CourseMiniAppEvent.created_at >= since)
        assignment_rows = (
            await self.session.execute(
                select(
                    CourseMiniAppEvent.event_name,
                    CourseMiniAppEvent.telegram_id,
                    CourseMiniAppEvent.source,
                    CourseMiniAppEvent.level,
                    CourseMiniAppEvent.lesson_id,
                    CourseMiniAppEvent.lesson_order,
                    CourseMiniAppEvent.payload_json,
                    CourseMiniAppEvent.created_at,
                ).where(*assignment_conditions)
            )
        ).all()
        if not assignment_rows:
            result = _sales_value_experiment([], [], [], now=now)
            if since is not None:
                result["scope"] = {
                    "key": "rolling_window",
                    "since": _dt(since),
                    "note": "Sales A/B overview snapshot oxirgi 30 kun assignmentlari bo'yicha.",
                }
            return result

        assigned_ids = tuple(
            {
                int(row.telegram_id)
                for row in assignment_rows
                if getattr(row, "telegram_id", None)
            }
        )
        assignment_times = [
            _as_utc(row.created_at)
            for row in assignment_rows
            if _as_utc(getattr(row, "created_at", None))
        ]
        if not assigned_ids or not assignment_times:
            result = _sales_value_experiment(
                [tuple(row) for row in assignment_rows],
                [],
                [],
                now=now,
            )
            if since is not None:
                result["scope"] = {
                    "key": "rolling_window",
                    "since": _dt(since),
                    "note": "Sales A/B overview snapshot oxirgi 30 kun assignmentlari bo'yicha.",
                }
            return result
        earliest_assignment = min(assignment_times)

        outcome_names = (
            "sales_bridge_seen",
            "sales_bridge_cta",
            "sales_offer_seen",
            "sales_offer_dismissed",
            "paywall_seen",
            "foundation_completed",
            *tuple(SALES_VALUE_MEANINGFUL_EVENTS),
        )
        outcome_rows = (
            await self.session.execute(
                select(
                    CourseMiniAppEvent.event_name,
                    CourseMiniAppEvent.telegram_id,
                    CourseMiniAppEvent.source,
                    CourseMiniAppEvent.level,
                    CourseMiniAppEvent.lesson_id,
                    CourseMiniAppEvent.lesson_order,
                    CourseMiniAppEvent.payload_json,
                    CourseMiniAppEvent.created_at,
                ).where(
                    CourseMiniAppEvent.telegram_id.in_(assigned_ids),
                    CourseMiniAppEvent.event_name.in_(outcome_names),
                    CourseMiniAppEvent.created_at >= earliest_assignment,
                    CourseMiniAppEvent.created_at <= now,
                )
            )
        ).all()
        funnel_rows = (
            await self.session.execute(
                select(
                    ConversionFunnelEvent.event_name,
                    ConversionFunnelEvent.telegram_id,
                    ConversionFunnelEvent.payment_id,
                    ConversionFunnelEvent.payload_json,
                    ConversionFunnelEvent.created_at,
                ).where(
                    ConversionFunnelEvent.telegram_id.in_(assigned_ids),
                    ConversionFunnelEvent.event_name.in_(
                        ("checkout_opened", "payment_screenshot_submitted", "payment_approved")
                    ),
                    ConversionFunnelEvent.created_at >= earliest_assignment,
                    ConversionFunnelEvent.created_at <= now,
                )
            )
        ).all()
        payment_rows = (
            await self.session.execute(
                select(
                    Payment.id,
                    Payment.user_telegram_id,
                    Payment.payment_status,
                    Payment.amount,
                    Payment.currency,
                    Payment.base_amount,
                    Payment.reviewed_at,
                    Payment.submitted_at,
                ).where(
                    Payment.user_telegram_id.in_(assigned_ids),
                    Payment.payment_status.in_(("pending", "approved", "rejected")),
                )
            )
        ).all()
        error_rows = (
            await self.session.execute(
                select(User.telegram_id, Message.created_at)
                .select_from(Message)
                .join(User, User.id == Message.user_id)
                .where(
                    User.telegram_id.in_(assigned_ids),
                    Message.content_type == "app_error_context",
                    Message.created_at >= earliest_assignment,
                    Message.created_at <= now,
                )
            )
        ).all()
        result = _sales_value_experiment(
            [tuple(row) for row in assignment_rows] + [tuple(row) for row in outcome_rows],
            [tuple(row) for row in funnel_rows],
            [tuple(row) for row in payment_rows],
            now=now,
            error_rows=[tuple(row) for row in error_rows],
        )
        if since is not None:
            result["scope"] = {
                "key": "rolling_window",
                "since": _dt(since),
                "note": "Sales A/B overview snapshot oxirgi 30 kun assignmentlari bo'yicha.",
            }
        return result

    async def _d1_recovery_stats(self, *, since: datetime | None, now: datetime) -> dict:
        event_names = (
            "d1_recovery_assigned",
            "d1_recovery_sent",
            "d1_recovery_send_failed",
            "miniapp_opened",
            "lesson_completed",
            "book_lesson_completed",
        )
        conditions = [CourseMiniAppEvent.event_name.in_(event_names)]
        if since is not None:
            conditions.append(CourseMiniAppEvent.created_at >= since)
        rows = (
            await self.session.execute(
                select(
                    CourseMiniAppEvent.event_name,
                    CourseMiniAppEvent.telegram_id,
                    CourseMiniAppEvent.source,
                    CourseMiniAppEvent.level,
                    CourseMiniAppEvent.lesson_id,
                    CourseMiniAppEvent.lesson_order,
                    CourseMiniAppEvent.payload_json,
                    CourseMiniAppEvent.created_at,
                ).where(*conditions)
            )
        ).all()
        assigned_ids = {
            int(row.telegram_id)
            for row in rows
            if row.telegram_id
            and row.event_name == "d1_recovery_assigned"
            and row.source == "d1_recovery_v1"
        }
        block_rows = []
        if assigned_ids:
            block_rows = (
                await self.session.execute(
                    select(User.telegram_id, User.bot_blocked_at).where(
                        User.telegram_id.in_(tuple(assigned_ids))
                    )
                )
            ).all()
        return _d1_recovery_experiment(
            [tuple(row) for row in rows],
            [tuple(row) for row in block_rows],
            now=now,
        )

    async def _activation_stats(self, *, since: datetime | None, now: datetime) -> dict:
        event_names = (
            "onboarding_completed",
            "lesson_started",
            "section_completed",
            "lesson_completed",
            "book_lesson_completed",
        )
        conditions = [CourseMiniAppEvent.event_name.in_(event_names)]
        if since is not None:
            conditions.append(CourseMiniAppEvent.created_at >= since)
        rows = (
            await self.session.execute(
                select(
                    CourseMiniAppEvent.event_name,
                    CourseMiniAppEvent.telegram_id,
                    CourseMiniAppEvent.created_at,
                    CourseMiniAppEvent.payload_json,
                ).where(*conditions)
            )
        ).all()
        return _activation_funnel([tuple(row) for row in rows], now=now)

    async def _retention_stats(self, *, since: datetime | None, now: datetime) -> dict:
        stmt = select(User.telegram_id, User.created_at).select_from(User)
        if since is not None:
            stmt = stmt.where(User.created_at >= since)
        rows = (await self.session.execute(stmt)).all()

        created_by_user = {
            int(telegram_id): _as_utc(created_at)
            for telegram_id, created_at in rows
            if telegram_id and _as_utc(created_at)
        }
        opens_by_user: dict[int, list[datetime]] = defaultdict(list)
        if created_by_user:
            event_conditions = [
                CourseMiniAppEvent.telegram_id.in_(tuple(created_by_user)),
                CourseMiniAppEvent.event_name == "miniapp_opened",
            ]
            earliest_created = min(created_by_user.values())
            event_conditions.append(CourseMiniAppEvent.created_at >= earliest_created)
            open_rows = (
                await self.session.execute(
                    select(CourseMiniAppEvent.telegram_id, CourseMiniAppEvent.created_at).where(
                        *event_conditions
                    )
                )
            ).all()
            for telegram_id, opened_at in open_rows:
                opened = _as_utc(opened_at)
                if opened:
                    opens_by_user[int(telegram_id)].append(opened)

        return {
            "d1": _cohort_retention(
                created_by_user=created_by_user,
                opens_by_user=opens_by_user,
                days=1,
                now=now,
            ),
            "d7": _cohort_retention(
                created_by_user=created_by_user,
                opens_by_user=opens_by_user,
                days=7,
                now=now,
            ),
            "explain": (
                "D1/D7 retention = shu davrda ro'yxatdan o'tgan userlardan signupdan keyingi aynan "
                "24–48 soat / 168–192 soat oynasida Mini Appni qayta ochganlar. To'liq oynasi tugamagan "
                "userlar denominatorga kirmaydi."
            ),
        }

    async def _miniapp_session_time(self, *, since: datetime | None) -> dict:
        conditions = [
            CourseMiniAppEvent.session_id.is_not(None),
            CourseMiniAppEvent.session_id != "",
        ]
        if since is not None:
            conditions.append(CourseMiniAppEvent.created_at >= since)
        rows = (
            await self.session.execute(
                select(
                    CourseMiniAppEvent.telegram_id,
                    CourseMiniAppEvent.session_id,
                    CourseMiniAppEvent.created_at,
                ).where(*conditions)
            )
        ).all()
        sessions, durations = _miniapp_session_durations([tuple(row) for row in rows])
        avg_seconds = round(sum(durations) / len(durations)) if durations else 0
        return {
            "sessions": sessions,
            "measured_sessions": len(durations),
            "avg_seconds": avg_seconds,
            "avg_text": _duration_text(avg_seconds),
            "total_text": _duration_text(sum(durations)),
            "explain": "Mini App session vaqti session_id ichidagi eventlar oralig'idan olinadi; 30 daqiqadan uzun idle yangi segment, bitta eventli segment countda bor, lekin averagega kirmaydi.",
        }

    async def _lesson_time(self, *, since: datetime | None) -> dict:
        event_names = (
            "lesson_started",
            "book_lesson_completed",
            "lesson_completed",
        )
        conditions = [CourseMiniAppEvent.event_name.in_(event_names)]
        if since is not None:
            conditions.append(CourseMiniAppEvent.created_at >= since - timedelta(hours=8))
        rows = (
            await self.session.execute(
                select(
                    CourseMiniAppEvent.telegram_id,
                    CourseMiniAppEvent.level,
                    CourseMiniAppEvent.lesson_id,
                    CourseMiniAppEvent.lesson_order,
                    CourseMiniAppEvent.session_id,
                    CourseMiniAppEvent.event_name,
                    CourseMiniAppEvent.created_at,
                ).where(*conditions)
            )
        ).all()
        durations = _lesson_attempt_durations(
            [tuple(row) for row in rows],
            completion_since=since,
        )
        avg_seconds = round(sum(durations) / len(durations)) if durations else 0
        return {
            "completed_lessons": len(durations),
            "avg_seconds": avg_seconds,
            "avg_text": _duration_text(avg_seconds),
            "total_text": _duration_text(sum(durations)),
            "explain": "Lesson time = bir sessiondagi eng yaqin lesson_started dan lesson_completed/book_lesson_completed gacha; abandon retry va qisman sectionlar yakunlangan dars deb sanalmaydi.",
        }

    async def _qa_message_stats(self, *, since: datetime | None) -> dict:
        conditions = [Message.role == "user", Message.content_type == "text"]
        if since is not None:
            conditions.append(Message.created_at >= since)
        row = (
            await self.session.execute(
                select(
                    func.count(Message.id).label("messages"),
                    func.count(func.distinct(Message.user_id)).label("users"),
                ).where(*conditions)
            )
        ).one()
        messages = int(row.messages or 0)
        users = int(row.users or 0)
        return {
            "messages": messages,
            "users": users,
            "avg_per_user": round(messages / users, 2) if users else 0,
            "explain": "AI chat message/user = user yuborgan text xabarlar / shu davrdagi AI chat aktiv userlar.",
        }

    async def _voice_minutes(self, *, since: datetime | None) -> dict:
        conditions = [VoicePracticeSession.ended_at.is_not(None)]
        if since is not None:
            conditions.append(VoicePracticeSession.started_at >= since)
        rows = (
            await self.session.execute(
                select(VoicePracticeSession.started_at, VoicePracticeSession.ended_at).where(*conditions)
            )
        ).all()
        durations = [_duration_seconds(start, end) for start, end in rows]
        durations = [seconds for seconds in durations if seconds > 0]
        total_seconds = sum(durations)
        avg_seconds = round(total_seconds / len(durations)) if durations else 0
        return {
            "sessions": len(durations),
            "seconds": total_seconds,
            "minutes": round(total_seconds / 60, 1),
            "minutes_text": f"{round(total_seconds / 60, 1)} min" if total_seconds else "0 min",
            "avg_text": _duration_text(avg_seconds),
            "explain": "Voice minutes faqat yakunlangan VoicePracticeSession started_at→ended_at oralig'i bo'yicha hisoblanadi.",
        }

    async def _payment_advanced_stats(self, *, since: datetime | None) -> dict:
        rows = (
            await self.session.execute(
                select(
                    Payment.user_telegram_id,
                    Payment.amount,
                    Payment.currency,
                    Payment.base_amount,
                    Payment.reviewed_at,
                    Payment.submitted_at,
                ).where(Payment.payment_status == "approved")
            )
        ).all()
        approved = []
        for user_id, amount, currency, base_amount, reviewed_at, submitted_at in rows:
            at = _as_utc(reviewed_at or submitted_at)
            if not at:
                continue
            usd = _amount_to_usd(amount, currency, base_amount=base_amount)
            approved.append(
                {
                    "user_id": int(user_id),
                    "at": at,
                    "usd": float(usd or 0.0),
                    "priced": usd is not None,
                }
            )
        in_period = [item for item in approved if since is None or item["at"] >= since]
        revenue_usd = sum(item["usd"] for item in in_period if item["priced"])
        unpriced_payments = len([item for item in in_period if not item["priced"]])
        paying_users = len({item["user_id"] for item in in_period})
        revenue_per_payer = revenue_usd / paying_users if paying_users else 0.0

        first_by_user: dict[int, dict] = {}
        for item in sorted(approved, key=lambda value: value["at"]):
            first_by_user.setdefault(item["user_id"], item)
        first_in_period = [
            item for item in first_by_user.values()
            if since is None or item["at"] >= since
        ]
        created_map = await self._user_created_map([item["user_id"] for item in first_in_period])
        first_payment_durations = []
        for item in first_in_period:
            created_at = created_map.get(item["user_id"])
            seconds = _duration_seconds(created_at, item["at"], cap_seconds=3650 * 24 * 60 * 60)
            if seconds > 0:
                first_payment_durations.append(seconds)
        avg_first_seconds = round(sum(first_payment_durations) / len(first_payment_durations)) if first_payment_durations else 0

        marketing_expense_usd = await self._marketing_expense_usd(since=since)
        new_paying_users = len(first_in_period)
        cac = marketing_expense_usd / new_paying_users if new_paying_users else 0.0
        funnel = await self._payment_funnel(since=since)

        return {
            "revenue_usd": round(revenue_usd, 2),
            "revenue_text": _usd(revenue_usd),
            "paying_users": paying_users,
            "unpriced_payments": unpriced_payments,
            "revenue_per_payer_usd": round(revenue_per_payer, 2),
            "revenue_per_payer_text": _usd(revenue_per_payer),
            # Deprecated aliases retained for older clients; this is ARPPU,
            # not cohort lifetime value.
            "ltv_usd": round(revenue_per_payer, 2),
            "ltv_text": _usd(revenue_per_payer),
            "first_payment_users": new_paying_users,
            "first_payment_time_seconds": avg_first_seconds,
            "first_payment_time_text": _duration_text(avg_first_seconds),
            "marketing_expense_usd": round(marketing_expense_usd, 2),
            "marketing_expense_text": _usd(marketing_expense_usd),
            "cac_usd": round(cac, 2),
            "cac_text": _usd(cac) if marketing_expense_usd else "—",
            "cac_note": (
                f"{new_paying_users} yangi payer · note/source bo'yicha taglangan expense"
                if marketing_expense_usd
                else "marketing xarajat kiritilmagan"
            ),
            "explain": (
                "Revenue/payer = tanlangan davrdagi priced approved revenue ÷ shu davrdagi unikal payer; bu LTV emas. "
                f"Narxi aniqlanmagan payment: {unpriced_payments}. "
                "Taglangan CAC faqat portfolio note/source ichida marketing/reklama deb topilgan xarajatlardan hisoblanadi."
            ),
            "funnel": funnel,
        }

    async def _user_created_map(self, telegram_ids: list[int]) -> dict[int, datetime]:
        ids = list({int(value) for value in telegram_ids if value})
        if not ids:
            return {}
        rows = (
            await self.session.execute(
                select(User.telegram_id, User.created_at).where(User.telegram_id.in_(ids))
            )
        ).all()
        return {int(telegram_id): _as_utc(created_at) for telegram_id, created_at in rows}

    async def _marketing_expense_usd(self, *, since: datetime | None) -> float:
        text = func.lower(func.coalesce(PortfolioTransaction.note, ""))
        source = func.lower(func.coalesce(PortfolioTransaction.source, ""))
        patterns = ("%marketing%", "%reklama%", "%реклама%", "%ads%", "%target%", "%таргет%", "%cac%", "%smm%", "%traffic%")
        conditions = [
            PortfolioTransaction.transaction_type == "expense",
            or_(
                *[text.like(pattern) for pattern in patterns],
                *[source.like(pattern) for pattern in patterns],
            ),
        ]
        if since is not None:
            conditions.append(PortfolioTransaction.created_at >= since)
        value = (
            await self.session.execute(
                select(func.coalesce(func.sum(PortfolioTransaction.amount_usd), 0.0)).where(*conditions)
            )
        ).scalar()
        return float(value or 0.0)

    async def _payment_funnel(self, *, since: datetime | None) -> dict:
        event_names = ("checkout_opened", "payment_screenshot_submitted", "payment_approved")
        conditions = [ConversionFunnelEvent.event_name.in_(event_names)]
        if since is not None:
            conditions.append(ConversionFunnelEvent.created_at >= since)
        rows = (
            await self.session.execute(
                select(
                    ConversionFunnelEvent.event_name,
                    ConversionFunnelEvent.telegram_id,
                    ConversionFunnelEvent.payment_id,
                    ConversionFunnelEvent.payload_json,
                    ConversionFunnelEvent.created_at,
                )
                .where(*conditions)
            )
        ).all()
        funnel = _payment_attempt_funnel([tuple(row) for row in rows])
        status_counts = await self._payment_status_counts(since)
        funnel["payment_status"] = status_counts
        funnel["explain"] = (
            "Har bosqich bir xil checkout attempt_id va payment_id orqali bog'langan. "
            "Yangi attempt eventlari bo'lmasa 'ma'lumot yig'ilmoqda' ko'rsatiladi."
        )
        return funnel

    async def _feature_adoption(self, *, since: datetime | None, now: datetime) -> dict:
        paid_denominator = await self._feature_denominator(paid=True, since=since, now=now)
        free_denominator = await self._feature_denominator(paid=False, since=since, now=now)
        rows = [
            await self._course_feature_row("Darslar", ("lesson_started", "section_started"), since, now, paid_denominator, free_denominator),
            await self._course_feature_row("Testlar", ("test_started", "test_completed"), since, now, paid_denominator, free_denominator),
            await self._course_feature_row("Mashqlar", ("training_started", "training_completed"), since, now, paid_denominator, free_denominator),
            await self._course_feature_row("Xatolar takrori", ("mistake_review_started", "mistake_review_completed"), since, now, paid_denominator, free_denominator),
            await self._ai_feature_row("AI chat aktiv user", since, now, paid_denominator, free_denominator),
            await self._voice_feature_row("Voice roleplay", since, now, paid_denominator, free_denominator),
        ]
        rows.sort(key=lambda item: (item["paid"] + item["free"], item["paid"]), reverse=True)
        return {
            "paid_denominator": paid_denominator,
            "free_denominator": free_denominator,
            "rows": rows,
            "explain": "Feature adoption paid/free = shu davrda feature'ni ishlatgan unik userlar, hozirgi obuna holati bo'yicha ajratilgan.",
        }

    def _paid_user_conditions(self, now: datetime) -> list:
        return [
            User.payment_status == "approved",
            User.status == "active",
            User.end_date.is_not(None),
            User.end_date > now,
        ]

    def _free_user_condition(self, now: datetime):
        return or_(
            User.payment_status != "approved",
            User.status != "active",
            User.end_date.is_(None),
            User.end_date <= now,
        )

    async def _feature_denominator(self, *, paid: bool, since: datetime | None, now: datetime) -> int:
        conditions = self._paid_user_conditions(now) if paid else [self._free_user_condition(now)]
        if since is not None:
            conditions.append(User.last_active_at >= since)
        return await self._count_users(*conditions)

    async def _course_feature_row(
        self,
        label: str,
        event_names: tuple[str, ...],
        since: datetime | None,
        now: datetime,
        paid_denominator: int,
        free_denominator: int,
    ) -> dict:
        paid = await self._count_course_feature_users(event_names, since, now, paid=True)
        free = await self._count_course_feature_users(event_names, since, now, paid=False)
        return self._feature_row(label, paid, free, paid_denominator, free_denominator)

    async def _count_course_feature_users(self, event_names: tuple[str, ...], since: datetime | None, now: datetime, *, paid: bool) -> int:
        conditions = [CourseMiniAppEvent.event_name.in_(event_names)]
        if since is not None:
            conditions.append(CourseMiniAppEvent.created_at >= since)
        user_conditions = self._paid_user_conditions(now) if paid else [self._free_user_condition(now)]
        value = (
            await self.session.execute(
                select(func.count(func.distinct(CourseMiniAppEvent.telegram_id)))
                .select_from(CourseMiniAppEvent)
                .join(User, User.telegram_id == CourseMiniAppEvent.telegram_id)
                .where(*conditions, *user_conditions)
            )
        ).scalar()
        return int(value or 0)

    async def _ai_feature_row(self, label: str, since: datetime | None, now: datetime, paid_denominator: int, free_denominator: int) -> dict:
        paid = await self._count_ai_feature_users(since, now, paid=True)
        free = await self._count_ai_feature_users(since, now, paid=False)
        return self._feature_row(label, paid, free, paid_denominator, free_denominator)

    async def _count_ai_feature_users(self, since: datetime | None, now: datetime, *, paid: bool) -> int:
        conditions = [AIUsageEvent.source == "qa"]
        if since is not None:
            conditions.append(AIUsageEvent.created_at >= since)
        user_conditions = self._paid_user_conditions(now) if paid else [self._free_user_condition(now)]
        value = (
            await self.session.execute(
                select(func.count(func.distinct(AIUsageEvent.user_telegram_id)))
                .select_from(AIUsageEvent)
                .join(User, User.telegram_id == AIUsageEvent.user_telegram_id)
                .where(*conditions, *user_conditions)
            )
        ).scalar()
        return int(value or 0)

    async def _voice_feature_row(self, label: str, since: datetime | None, now: datetime, paid_denominator: int, free_denominator: int) -> dict:
        paid = await self._count_voice_feature_users(since, now, paid=True)
        free = await self._count_voice_feature_users(since, now, paid=False)
        return self._feature_row(label, paid, free, paid_denominator, free_denominator)

    async def _count_voice_feature_users(self, since: datetime | None, now: datetime, *, paid: bool) -> int:
        conditions = []
        if since is not None:
            conditions.append(VoicePracticeSession.started_at >= since)
        user_conditions = self._paid_user_conditions(now) if paid else [self._free_user_condition(now)]
        value = (
            await self.session.execute(
                select(func.count(func.distinct(VoicePracticeSession.user_telegram_id)))
                .select_from(VoicePracticeSession)
                .join(User, User.telegram_id == VoicePracticeSession.user_telegram_id)
                .where(*conditions, *user_conditions)
            )
        ).scalar()
        return int(value or 0)

    @staticmethod
    def _feature_row(label: str, paid: int, free: int, paid_denominator: int, free_denominator: int) -> dict:
        return {
            "label": label,
            "paid": paid,
            "free": free,
            "total": paid + free,
            "paid_rate": _pct(paid, paid_denominator),
            "free_rate": _pct(free, free_denominator),
        }

    async def _notification_open_proxy(self, *, since: datetime | None, now: datetime) -> dict:
        sent_conditions = [CourseMiniAppEvent.event_name == "motivation_lesson_unfinished_sent"]
        open_conditions = [
            CourseMiniAppEvent.event_name == "miniapp_opened",
            CourseMiniAppEvent.source == "motivation_reminder",
        ]
        if since is not None:
            sent_conditions.append(CourseMiniAppEvent.created_at >= since)
            open_conditions.append(CourseMiniAppEvent.created_at >= since)
        sent_rows = (
            await self.session.execute(
                select(CourseMiniAppEvent.telegram_id, CourseMiniAppEvent.created_at).where(*sent_conditions)
            )
        ).all()
        open_rows = (
            await self.session.execute(
                select(CourseMiniAppEvent.telegram_id, CourseMiniAppEvent.created_at).where(*open_conditions)
            )
        ).all()
        result = _matured_notification_open_proxy(
            [tuple(row) for row in sent_rows],
            [tuple(row) for row in open_rows],
            now=now,
        )
        result["explain"] = (
            "Faqat 48 soatlik oynasi to'liq tugagan unfinished-lesson reminderlar denominatorga kiradi. "
            "source=motivation_reminder open eng yaqin oldingi reminderga bir marta bog'lanadi."
        )
        return result

    async def _required_channels(self) -> list[dict]:
        rows = (await self.session.execute(
            select(RequiredChannel).order_by(RequiredChannel.created_at.desc()).limit(20)
        )).scalars().all()
        return [
            {
                "id": item.id,
                "title": item.title,
                "chat_id": item.chat_id,
                "enabled": bool(item.is_active),
                "link": item.invite_link,
            }
            for item in rows
        ]

    async def _count_active_required_channels(self) -> int:
        value = (
            await self.session.execute(
                select(func.count()).select_from(RequiredChannel).where(
                    RequiredChannel.is_active.is_(True)
                )
            )
        ).scalar()
        return int(value or 0)

    async def _ad_summary(self) -> dict:
        now = datetime.now(timezone.utc)
        total = (await self.session.execute(select(func.count()).select_from(AdCampaign))).scalar() or 0
        active = (await self.session.execute(
            select(func.count()).select_from(AdCampaign).where(
                AdCampaign.is_active == True,  # noqa: E712
                AdCampaign.starts_at <= now,
                AdCampaign.ends_at >= now,
            )
        )).scalar() or 0
        deliveries = (await self.session.execute(
            select(AdCampaignDelivery.status, func.count().label("cnt")).group_by(AdCampaignDelivery.status)
        )).fetchall()
        by_status = {str(row.status or "—"): int(row.cnt or 0) for row in deliveries}
        latest = (await self.session.execute(
            select(AdCampaign).order_by(AdCampaign.created_at.desc()).limit(8)
        )).scalars().all()
        return {
            "total": int(total),
            "active": int(active),
            "delivered": int(by_status.get("delivered", 0) + by_status.get("sent", 0)),
            "failed": int(by_status.get("failed", 0) or 0),
            "by_status": by_status,
            "latest": [
                {
                    "id": item.id,
                    "title": item.title,
                    "enabled": bool(item.is_active),
                    "rounds_sent": item.rounds_sent,
                    "send_count_total": item.send_count_total,
                    "ends_at": _dt(item.ends_at),
                }
                for item in latest
            ],
        }

    async def _feedback_summary(self) -> dict:
        rows = (await self.session.execute(
            select(BotFeedback.status, func.count().label("cnt")).group_by(BotFeedback.status)
        )).fetchall()
        values = {str(row.status or "—"): int(row.cnt or 0) for row in rows}
        return {
            "pending": values.get("pending", 0),
            "completed": values.get("completed", 0),
            "values": values,
        }

    async def _course_xp_user_ids_since(self, since: datetime) -> set[int]:
        rows = (
            await self.session.execute(
                select(CourseXpEvent.user_id)
                .join(User, User.id == CourseXpEvent.user_id)
                .where(CourseXpEvent.created_at >= since, _bot_not_blocked_filter())
                .group_by(CourseXpEvent.user_id)
            )
        ).all()
        return {int(row.user_id) for row in rows if row.user_id}

    async def _course_profile_activity_user_ids_since(self, start_date) -> set[int]:
        rows = (
            await self.session.execute(
                select(CourseMiniAppProfile.user_id)
                .join(User, User.id == CourseMiniAppProfile.user_id)
                .where(CourseMiniAppProfile.last_activity_date >= start_date, _bot_not_blocked_filter())
                .group_by(CourseMiniAppProfile.user_id)
            )
        ).all()
        return {int(row.user_id) for row in rows if row.user_id}

    async def _course_streak_user_count(self, min_streak: int) -> int:
        value = (
            await self.session.execute(
                select(func.count(func.distinct(CourseMiniAppProfile.user_id)))
                .select_from(CourseMiniAppProfile)
                .join(User, User.id == CourseMiniAppProfile.user_id)
                .where(CourseMiniAppProfile.current_streak >= int(min_streak), _bot_not_blocked_filter())
            )
        ).scalar()
        return int(value or 0)

    async def _course_activity_hot_leads(
        self,
        *,
        today_start: datetime,
        hot_since: datetime,
        today_date,
        two_day_start_date,
    ) -> dict:
        today_ids = (
            await self._course_xp_user_ids_since(today_start)
        ) | (
            await self._course_profile_activity_user_ids_since(today_date)
        )
        two_day_ids = (
            await self._course_xp_user_ids_since(hot_since)
        ) | (
            await self._course_profile_activity_user_ids_since(two_day_start_date)
        )
        streak_3 = await self._course_streak_user_count(3)
        streak_7 = await self._course_streak_user_count(7)
        return {
            "today_users": len(today_ids),
            "last_2_days_users": len(two_day_ids),
            "streak_3_users": streak_3,
            "streak_7_users": streak_7,
            "explain": (
                "Course faol userlar CourseXpEvent.created_at va CourseMiniAppProfile.last_activity_date "
                "unionidan olinadi; streak CourseMiniAppProfile.current_streak bo'yicha sanaladi."
            ),
        }

    async def _subscription_sources(self, week_ago: datetime) -> list[dict]:
        rows = await SubscriptionEntryAnalyticsService(self.session).source_stats(
            week_ago=week_ago,
            limit=8,
        )
        return [
            {
                "source": row.source,
                "label": self._source_label(row.label),
                "unique_all": row.unique_all,
                "unique_week": row.unique_week,
                "total_all": row.total_all,
                "total_week": row.total_week,
            }
            for row in rows
        ]

    @staticmethod
    def _source_label(label: str) -> str:
        replacements = {
            "Mini App": "мини илова",
            "Course": "Курс",
            "Voice": "овозли AI",
            "Release feedback": "янгилик фикри",
            "Feedback": "фикр",
            "Daily limit": "кунлик лимит",
            "QA limit": "савол лимити",
            "Kurs paywall": "курс обуна ойнаси",
            "Paywall": "обуна ойнаси",
            "Unknown": "Номаълум",
        }
        result = label
        for source, target in replacements.items():
            result = result.replace(source, target)
        return result

    async def _price_rows(self) -> list[dict]:
        prices = await SubscriptionPriceService(self.session).all_prices()
        return [
            {
                "method": _method_label(item.payment_method),
                "plan": _plan_label(item.plan_type),
                "amount": format_subscription_price(item.amount, item.currency),
            }
            for item in prices
        ]

    async def _latest_users(
        self,
        now: datetime,
        *,
        today_start: datetime,
        hot_since: datetime,
    ) -> list[dict]:
        pending_user_ids = {
            int(value)
            for value in (
                await self.session.execute(
                    select(func.distinct(Payment.user_telegram_id)).where(
                        Payment.payment_status == "pending"
                    )
                )
            ).scalars().all()
            if value
        }
        rows = (await self.session.execute(
            select(User, CourseMiniAppProfile)
            .outerjoin(CourseMiniAppProfile, CourseMiniAppProfile.user_id == User.id)
            .order_by(User.last_active_at.desc())
            .limit(120)
        )).all()
        return [
            {
                "id": item.telegram_id,
                "name": item.full_name or "Номсиз",
                "username": item.username,
                "language": _language_label(item.language),
                "level": _level_label(item.level),
                "mode": "Курс" if item.learning_mode == "course" else "Савол-жавоб",
                "status": item.status,
                "status_label": _status_label(item.status),
                "bot_blocked": BotBlockStatusService.is_bot_blocked(item),
                "bot_blocked_at": _dt(item.bot_blocked_at),
                "bot_unblocked_at": _dt(item.bot_unblocked_at),
                "last_bot_block_check_at": _dt(item.last_bot_block_check_at),
                "payment_status": item.payment_status,
                "payment_label": _payment_label(item.payment_status),
                "has_pending_payment": item.telegram_id in pending_user_ids,
                "plan": _plan_label(item.selected_plan_type),
                "method": _method_label(item.payment_method),
                "end_date": _dt(item.end_date),
                "last_active": _ago(item.last_active_at, now=now),
                "active_today": is_admin_active_today(item, today_start),
                "hot_lead": (
                    is_admin_hot_lead(item, hot_since)
                    and item.telegram_id not in pending_user_ids
                ),
                "questions": f"{item.questions_used}/{item.question_limit}",
                "bonus_left": max((item.bonus_questions or 0) - (item.bonus_questions_used or 0), 0),
                "streak": int(getattr(profile, "current_streak", 0) or 0),
                "course_last_activity_date": str(getattr(profile, "last_activity_date", "") or ""),
            }
            for item, profile in rows
        ]

    async def _latest_payments(self) -> list[dict]:
        pending_rows = (
            await self.session.execute(
                select(Payment, User)
                .outerjoin(User, User.telegram_id == Payment.user_telegram_id)
                .where(Payment.payment_status == "pending")
                .order_by(Payment.submitted_at.desc())
            )
        ).all()
        recent_rows = (
            await self.session.execute(
                select(Payment, User)
                .outerjoin(User, User.telegram_id == Payment.user_telegram_id)
                .where(Payment.payment_status.in_(("approved", "rejected")))
                .order_by(func.coalesce(Payment.reviewed_at, Payment.submitted_at).desc())
                .limit(60)
            )
        ).all()
        rows = [*pending_rows, *recent_rows]
        result = []
        for payment, user in rows:
            result.append(
                {
                    "id": payment.id,
                    "telegram_id": payment.user_telegram_id,
                    "name": getattr(user, "full_name", None) or "Номсиз",
                    "username": getattr(user, "username", None),
                    "status": payment.payment_status,
                    "status_label": _payment_label(payment.payment_status),
                    "plan": _plan_label(payment.plan_type),
                    "method": _method_label(payment.payment_method),
                    "amount": format_subscription_price(payment.amount, payment.currency),
                    "submitted_at": _dt(payment.submitted_at),
                    "reviewed_at": _dt(payment.reviewed_at),
                    "has_screenshot": bool(payment.screenshot_file_id),
                    "comment": payment.admin_comment,
                }
            )
        return result

    @staticmethod
    def _queue(*, pending_payments: int, expiring_soon: int, expired_hot: int, ad_summary: dict) -> list[dict]:
        return [
            {
                "title": "Тўлов текшируви",
                "note": f"{pending_payments} та тўлов админ тасдиғини кутяпти",
                "priority": "ҳозир" if pending_payments else "тинч",
                "section": "payments",
            },
            {
                "title": "Обунаси тугаётганлар",
                "note": f"{expiring_soon} фойдаланувчига эслатма керак",
                "priority": "муҳим" if expiring_soon else "тинч",
                "section": "users",
            },
            {
                "title": "Қайта сотиш сегменти",
                "note": f"{expired_hot} муддати тугаган, лекин ҳафтада фаол",
                "priority": "иссиқ" if expired_hot else "тинч",
                "section": "users",
            },
            {
                "title": "Реклама ҳолати",
                "note": f"{ad_summary.get('active', 0)} та фаол кампания",
                "priority": "кузатиш",
                "section": "ads",
            },
        ]

    @staticmethod
    def _modules() -> list[dict]:
        return [
            {"key": "stats", "icon": "📊", "title": "Статистика", "note": "Умумий ҳисобот ва конверсия", "section": "statistics", "callback": "adm:stats"},
            {"key": "user_search", "icon": "🔎", "title": "Фойдаланувчи қидириш", "note": "ID ёки username бўйича Mini App ичида қидириш", "section": "users", "callback": "adm:user_search_info"},
            {"key": "portfolio", "icon": "💼", "title": "Портфель", "note": "Тушум, харажат ва соф фойдани бошқариш", "section": "settings", "callback": "adm:portfolio"},
            {"key": "prices", "icon": "💳", "title": "Обуна нархлари", "note": "Visa/карта, Alipay, WeChat нархларини таҳрирлаш", "section": "settings", "callback": "adm:prices"},
            {"key": "course_access", "icon": "📚", "title": "Курс access", "note": "Дарс paywall, реклама ёки вақтинча free режими", "section": "settings", "callback": "adm:course_access"},
            {"key": "course_sales_experiment", "icon": "🧭", "title": "HSK сотув A/B", "note": "sales_value_v1 kill switch ва rollout фоизи", "section": "settings", "callback": "adm:course_sales_experiment"},
            {"key": "app_promo", "icon": "💻", "title": "App рекламаси", "note": "Mini App очилганда ва реклама жойларида илова промоси", "section": "settings", "callback": "adm:app_promo"},
            {"key": "channels", "icon": "📣", "title": "Мажбурий канал обунаси", "note": "Канал линки, ёқиш/ўчириш ва рўйхат", "section": "settings", "callback": "adm:channels"},
            {"key": "delete_user", "icon": "🗑", "title": "Фойдаланувчини ўчириш", "note": "Хавфли амал, ID билан тасдиқланади", "section": "users", "callback": "adm:deleteuser_info"},
            {"key": "broadcast", "icon": "📢", "title": "Оммавий хабар", "note": "Сегмент танлаб матн юбориш", "section": "settings", "callback": "adm:broadcast_info"},
            {"key": "ads", "icon": "📣", "title": "Реклама кампанияси", "note": "Матнли реклама яратиш ва ҳолатни кўриш", "section": "settings", "callback": "adm:ads_panel"},
            {"key": "release_feedback", "icon": "🆕", "title": "Янгилик фикри", "note": "Янгилик фикри кампаниясини режалаш", "section": "settings", "callback": "adm:release_feedback"},
            {"key": "discount", "icon": "🎁", "title": "Чегирма бошқаруви", "note": "Чегирма кампаниясини яратиш ва кузатиш", "section": "settings", "callback": "adm:discount_panel"},
            {"key": "partners", "icon": "🤝", "title": "Ҳамкорлар", "note": "Ариза, тўлов ва ҳамкор статистикаси", "section": "settings", "callback": "adm:partners"},
            {"key": "help", "icon": "🆘", "title": "Ёрдам созламалари", "note": "Админ алоқа ва видео линклар", "section": "settings", "callback": "adm:help_settings"},
            {"key": "give_access", "icon": "✅", "title": "Обуна бериш", "note": "Фойдаланувчига қўлда рухсат бериш", "section": "users", "callback": "adm:giveaccess_info"},
            {"key": "audio", "icon": "🎵", "title": "Аудио бошқаруви", "note": "Курс аудио файлларини текшириш", "section": "settings", "callback": "adm:audio_panel"},
        ]

    @staticmethod
    def _monitor(
        *,
        active_week: int,
        active_24h: int,
        pending_payments: int,
        approved_total_text: str,
        miniapp_course,
        ad_summary: dict,
        channels_enabled: bool,
        active_channels: int,
    ) -> dict:
        return {
            "ticker": [
                {"label": "Ҳафталик фаол", "value": active_week, "tone": "up"},
                {"label": "24 соат фаол", "value": active_24h, "tone": "up"},
                {"label": "Текширувдаги тўлов", "value": pending_payments, "tone": "warn"},
                {"label": "Тушум", "value": approved_total_text, "tone": "flat"},
                {"label": "Курс очилди", "value": miniapp_course.opened_users, "tone": "up"},
                {"label": "Реклама фаол", "value": ad_summary.get("active", 0), "tone": "flat"},
            ],
            "heat": [
                {"label": "мини илова очилди", "value": miniapp_course.opened_users, "tone": "hot"},
                {"label": "дарс бошланди", "value": miniapp_course.lesson_users, "tone": "hot"},
                {"label": "дарс тугади", "value": miniapp_course.completed_users, "tone": "hot"},
                {"label": "тўлов текширувда", "value": pending_payments, "tone": "warn"},
                {"label": "канал ёқилган", "value": "ҳа" if channels_enabled else "йўқ", "tone": "flat"},
                {"label": "фаол канал", "value": active_channels, "tone": "flat"},
                {"label": "реклама етказилди", "value": ad_summary.get("delivered", 0), "tone": "hot"},
                {"label": "реклама хатоси", "value": ad_summary.get("failed", 0), "tone": "risk"},
            ],
            "bars": [
                {"label": "24 соат фаол", "value": active_24h, "tone": "hot"},
                {"label": "Ҳафталик фаол", "value": active_week, "tone": "hot"},
                {"label": "Курс очилди", "value": miniapp_course.opened_users, "tone": "hot"},
                {"label": "Дарс бошланди", "value": miniapp_course.lesson_users, "tone": "hot"},
                {"label": "Дарс тугади", "value": miniapp_course.completed_users, "tone": "hot"},
                {"label": "Текширувдаги тўлов", "value": pending_payments, "tone": "warn"},
                {"label": "Реклама етказилди", "value": ad_summary.get("delivered", 0), "tone": "hot"},
                {"label": "Реклама хатоси", "value": ad_summary.get("failed", 0), "tone": "risk"},
            ],
        }

    @staticmethod
    def _period_report_text(report: dict) -> str:
        metrics = report.get("metrics") or {}
        course = report.get("course") or {}
        payments = report.get("payments") or {}
        by_plan = payments.get("by_plan") or {}
        return (
            f"📊 {report.get('title', 'Статистика')} статистика\n"
            f"Давр: {report.get('note', '—')}\n"
            f"Янгиланди: {report.get('generated_at') or '—'}\n"
            "────────────────────────────────\n\n"
            "👥 ФОЙДАЛАНУВЧИЛАР\n"
            f"Янги/жами: {metrics.get('user_count', 0)}\n"
            f"{metrics.get('active_label', 'Фаол')}: {metrics.get('active_users', 0)}\n"
            f"Ботни блоклаган: {metrics.get('bot_blocked', 0)}\n\n"
            "💳 ТЎЛОВЛАР\n"
            f"Тасдиқланган user: {metrics.get('approved_payment_users', 0)}\n"
            f"Кутилмоқда: {metrics.get('pending_payments', 0)} · Рад: {metrics.get('rejected_payments', 0)}\n"
            f"10 кун: {by_plan.get('10_days', 0)} · 1 ой: {by_plan.get('1_month', 0)}\n"
            f"Тушум: {metrics.get('approved_total_text', '0')}\n\n"
            "📚 КУРС\n"
            f"Мини илова очган: {course.get('opened_users', 0)}\n"
            f"Дарс бошлаган: {course.get('lesson_users', 0)}\n"
            f"Дарс тугатган: {course.get('completed_users', 0)}\n"
            f"Тугатилган қисм: {course.get('completed_sections', 0)}\n"
            f"Тугатилган дарс: {course.get('completed_book_lessons', 0)}\n"
            "Изоҳ: очган/бошлаган/тугатган — мустақил уникал user count; cohort conversion эмас."
        ) + AdminMiniAppService._advanced_report_text(report.get("advanced") or {})

    @staticmethod
    def _advanced_report_text(advanced: dict) -> str:
        if not advanced:
            return ""
        retention = advanced.get("retention") or {}
        d1 = retention.get("d1") or {}
        d7 = retention.get("d7") or {}
        activation = advanced.get("activation") or {}
        direct_activation = (activation.get("variants") or {}).get("direct_start_v1") or {}
        d1_recovery = advanced.get("d1_recovery") or {}
        d1_arms = d1_recovery.get("arms") or {}
        d1_treatment = d1_arms.get("treatment") or {}
        d1_control = d1_arms.get("control") or {}
        sales_value = advanced.get("sales_value") or {}
        sales_arms = sales_value.get("arms") or {}
        sales_treatment = sales_arms.get("treatment") or {}
        sales_control = sales_arms.get("control") or {}
        session_time = advanced.get("session_time") or {}
        lesson_time = advanced.get("lesson_time") or {}
        qa = advanced.get("qa") or {}
        voice = advanced.get("voice") or {}
        foundation = advanced.get("foundation") or {}
        payment = advanced.get("payment") or {}
        funnel = payment.get("funnel") or {}
        notifications = advanced.get("notifications") or {}
        d1_value = f"{d1.get('rate', 0)}%" if d1.get("eligible") else "yig'ilmoqda"
        d7_value = f"{d7.get('rate', 0)}%" if d7.get("eligible") else "yig'ilmoqda"
        notification_value = (
            f"{notifications.get('open_rate', 0)}%"
            if notifications.get("sent")
            else "yig'ilmoqda"
        )
        direct_line = (
            f"Direct-start → dars ≤2m: {direct_activation.get('lesson_started_rate', 0)}% "
            f"({direct_activation.get('lesson_started_2m', 0)}/{direct_activation.get('lesson_started_eligible', 0)})\n"
            if direct_activation
            else ""
        )
        if foundation:
            foundation_first = foundation.get("first_attempt") or {}
            foundation_parts = {
                int(item.get("part") or 0): item
                for item in foundation.get("parts") or []
                if isinstance(item, dict)
            }
            p1 = foundation_parts.get(1, {})
            p2 = foundation_parts.get(2, {})
            p3 = foundation_parts.get(3, {})
            checkpoint_paywall = foundation.get("checkpoint_to_paywall") or {}
            foundation_d1 = foundation.get("d1_meaningful_return") or {}
            foundation_d1_value = (
                f"{foundation_d1.get('rate', 0)}%"
                if foundation_d1.get("eligible")
                else "yig'ilmoqda"
            )
            foundation_lines = (
                f"Starter start → complete: {foundation.get('completion_rate', 0)}% "
                f"({foundation.get('completed_users', 0)}/{foundation.get('started_users', 0)} unikal user)\n"
                f"Starter first-attempt: {foundation_first.get('accuracy', 0)}% "
                f"({foundation_first.get('correct', 0)}/{foundation_first.get('objectives', 0)} objective)\n"
                f"Starter → HSK1 P1/P2/P3: {p1.get('rate_from_foundation', 0)}% / "
                f"{p2.get('rate_from_foundation', 0)}% / {p3.get('rate_from_foundation', 0)}%\n"
                f"Checkpoint → paywall ≤24h: {checkpoint_paywall.get('rate', 0)}% "
                f"({checkpoint_paywall.get('paywall_users', 0)}/{checkpoint_paywall.get('checkpoint_users', 0)})\n"
                f"Starter D1 meaningful learning: {foundation_d1_value} "
                f"({foundation_d1.get('returned', 0)}/{foundation_d1.get('eligible', 0)})\n"
            )
        else:
            foundation_lines = ""
        if d1_recovery.get("collecting"):
            d1_recovery_line = "D1 recovery: 48h natija yig'ilmoqda\n"
        else:
            d1_recovery_label = (
                "D1 recovery (erta signal)"
                if d1_recovery.get("directional_only")
                else "D1 recovery return"
            )
            d1_recovery_line = (
                f"{d1_recovery_label}: T {d1_treatment.get('open_rate', 0)}% "
                f"({d1_treatment.get('opened_any_48h', 0)}/{d1_treatment.get('matured', 0)}) · "
                f"C {d1_control.get('open_rate', 0)}% "
                f"({d1_control.get('opened_any_48h', 0)}/{d1_control.get('matured', 0)}) · "
                f"lift {((d1_recovery.get('uplift_pp') or {}).get('open', 0)):+.1f} pp\n"
            )
        if sales_value:
            sales_status_labels = {
                "collecting": "yig'ilmoqda",
                "early_signal": "erta signal",
                "srm_warning": "SRM xato",
                "guardrail_failed": "guardrail xato",
                "winner": "winner",
                "keep_testing": "test davom etsin",
                "inconclusive": "inconclusive/control",
            }
            sales_ci = sales_value.get("ci_95_pp") or {}
            sales_ci_text = (
                f"{float(sales_ci['low_pp']):+.1f}…{float(sales_ci['high_pp']):+.1f} pp"
                if sales_ci.get("low_pp") is not None and sales_ci.get("high_pp") is not None
                else "yig'ilmoqda"
            )
            sales_guardrails = sales_value.get("guardrails") or {}
            sales_srm = sales_value.get("srm") or {}
            sales_srm_text = (
                f"p={sales_srm.get('p_value')}"
                if sales_srm.get("checked")
                else "hali tekshirilmadi"
            )
            sales_error_guardrail = sales_guardrails.get("frontend_error") or {}
            sales_error_text = (
                f"{float(sales_error_guardrail.get('delta_pp') or 0):+.1f} pp"
                if sales_error_guardrail.get("available")
                else "mavjud emas"
            )
            sales_value_line = (
                f"Sales A/B 7d ({sales_status_labels.get(sales_value.get('status'), sales_value.get('status', '—'))}): "
                f"T {sales_treatment.get('approval_rate', 0)}% "
                f"({sales_treatment.get('approved_users', 0)}/{sales_treatment.get('matured', 0)}) · "
                f"C {sales_control.get('approval_rate', 0)}% "
                f"({sales_control.get('approved_users', 0)}/{sales_control.get('matured', 0)}) · "
                f"lift {float(sales_value.get('uplift_pp') or 0):+.1f} pp · CI {sales_ci_text} · "
                f"Starter {((sales_guardrails.get('foundation') or {}).get('delta_pp', 0)):+.1f} pp · "
                f"checkpoint {((sales_guardrails.get('first_checkpoint') or {}).get('delta_pp', 0)):+.1f} pp · "
                f"D1 {((sales_guardrails.get('learning') or {}).get('delta_pp', 0)):+.1f} pp · "
                f"reject {((sales_guardrails.get('rejection') or {}).get('delta_pp', 0)):+.1f} pp · "
                f"pending {((sales_guardrails.get('pending') or {}).get('delta_pp', 0)):+.1f} pp · "
                f"frontend error {sales_error_text} · SRM {sales_srm_text}\n"
            )
        else:
            sales_value_line = ""
        return (
            "\n\n"
            "📌 ҚЎШИМЧА PRODUCT МЕТРИКАЛАР\n"
            "Бу блок retention, вақт, QA/Voice, payment abandon, revenue/payer, taglangan CAC ва feature adoption'ни кўрсатади.\n"
            f"Signup → Mini App D1: {d1_value} ({d1.get('retained', 0)}/{d1.get('eligible', 0)} mature)\n"
            f"Signup → Mini App D7: {d7_value} ({d7.get('retained', 0)}/{d7.get('eligible', 0)} mature)\n"
            f"{d1_recovery_line}"
            f"{sales_value_line}"
            f"Onboarding → dars ≤2m: {activation.get('lesson_started_rate', 0)}% ({activation.get('lesson_started_2m', 0)}/{activation.get('lesson_started_eligible', 0)})\n"
            f"{direct_line}"
            f"{foundation_lines}"
            f"Avg Mini App session: {session_time.get('avg_text', '—')} · measured/session: {session_time.get('measured_sessions', 0)}/{session_time.get('sessions', 0)}\n"
            f"Lesson time: {lesson_time.get('avg_text', '—')} · tugagan dars: {lesson_time.get('completed_lessons', 0)}\n"
            f"AI chat message/user: {qa.get('avg_per_user', 0)} · xabar: {qa.get('messages', 0)} · user: {qa.get('users', 0)}\n"
            f"Voice minutes: {voice.get('minutes_text', '0 min')} · avg: {voice.get('avg_text', '—')}\n"
            f"Payment abandon: {funnel.get('abandon_step', '—')} · yo'qotish: {funnel.get('abandon_count', 0)} ({funnel.get('abandon_rate', 0)}%)\n"
            f"First payment time: {payment.get('first_payment_time_text', '—')} · first pay user: {payment.get('first_payment_users', 0)}\n"
            f"Davr revenue/payer: {payment.get('revenue_per_payer_text', payment.get('ltv_text', '—'))} · Taglangan CAC: {payment.get('cac_text', '—')}\n"
            f"Unfinished lesson notification open: {notification_value} "
            f"({notifications.get('opened_after', 0)}/{notifications.get('sent', 0)} mature; "
            f"{notifications.get('immature_sent', 0)} kutilmoqda)"
        )

    @staticmethod
    def _report_text(
        *,
        now: datetime,
        total: int,
        status_counts: dict[str, int],
        paid_users: int,
        historical_approved_users: int,
        new_today: int,
        new_week: int,
        new_month: int,
        active_today: int,
        active_24h: int,
        active_week: int,
        level_counts: dict[str, int],
        language_counts: dict[str, int],
        pending_payments: int,
        approved_payments: int,
        rejected_payments: int,
        pay_by_plan: dict[str, int],
        approved_total_text: str,
        source_rows: list[dict],
        miniapp_course,
        avg_sections: float,
        ad_summary: dict,
        channels_enabled: bool,
        active_channels: int,
        conversion: float,
        qa_users: int,
        engagement: float,
    ) -> str:
        source_text = "ҳали йўқ"
        if source_rows:
            source_text = "\n".join(
                f"{row['label']}: фойдаланувчи {row['unique_all']}/+{row['unique_week']} · кириш {row['total_all']}/+{row['total_week']}"
                for row in source_rows
            )
        level_text = " · ".join(
            f"{_level_label(key)}: {level_counts.get(key, 0)}"
            for key in ("beginner", "hsk1", "hsk2", "hsk3", "hsk4")
        )
        language_text = " · ".join(
            f"{_language_label(key)}: {value}"
            for key, value in sorted(language_counts.items())
        ) or "ҳали йўқ"
        channel_status = "ёқилган" if channels_enabled else "ўчирилган"
        return (
            f"📊 Статистика {now.astimezone(ADMIN_MINIAPP_TZ).strftime('%d.%m.%Y %H:%M Asia/Shanghai')}\n"
            "────────────────────────────────\n\n"
            f"👥 ФОЙДАЛАНУВЧИЛАР [{total}]\n"
            f"Бепул: {status_counts.get('free', 0)} · Синов: {status_counts.get('trial', 0)}\n"
            f"Фаол ҳолат: {status_counts.get('active', 0)} · Тўловли: {paid_users}\n"
            f"Тарихий тасдиқланган: {historical_approved_users}\n"
            f"Тугаган: {status_counts.get('expired', 0)} · Блокланган: {status_counts.get('blocked', 0)}\n\n"
            "📅 ФАОЛЛИК\n"
            f"Янги: бугун +{new_today} · ҳафта +{new_week} · ой +{new_month}\n"
            f"Фаол: бугун {active_today} · 24 соат {active_24h} · ҳафта {active_week}\n\n"
            "📊 ДАРАЖАЛАР\n"
            f"{level_text}\n\n"
            "🌐 ТИЛ\n"
            f"{language_text}\n\n"
            "💳 ТЎЛОВЛАР\n"
            f"Кутилмоқда: {pending_payments} · Тасдиқланган: {approved_payments} · Рад: {rejected_payments}\n"
            f"10 кун: {pay_by_plan.get('10_days', 0)} · 1 ой: {pay_by_plan.get('1_month', 0)}\n"
            f"Жами даромад: {approved_total_text}\n\n"
            "💎 ОБУНА МАНБАЛАРИ\n"
            f"{source_text}\n\n"
            "📚 КУРС\n"
            f"Мини илова очган: {miniapp_course.opened_users} · Дарс бошлаганлар: {miniapp_course.lesson_users}\n"
            f"Дарс тугатганлар: {miniapp_course.completed_users} · Тугатилган қисмлар: {miniapp_course.completed_sections}\n"
            f"Тугатилган дарслар: {miniapp_course.completed_book_lessons} · Ўртача қисм: {avg_sections}\n\n"
            "📣 РЕКЛАМА ВА КАНАЛ\n"
            f"Реклама кампаниялари: {ad_summary.get('total', 0)} · Фаол: {ad_summary.get('active', 0)}\n"
            f"Етказилди: {ad_summary.get('delivered', 0)} · Хато: {ad_summary.get('failed', 0)}\n"
            f"Мажбурий канал: {channel_status} · Фаол канал: {active_channels}\n\n"
            "📈 КОНВЕРСИЯ\n"
            f"Фойдаланувчи → approved payer: {conversion}%\n"
            f"AI chat ишлатган уникал user: {qa_users} ({engagement}%)"
        )
