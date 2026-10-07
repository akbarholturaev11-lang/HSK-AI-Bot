from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select

from app.db.models.conversion_funnel_event import ConversionFunnelEvent
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.course_miniapp_profile import CourseMiniAppProfile
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
    COURSE_FUNNEL_EVENTS = {
        "hsk30_promo_shown",
        "hsk30_promo_cta_clicked",
        "hsk30_promo_dismissed",
        "hsk30_level_selected",
        "course_track_switched",
    }
    STAGE_LABELS = {
        "promo_shown": "HSK 3.0 таклифи кўрсатилди",
        "promo_cta": "Таклиф тугмаси босилди",
        "promo_dismissed": "Таклиф ёпилди",
        "level_selected": "HSK 3.0 даражаси танланди",
        "track_activated": "HSK 3.0 курси фаоллашди",
        "subscription_entry": "HSK 3.0 обуна саҳифасига кирди",
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

        # Course funnel users come only from event rows emitted by the Mini App.
        # The profile counter below is shared by Mini App, Desktop, and Android.
        promo_impressions = 0
        promo_dismiss_users: set[int] = set()
        course_stage_times: dict[int, dict[str, list[datetime]]] = defaultdict(
            lambda: defaultdict(list)
        )
        error_rows: list[dict] = []
        latest_course_event: dict[int, tuple[datetime, str, dict, str]] = {}

        for event in course_events:
            telegram_id = int(event.telegram_id)
            payload = self._payload(event.payload_json)
            name = str(event.event_name)
            promo_impressions += int(name == "hsk30_promo_shown")
            if name == "hsk30_promo_shown":
                course_stage_times[telegram_id]["promo_shown"].append(event.created_at)
            elif name == "hsk30_promo_cta_clicked":
                course_stage_times[telegram_id]["promo_cta"].append(event.created_at)
            elif name == "hsk30_promo_dismissed":
                promo_dismiss_users.add(telegram_id)
            elif name == "hsk30_level_selected":
                course_stage_times[telegram_id]["level_selected"].append(event.created_at)
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
                course_stage_times[telegram_id]["track_activated"].append(event.created_at)

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
            CourseMiniAppProfile.hsk30_promo_shown_count,
        ).where(CourseMiniAppProfile.hsk30_promo_shown_count > 0)
        profile_rows = (await self.session.execute(profile_stmt)).all()
        lifetime_promo_impressions_all_platforms = sum(
            max(0, int(row.hsk30_promo_shown_count or 0))
            for row in profile_rows
        )

        tracking_since = (await self.session.execute(
            select(func.min(CourseMiniAppEvent.created_at)).where(
                CourseMiniAppEvent.event_name.in_(self.COURSE_FUNNEL_EVENTS - {"course_track_switched"})
            )
        )).scalar_one_or_none()

        # Keep Mini App course steps in sequence. A later event counts only when
        # the same user has the preceding event in the selected reporting window.
        course_reached: dict[str, set[int]] = {
            "promo_shown": set(),
            "promo_cta": set(),
            "level_selected": set(),
            "track_activated": set(),
        }
        for telegram_id, event_times in course_stage_times.items():
            promo_at = min(event_times.get("promo_shown", []), default=None)
            if promo_at is None:
                continue
            course_reached["promo_shown"].add(telegram_id)
            cta_at = min(
                (value for value in event_times.get("promo_cta", []) if value >= promo_at),
                default=None,
            )
            if cta_at is None:
                continue
            course_reached["promo_cta"].add(telegram_id)
            level_at = min(
                (value for value in event_times.get("level_selected", []) if value >= cta_at),
                default=None,
            )
            if level_at is None:
                continue
            course_reached["level_selected"].add(telegram_id)
            track_at = min(
                (value for value in event_times.get("track_activated", []) if value >= level_at),
                default=None,
            )
            if track_at is not None:
                course_reached["track_activated"].add(telegram_id)
        promo_users = course_reached["promo_shown"]
        promo_cta_users = course_reached["promo_cta"]
        selected_level_users = course_reached["level_selected"]
        track_users = course_reached["track_activated"]

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
            ConversionFunnelEvent.event_name.in_(
                ("checkout_opened", "payment_screenshot_submitted")
            ),
        )
        if since is not None:
            checkout_events_stmt = checkout_events_stmt.where(
                ConversionFunnelEvent.created_at >= since
            )
        checkout_event_rows = sorted(
            (await self.session.execute(checkout_events_stmt)).scalars().all(),
            key=lambda event: event.created_at,
        )
        hsk30_attempts: dict[tuple[int, str], dict] = {}

        # First identify real HSK 3.0 checkout starts. Stage and submit events
        # are then attached only to that user's same attempt_id.
        for event in checkout_event_rows:
            if event.event_name != "checkout_opened":
                continue
            payload = self._payload(event.payload_json)
            if str(payload.get("stage") or "").strip():
                continue
            if not (
                str(payload.get("plan_type") or "") == HSK30_UNLOCK_PLAN_TYPE
                or str(payload.get("mode") or "") == HSK30_UNLOCK_PLAN_TYPE
                or str(event.source or "") == HSK30_UNLOCK_PLAN_TYPE
            ):
                continue
            telegram_id = int(event.telegram_id)
            attempt_id = str(payload.get("attempt_id") or "").strip()
            if not attempt_id:
                continue
            key = (telegram_id, attempt_id)
            hsk30_attempts.setdefault(key, {
                "telegram_id": telegram_id,
                "attempt_id": attempt_id,
                "opened_at": event.created_at,
                "stages": {},
                "payment_id": None,
            })

        checkout_events: dict[int, list[tuple[datetime, str, dict, str]]] = defaultdict(list)
        attempt_payment_ids: set[int] = set()
        for event in checkout_event_rows:
            payload = self._payload(event.payload_json)
            attempt_id = str(payload.get("attempt_id") or "").strip()
            telegram_id = int(event.telegram_id)
            if (
                event.event_name == "payment_screenshot_submitted"
                and attempt_id
                and event.payment_id
                and (
                    str(payload.get("plan_type") or "") == HSK30_UNLOCK_PLAN_TYPE
                    or str(payload.get("mode") or "") == HSK30_UNLOCK_PLAN_TYPE
                    or str(event.source or "") == HSK30_UNLOCK_PLAN_TYPE
                )
            ):
                # A submission may belong to an attempt started before the
                # selected period. It is still attempt-aware, even though its
                # opening step is outside this period's funnel cohort.
                attempt_payment_ids.add(int(event.payment_id))
            attempt = hsk30_attempts.get((telegram_id, attempt_id)) if attempt_id else None
            if attempt is None or event.created_at < attempt["opened_at"]:
                continue
            if event.event_name == "checkout_opened":
                stage = str(payload.get("stage") or "").strip()
                stage_key = self.CHECKOUT_STAGES.get(stage)
                if stage_key:
                    attempt["stages"].setdefault(stage_key, event.created_at)
                    checkout_events[telegram_id].append(
                        (event.created_at, stage_key, payload, str(event.source or ""))
                    )
            elif event.event_name == "payment_screenshot_submitted":
                attempt["stages"].setdefault("payment_submitted", event.created_at)
                if event.payment_id:
                    attempt["payment_id"] = int(event.payment_id)
                    attempt_payment_ids.add(int(event.payment_id))
                checkout_events[telegram_id].append(
                    (event.created_at, "payment_submitted", payload, str(event.source or ""))
                )

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

        course_stages = [
            ("promo_shown", "Таклиф кўрсатилди"),
            ("promo_cta", "Таклиф тугмаси босилди"),
            ("level_selected", "HSK 3.0 даражаси танланди"),
            ("track_activated", "HSK 3.0 курси очилди"),
        ]
        course_funnel = []
        previous_course_users: set[int] | None = None
        for key, label in course_stages:
            users = course_reached[key]
            converted = (
                len(previous_course_users & users)
                if previous_course_users is not None
                else len(users)
            )
            previous_count = (
                len(previous_course_users)
                if previous_course_users is not None
                else None
            )
            course_funnel.append({
                "key": key,
                "label": label,
                "users": len(users),
                "previous_users": previous_count,
                "converted_from_previous": converted if previous_count is not None else None,
                "conversion_from_previous_pct": (
                    round(converted * 100 / previous_count, 1)
                    if previous_count
                    else None
                ),
            })
            previous_course_users = users

        payment_reached: dict[str, set[tuple[int, str]]] = {
            "checkout_opened": set(),
            "instructions": set(),
            "receipt_selected": set(),
            "payment_submitted": set(),
        }
        dropoff_counts: Counter[str] = Counter()
        for attempt_key, attempt in hsk30_attempts.items():
            stages = attempt["stages"]
            payment_reached["checkout_opened"].add(attempt_key)
            submitted = "payment_submitted" in stages
            receipt = "receipt_selected" in stages or submitted
            instructions = "instructions" in stages or receipt
            if instructions:
                payment_reached["instructions"].add(attempt_key)
            if receipt:
                payment_reached["receipt_selected"].add(attempt_key)
            if submitted:
                payment_reached["payment_submitted"].add(attempt_key)
            else:
                last_step = (
                    "receipt_selected" if receipt
                    else "instructions" if instructions
                    else "checkout_opened"
                )
                dropoff_counts[last_step] += 1

        payment_stages = [
            ("checkout_opened", "HSK 3.0 checkout очилди"),
            ("instructions", "Тўлов йўриқномаси кўрилди"),
            ("receipt_selected", "Чек танланди"),
            ("payment_submitted", "Тўлов юборилди"),
        ]
        payment_funnel = []
        previous_attempts: set[tuple[int, str]] | None = None
        for key, label in payment_stages:
            attempts = payment_reached[key]
            converted = (
                len(previous_attempts & attempts)
                if previous_attempts is not None
                else len(attempts)
            )
            previous_count = (
                len(previous_attempts)
                if previous_attempts is not None
                else None
            )
            payment_funnel.append({
                "key": key,
                "label": label,
                "attempts": len(attempts),
                "previous_attempts": previous_count,
                "converted_from_previous": converted if previous_count is not None else None,
                "conversion_from_previous_pct": (
                    round(converted * 100 / previous_count, 1)
                    if previous_count
                    else None
                ),
            })
            previous_attempts = attempts

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
                    "subscription_entry",
                    {
                        "payment_method": entry.payment_method,
                        "source": entry.source,
                    },
                )
        for telegram_id, values in checkout_events.items():
            for created_at, stage, payload, source in values:
                previous = user_stages.get(telegram_id)
                if previous is None or created_at > previous[0]:
                    user_stages[telegram_id] = (
                        created_at,
                        stage,
                        {**payload, "source": source},
                    )
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

        recent_rows: list[dict] = []
        attempt_users = {telegram_id for telegram_id, _attempt_id in hsk30_attempts}
        candidate_users = (
            set(user_stages)
            | set(latest_entries)
            | set(latest_payments)
            | attempt_users
        )
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
            {"step": key, "label": self.STAGE_LABELS.get(key, key), "attempts": count}
            for key, count in dropoff_counts.most_common()
        ]

        linked_payment_ids = {
            int(payment.id)
            for payment in payment_rows
            if payment.id is not None and int(payment.id) in attempt_payment_ids
        }

        return {
            "ok": True,
            "period_days": days,
            "generated_at": now.isoformat(),
            "course_funnel": course_funnel,
            "payment_funnel": payment_funnel,
            "promo_dismissed_users": len(promo_dismiss_users),
            "selected_level_users": len(selected_level_users),
            "track_activated_users": len(track_users),
            "promo_impressions": promo_impressions,
            "promo_impressions_all_platforms_lifetime": lifetime_promo_impressions_all_platforms,
            "course_funnel_tracking_since": self._iso(tracking_since),
            "unlinked_payment_records": max(0, len(payment_rows) - len(linked_payment_ids)),
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
                "Курс voronkasi фақат Mini App’да қайд этилган promo → танлаш → курс очиш user’ларини санайди; "
                "қадамлар танланган даврда ва шу тартибда бўлиши шарт. Promo lifetime сони барча платформанинг "
                "профиль ҳисоблагичидан алоҳида олинади. Тўлов voronkasi HSK 3.0 checkout attempt_id бўйича "
                "Mini App, Android ва Desktop’ни боғлайди ва уринишларни санайди; attempt_id билан боғланмаган "
                "танланган даврдан олдин бошланган тўлов уринишлари воронкага кирмайди. "
                "Тўлов ҳолатлари эса "
                "танланган даврдаги барча HSK 3.0 тўлов "
                "ёзувларини қамрайди. Сабабсиз ёпилган checkout сабабини сервер аниқлай олмайди."
            ),
        }
