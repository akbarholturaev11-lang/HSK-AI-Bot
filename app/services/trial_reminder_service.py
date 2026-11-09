"""7 kunlik Pro trial tugashi haqida ogohlantirish.

Jami IKKI xabar: 2 kun qolganda va oxirgi kuni. Ko'proq emas — loyihada
allaqachon oltita bildirishnoma servisi bor va odam kuniga to'rt xabar olsa
botni bloklaydi (bu KPI ro'yxatidagi ko'rsatkich).

Takrorlanmasligi `course_user_notifications` dagi `dedupe_key` bilan
ta'minlanadi: `users` ga yangi ustun qo'shilmaydi, chunki trial ustunlariga
har qanday qo'shimcha yozuv referral byudjeti bilan bog'liq xavfni oshiradi.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from sqlalchemy import and_, exists, or_, select

from app.bot.keyboards.subscription import subscription_miniapp_keyboard
from app.bot.utils.i18n import t
from app.db.models.user import User
from app.db.models.course_user_notification import CourseUserNotification
from app.config import settings
from app.services.entitlements.state import EntitlementState, resolve_state
from app.services.course_notification_service import CourseNotificationService
from app.services.notification_delivery_service import (
    DELIVERED,
    NotificationDeliveryService,
    TelegramNotice,
)


logger = logging.getLogger(__name__)


#: Qaysi kunlarda xabar yuboriladi (trial tugashiga necha kun qolganda).
REMINDER_DAYS = (2, 0)

MAX_BATCH = 200
TWO_DAY_NOTICE_WINDOW = timedelta(hours=48)
FINAL_DAY_NOTICE_WINDOW = timedelta(hours=24)
# Do not send a misleading "2 days" reminder just before the final-day
# notice. The scheduler runs every minute; 12h slack covers missed runs.
TWO_DAY_MAX_LATE = timedelta(hours=12)


def _due_notice_slot(ends_at: datetime, now: datetime) -> int | None:
    """At-or-after the real T-48h threshold, never at T-49h or T-72h.

    The existing second notification stays in the final 24h. There are
    still only TWO stable dedupe keys per trial, not hourly notifications.
    """
    remaining = ends_at - now
    if remaining <= timedelta(0):
        return None
    if remaining <= FINAL_DAY_NOTICE_WINDOW:
        return 0
    if TWO_DAY_NOTICE_WINDOW - TWO_DAY_MAX_LATE <= remaining <= TWO_DAY_NOTICE_WINDOW:
        return 2
    return None


def _as_utc(value: datetime | None) -> datetime | None:
    if not value:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class TrialReminderService:
    def __init__(self, session):
        self.session = session

    async def send_due_reminders(self, bot: Bot, *, now: datetime | None = None) -> int:
        now = now or datetime.now(timezone.utc)
        # Only due notice windows enter the bounded DB batch. Previously the
        # first 200 not-yet-due trials (48–72h away) could consume the entire
        # query result and starve an actual T-48h reminder.
        # Exclude rows already recorded for the relevant slot before LIMIT.
        # If more than MAX_BATCH users have the same due window, the next
        # scheduler pass must reach the next unsent page, not re-scan the same
        # first 200 users indefinitely. Trials are one-time per account.
        def not_already_recorded(slot: int):
            return ~exists(
                select(CourseUserNotification.id)
                .where(
                    CourseUserNotification.user_id == User.id,
                    CourseUserNotification.source == "trial_reminder",
                    CourseUserNotification.dedupe_key.like(
                        f"trial_reminder:%:{slot}"
                    ),
                )
                .correlate(User)
            )

        last_day = and_(
            User.pro_trial_ends_at <= now + FINAL_DAY_NOTICE_WINDOW,
            not_already_recorded(0),
        )
        two_day = and_(
            User.pro_trial_ends_at >= now + TWO_DAY_NOTICE_WINDOW - TWO_DAY_MAX_LATE,
            User.pro_trial_ends_at <= now + TWO_DAY_NOTICE_WINDOW,
            not_already_recorded(2),
        )
        result = await self.session.execute(
            select(User)
            .where(
                User.pro_trial_ends_at.is_not(None),
                User.pro_trial_ends_at > now,
                or_(last_day, two_day),
                User.pro_trial_revoked_at.is_(None),
                User.status != "blocked",
                # Applying LIMIT before checking entitlement could repeatedly
                # select 200 paid or referral/bonus users with stale trial dates,
                # permanently starving genuinely due trials behind them.
                # Mirror the canonical PAID/TEMP precedence at SQL selection;
                # a pending receipt + active trial must remain eligible.
                ~and_(
                    User.status == "active",
                    User.end_date.is_not(None),
                    User.end_date > now,
                    or_(
                        User.payment_status == "approved",
                        User.payment_preview_payment_id.is_(None),
                    ),
                ),
            )
            .order_by(User.pro_trial_ends_at.asc(), User.id.asc())
            .limit(MAX_BATCH)
        )
        users = list(result.scalars().all())

        notifications = CourseNotificationService(self.session)
        delivery = NotificationDeliveryService(self.session)
        sent = 0

        for user in users:
            # A paid subscriber may still have a historical, unexpired
            # pro_trial_ends_at column. Sending "trial almost over" to that
            # person is misleading, even if their old trial has not expired.
            # Use the single entitlement resolver, matching Web Push dispatch.
            if resolve_state(user, now=now) != EntitlementState.TRIAL_ACTIVE:
                continue
            if not await delivery.reachable(user):
                continue
            ends_at = _as_utc(user.pro_trial_ends_at)
            if not ends_at:
                continue
            # A real 48h due threshold, not the floor of timedelta.days.
            days_left = _due_notice_slot(ends_at, now)
            if days_left not in REMINDER_DAYS:
                continue

            lang = user.language or "ru"
            key = "trial_expiring_soon" if days_left else "trial_expired_notice"
            text = (
                t(key, lang, days=days_left) if days_left else t(key, lang)
            )
            dedupe = f"trial_reminder:{ends_at.date().isoformat()}:{days_left}"

            # PWA Home Screen opt-in takes ownership of the T-48h notice.
            # The already-existing generic learner push outbox is one event
            # per browser subscription. No extra Web Push engine or permission
            # is invented, and we don't also dispatch Telegram/Android for
            # the same reminder when its PWA event was durably queued.
            pwa_ready = False
            if days_left == 2 and type(getattr(user, "id", None)) is int:
                try:
                    from app.services.learner_pwa_push import (
                        active_subscriptions, enqueue_event, sender_config,
                    )
                    pwa_ready = bool(
                        sender_config(settings) is not None
                        and await active_subscriptions(self.session, user.id, now=now, limit=1)
                    )
                except Exception:  # noqa: BLE001 - existing Android/TG route remains available
                    logger.warning("Trial 48h PWA push eligibility unavailable")
                    pwa_ready = False

            # FIRST persist the common Inbox record, then transport it once.
            # The record is the existing dedupe owner for this trial window.
            if not await notifications.record_from_text(
                user,
                key="trial_expiring",
                lang=lang,
                text=text,
                action="subscription",
                source="trial_reminder",
                dedupe_key=dedupe,
                params={"days_left": days_left},
                pwa_push_suppressed=True,
            ):
                continue

            if pwa_ready:
                try:
                    notice_id = await self.session.scalar(
                        select(CourseUserNotification.id).where(
                            CourseUserNotification.user_id == user.id,
                            CourseUserNotification.dedupe_key == dedupe,
                        )
                    )
                    queued = await enqueue_event(
                        self.session, user_id=user.id, source="course",
                        source_id=notice_id, language=lang, now=now,
                    ) if notice_id is not None else 0
                    if queued:
                        # Durable outbox: "queued" is NOT provider delivered
                        # and is intentionally not included in sent count.
                        continue
                except Exception:  # noqa: BLE001 - fallback to established channel
                    logger.warning("Trial 48h PWA enqueue unavailable")
            # Existing Android-first then Telegram fallback when no opted-in
            # PWA delivery could be queued. Never send two user-visible
            # transport copies from this trial reminder execution.

            # Android ilova birinchi; telefon ko'rsata olmasa — Telegram.
            outcome = await delivery.deliver(
                bot,
                user,
                key="trial_expiring",
                lang=lang,
                telegram=TelegramNotice(
                    text=text,
                    parse_mode="HTML",
                    reply_markup=subscription_miniapp_keyboard(
                        lang,
                        source="trial_reminder",
                        mode="subscription",
                    ),
                ),
                reason="trial_reminder",
            )
            if outcome not in DELIVERED:
                continue
            sent += 1

        await self.session.commit()
        return sent
