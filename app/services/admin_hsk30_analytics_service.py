from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select

from app.db.models.conversion_funnel_event import ConversionFunnelEvent
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.db.models.course_track_state import CourseTrackState
from app.db.models.payment import Payment
from app.db.models.subscription_entry_event import SubscriptionEntryEvent
from app.db.models.user import User
from app.services.hsk30_unlock_service import HSK30_UNLOCK_PLAN_TYPE


class AdminHsk30AnalyticsService:
    """Build the HSK 3.0 rollout funnel from existing product and payment data."""

    TRACK_EVENTS = {
        "hsk30_promo_shown",
        "hsk30_promo_cta_clicked",
        "hsk30_promo_dismissed",
        "hsk30_level_selected",
        "hsk30_checkout_failed",
        "course_track_switched",
    }
    CHECKOUT_STAGES = {
        "payment_instructions_viewed": "instructions",
        "payment_receipt_selected": "receipt_selected",
    }
    STAGE_LABELS = {
        "promo_shown": "HSK 3.0 таклифи кўрсатилди",
        "promo_cta": "Таклиф тугмаси босилди",
        "promo_dismissed": "Таклиф ёпилди",
        "level_selected": "HSK 3.0 даражаси танланди",
        "track_activated": "HSK 3.0 курси фаоллашди",
        "checkout_opened": "Checkout очилди",
        "instructions": "Тўлов йўриқномаси",
        "receipt_selected": "Чек танланди",
        "checkout_failed": "Checkout хатоси",
        "payment_submitted": "Тўлов юборилди",
        "pending": "Admin текширувида",
        "approved": "Тўлов тасдиқланди",
        "rejected": "Тўлов рад этилди",
    }

    def __init__(self, session):
        self.session = session

    @staticmethod
    def _payload(raw: str | None) -> dict:
        try:
            value = json.loads(raw or "{}")
        except (TypeError, ValueError):
            return {}
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _iso(value: datetime | None) -> str | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()

    @staticmethod
    def _normalize_reason(value: str | None) -> str:
        reason = " ".join(str(value or "").split())[:160]
        if not reason or reason.lower() in {
            "rejected by admin mini app",
            "rejected by admin",
        }:
            return "Сабаб изоҳи киритилмаган"
        return reason

    async def snapshot(self, *, days: int = 30, user_limit: int = 50) -> dict:
        now = datetime.now(timezone.utc)
        since = now - timedelta(days=days) if days else None

        course_stmt = select(CourseMiniAppEvent).where(
            CourseMiniAppEvent.event_name.in_(self.TRACK_EVENTS),
            or_(
                CourseMiniAppEvent.event_name != "course_track_switched",
                CourseMiniAppEvent.payload_json.contains('"to_track":"hsk30"'),
                CourseMiniAppEvent.payload_json.contains('"to_track": "hsk30"'),
            ),
        )
        if since is not None:
            course_stmt = course_stmt.where(CourseMiniAppEvent.created_at >= since)
        course_events = list((await self.session.execute(course_stmt)).scalars().all())

        promo_users: set[int] = set()
        promo_impressions = 0
        promo_cta_users: set[int] = set()
        promo_dismiss_users: set[int] = set()
        selected_level_users: set[int] = set()
        track_users: set[int] = set()
        error_rows: list[dict] = []
        latest_course_event: dict[int, tuple[datetime, str, dict, str]] = {}

        for event in course_events:
            telegram_id = int(event.telegram_id)
            payload = self._payload(event.payload_json)
            name = str(event.event_name)
            promo_impressions += int(name == "hsk30_promo_shown")
            if name == "hsk30_promo_shown":
                promo_users.add(telegram_id)
            elif name == "hsk30_promo_cta_clicked":
                promo_cta_users.add(telegram_id)
            elif name == "hsk30_promo_dismissed":
                promo_dismiss_users.add(telegram_id)
            elif name == "hsk30_level_selected":
                selected_level_users.add(telegram_id)
            elif name == "hsk30_checkout_failed":
                error_rows.append({
                    "telegram_id": telegram_id,
                    "stage": str(payload.get("stage") or "checkout"),
                    "error": str(payload.get("error") or "unknown_error")[:80],
                    "method": str(payload.get("payment_method") or "")[:16],
                    "created_at": event.created_at,
                })
            elif (
                name == "course_track_switched"
                and str(payload.get("to_track") or "") == "hsk30"
            ):
                track_users.add(telegram_id)

            event_stage = {
                "hsk30_promo_shown": "promo_shown",
                "hsk30_promo_cta_clicked": "promo_cta",
                "hsk30_promo_dismissed": "promo_dismissed",
                "hsk30_level_selected": "level_selected",
                "hsk30_checkout_failed": "checkout_failed",
                "course_track_switched": (
                    "track_activated"
                    if str(payload.get("to_track") or "") == "hsk30"
                    else ""
                ),
            }.get(name)
            if event_stage:
                previous = latest_course_event.get(telegram_id)
                if previous is None or event.created_at > previous[0]:
                    latest_course_event[telegram_id] = (
                        event.created_at,
                        event_stage,
                        payload,
                        str(event.source or ""),
                    )

        profile_stmt = select(
            User.telegram_id,
            CourseMiniAppProfile.hsk30_promo_shown_count,
            CourseMiniAppProfile.hsk30_promo_last_shown_at,
        ).join(
            CourseMiniAppProfile,
            CourseMiniAppProfile.user_id == User.id,
        ).where(CourseMiniAppProfile.hsk30_promo_shown_count > 0)
        if since is not None:
            profile_stmt = profile_stmt.where(
                CourseMiniAppProfile.hsk30_promo_last_shown_at >= since
            )
        profile_rows = (await self.session.execute(profile_stmt)).all()
        profile_promo_users = {int(row.telegram_id) for row in profile_rows}
        promo_users |= profile_promo_users
        if since is None:
            # The profile counter is the complete legacy impression count.
            promo_impressions = sum(
                max(0, int(row.hsk30_promo_shown_count or 0))
                for row in profile_rows
            )

        if since is None:
            track_state_ids = set((await self.session.execute(
                select(CourseTrackState.user_id).where(
                    CourseTrackState.track == "hsk30"
                )
            )).scalars().all())
            if track_state_ids:
                state_ids = (await self.session.execute(
                    select(User.telegram_id).where(User.id.in_(track_state_ids))
                )).scalars().all()
                track_users |= {int(value) for value in state_ids}

        entry_stmt = select(SubscriptionEntryEvent).where(or_(
            SubscriptionEntryEvent.mode == HSK30_UNLOCK_PLAN_TYPE,
            SubscriptionEntryEvent.plan_type == HSK30_UNLOCK_PLAN_TYPE,
            SubscriptionEntryEvent.source == HSK30_UNLOCK_PLAN_TYPE,
        ))
        if since is not None:
            entry_stmt = entry_stmt.where(SubscriptionEntryEvent.created_at >= since)
        entry_rows = list((await self.session.execute(entry_stmt)).scalars().all())
        latest_entries: dict[int, SubscriptionEntryEvent] = {}
        for entry in entry_rows:
            telegram_id = int(entry.telegram_id)
            previous = latest_entries.get(telegram_id)
            if previous is None or entry.created_at > previous.created_at:
                latest_entries[telegram_id] = entry

        checkout_events_stmt = select(ConversionFunnelEvent).where(
            ConversionFunnelEvent.event_name == "checkout_opened",
            or_(
                ConversionFunnelEvent.source == HSK30_UNLOCK_PLAN_TYPE,
                ConversionFunnelEvent.payload_json.contains(HSK30_UNLOCK_PLAN_TYPE),
            ),
        )
        if since is not None:
            checkout_events_stmt = checkout_events_stmt.where(
                ConversionFunnelEvent.created_at >= since
            )
        checkout_event_rows = list(
            (await self.session.execute(checkout_events_stmt)).scalars().all()
        )
        checkout_events: dict[int, list[tuple[datetime, str, dict]]] = defaultdict(list)
        stage_users: dict[str, set[int]] = {
            "instructions": set(),
            "receipt_selected": set(),
        }
        for event in checkout_event_rows:
            payload = self._payload(event.payload_json)
            if not (
                str(payload.get("plan_type") or "") == HSK30_UNLOCK_PLAN_TYPE
                or str(payload.get("mode") or "") == HSK30_UNLOCK_PLAN_TYPE
                or str(event.source or "") == HSK30_UNLOCK_PLAN_TYPE
            ):
                continue
            telegram_id = int(event.telegram_id)
            stage = str(payload.get("stage") or "")
            stage_key = self.CHECKOUT_STAGES.get(stage, "checkout_opened")
            if stage_key in stage_users:
                stage_users[stage_key].add(telegram_id)
            checkout_events[telegram_id].append((event.created_at, stage_key, payload))

        payment_stmt = select(Payment).where(
            Payment.plan_type == HSK30_UNLOCK_PLAN_TYPE,
        )
        if since is not None:
            payment_stmt = payment_stmt.where(Payment.submitted_at >= since)
        payment_rows = list((await self.session.execute(payment_stmt)).scalars().all())
        latest_payments: dict[int, Payment] = {}
        payment_status_counts: Counter[str] = Counter()
        payment_status_users: dict[str, set[int]] = defaultdict(set)
        payment_methods: dict[str, dict] = defaultdict(lambda: {
            "payments": 0,
            "users": set(),
            "approved": 0,
            "pending": 0,
            "rejected": 0,
        })
        rejection_reasons: Counter[str] = Counter()

        for payment in payment_rows:
            telegram_id = int(payment.user_telegram_id)
            status = str(payment.payment_status or "unknown")
            method = str(payment.payment_method or "unknown")
            payment_status_counts[status] += 1
            payment_status_users[status].add(telegram_id)
            method_row = payment_methods[method]
            method_row["payments"] += 1
            method_row["users"].add(telegram_id)
            if status in {"approved", "pending", "rejected"}:
                method_row[status] += 1
            previous = latest_payments.get(telegram_id)
            if previous is None or payment.submitted_at > previous.submitted_at:
                latest_payments[telegram_id] = payment
            if status == "rejected":
                rejection_reasons[self._normalize_reason(payment.admin_comment)] += 1

        payment_submitted_users = {int(payment.user_telegram_id) for payment in payment_rows}
        funnel_stages = [
            ("promo_shown", "Promo кўрсатилди", promo_users),
            ("promo_cta", "Promo тугмаси босилди", promo_cta_users),
            ("level_selected", "HSK 3.0 даражаси танланди", selected_level_users),
            ("checkout_opened", "Checkout очилди", set(latest_entries)),
            ("instructions", "Тўлов йўриқномаси очилди", stage_users["instructions"]),
            ("receipt_selected", "Чек танланди", stage_users["receipt_selected"]),
            ("payment_submitted", "Тўлов юборилди", payment_submitted_users),
        ]
        funnel_payload = []
        previous_users: set[int] | None = None
        for key, label, users in funnel_stages:
            count = len(users)
            shared_users = len(previous_users & users) if previous_users is not None else count
            conversion = (
                round(shared_users * 100 / len(previous_users), 1)
                if previous_users
                else None
            )
            reach = (
                round(len(promo_users & users) * 100 / len(promo_users), 1)
                if promo_users
                else 0.0
            )
            funnel_payload.append({
                "key": key,
                "label": label,
                "users": count,
                "conversion_from_previous_pct": conversion,
                "reach_pct": reach,
            })
            previous_users = users

        method_payload = [
            {
                "method": method,
                "payments": row["payments"],
                "users": len(row["users"]),
                "approved": row["approved"],
                "pending": row["pending"],
                "rejected": row["rejected"],
            }
            for method, row in sorted(
                payment_methods.items(),
                key=lambda item: (-item[1]["payments"], item[0]),
            )
        ]

        user_stages: dict[int, tuple[datetime, str, dict]] = {
            telegram_id: (created_at, stage, payload)
            for telegram_id, (created_at, stage, payload, _source)
            in latest_course_event.items()
        }
        for telegram_id, entry in latest_entries.items():
            previous = user_stages.get(telegram_id)
            if previous is None or entry.created_at > previous[0]:
                user_stages[telegram_id] = (
                    entry.created_at,
                    "checkout_opened",
                    {"payment_method": entry.payment_method},
                )
        for telegram_id, values in checkout_events.items():
            for created_at, stage, payload in values:
                previous = user_stages.get(telegram_id)
                if previous is None or created_at > previous[0]:
                    user_stages[telegram_id] = (created_at, stage, payload)
        for row in error_rows:
            telegram_id = int(row["telegram_id"])
            previous = user_stages.get(telegram_id)
            if previous is None or row["created_at"] > previous[0]:
                user_stages[telegram_id] = (
                    row["created_at"],
                    "checkout_failed",
                    {
                        "error": row["error"],
                        "payment_method": row["method"],
                    },
                )

        dropoff_counts: Counter[str] = Counter()
        recent_rows: list[dict] = []
        candidate_users = set(user_stages) | set(latest_entries) | set(latest_payments)
        for telegram_id in candidate_users:
            entry = latest_entries.get(telegram_id)
            payment = latest_payments.get(telegram_id)
            if (
                payment is not None
                and entry is not None
                and payment.submitted_at < entry.created_at
            ):
                payment = None
            last_event = user_stages.get(telegram_id)
            last_step = "promo_shown"
            last_at = entry.created_at if entry is not None else None
            last_payload: dict = {}
            if last_event:
                last_at, last_step, last_payload = last_event
            if payment is not None:
                status = str(payment.payment_status or "unknown")
                last_step = status if status in {"pending", "approved", "rejected"} else "payment_submitted"
                last_at = payment.reviewed_at or payment.submitted_at
                last_payload = {"payment_method": payment.payment_method}
                if status == "rejected":
                    last_payload["reason"] = self._normalize_reason(payment.admin_comment)
            else:
                status = "not_submitted"
                if last_step in {
                    "promo_shown",
                    "promo_cta",
                    "promo_dismissed",
                    "level_selected",
                    "track_activated",
                    "instructions",
                    "receipt_selected",
                    "checkout_failed",
                }:
                    dropoff_counts[last_step] += 1
                else:
                    dropoff_counts["checkout_opened"] += 1

            recent_rows.append({
                "telegram_id": telegram_id,
                "user_id": None,
                "name": "",
                "username": "",
                "last_step": last_step,
                "last_step_label": self.STAGE_LABELS.get(last_step, "Checkout тўхтаган"),
                "status": status,
                "method": str(
                    (payment.payment_method if payment else None)
                    or last_payload.get("payment_method")
                    or (entry.payment_method if entry else None)
                    or ""
                ),
                "reason": str(last_payload.get("reason") or last_payload.get("error") or ""),
                "last_seen_at": last_at,
            })

        if recent_rows:
            users_by_tg = {
                int(user.telegram_id): user
                for user in (await self.session.execute(
                    select(User).where(
                        User.telegram_id.in_([row["telegram_id"] for row in recent_rows])
                    )
                )).scalars().all()
            }
            for row in recent_rows:
                user = users_by_tg.get(row["telegram_id"])
                if user:
                    row["user_id"] = int(user.id)
                    row["name"] = str(user.full_name or "")[:100]
                    row["username"] = str(user.username or "")[:64]

        recent_rows.sort(key=lambda row: row["last_seen_at"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

        errors_by_reason: Counter[str] = Counter()
        for row in error_rows:
            errors_by_reason[f'{row["stage"]}: {row["error"]}'] += 1
        failures = [
            {"reason": reason, "count": count}
            for reason, count in errors_by_reason.most_common(10)
        ]
        dropoffs = [
            {"step": key, "label": self.STAGE_LABELS.get(key, key), "users": count}
            for key, count in dropoff_counts.most_common()
        ]

        return {
            "ok": True,
            "period_days": days,
            "generated_at": now.isoformat(),
            "funnel": funnel_payload,
            "promo_dismissed_users": len(promo_dismiss_users),
            "selected_level_users": len(selected_level_users),
            "track_activated_users": len(track_users),
            "promo_impressions": promo_impressions,
            "payments": {
                "pending": payment_status_counts.get("pending", 0),
                "approved": payment_status_counts.get("approved", 0),
                "rejected": payment_status_counts.get("rejected", 0),
                "pending_users": len(payment_status_users.get("pending", set())),
                "approved_users": len(payment_status_users.get("approved", set())),
                "rejected_users": len(payment_status_users.get("rejected", set())),
            },
            "payment_methods": method_payload,
            "rejection_reasons": [
                {"reason": reason, "count": count}
                for reason, count in rejection_reasons.most_common(10)
            ],
            "checkout_failures": failures,
            "dropoffs": dropoffs,
            "users": [
                {
                    **row,
                    "last_seen_at": self._iso(row["last_seen_at"]),
                }
                for row in recent_rows[:user_limit]
            ],
            "coverage_note": (
                "Checkout ва тўлов маълумоти танланган даврдаги сервер ёзувларидан олинди. "
                "Promo/track қадамлари аввал барча платформада бир хил қайд этилмаган; "
                "сабабсиз ёпилган checkout учун сабаб аниқ эмас, охирги қайд этилган қадам кўрсатилади."
            ),
        }
