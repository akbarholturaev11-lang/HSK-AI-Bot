from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import and_, func, or_, select

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
from app.db.models.user import User
from app.db.models.voice_practice_session import VoicePracticeSession
from app.services.admin_stats_service import miniapp_course_stats
from app.services.required_channel_service import RequiredChannelService
from app.services.bot_block_status_service import BotBlockStatusService
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


def _pct(part: int, total: int) -> float:
    return round(part / total * 100, 1) if total > 0 else 0.0


def _usd(value: float) -> str:
    try:
        return f"${float(value or 0):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def _amount_to_usd(amount, currency: str | None, *, base_amount=None) -> float:
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
    return 0.0


def _duration_seconds(start: datetime | None, end: datetime | None, *, cap_seconds: int = 8 * 60 * 60) -> int:
    start = _as_utc(start)
    end = _as_utc(end)
    if not start or not end or end < start:
        return 0
    seconds = int((end - start).total_seconds())
    if seconds <= 0 or seconds > cap_seconds:
        return 0
    return seconds


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


def _hot_lead_filter(hot_since: datetime):
    return (
        User.status.in_(HOT_LEAD_STATUSES),
        User.payment_status.in_(HOT_LEAD_PAYMENT_STATUSES),
        User.last_active_at >= hot_since,
        _bot_not_blocked_filter(),
    )


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
        historical_approved_users = await self._count_users(User.payment_status == "approved")
        bot_blocked_users = await self._count_users(*_bot_block_filter())

        miniapp_course = await miniapp_course_stats(self.session)
        avg_sections = (
            round(miniapp_course.completed_sections / miniapp_course.completed_users, 1)
            if miniapp_course.completed_users > 0
            else 0
        )

        channels_enabled = await RequiredChannelService(self.session).is_enabled()
        channel_rows = await self._required_channels()
        active_channels = len([item for item in channel_rows if item["enabled"]])
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
            two_day_start_date=two_day_start_date,
        )
        latest_payments = await self._latest_payments()

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
        hot_leads = int(course_hot.get("last_2_days_users", 0))
        qa_users = await self._count_users(User.questions_used > 0)
        conversion = _pct(paid_users, total)
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
            "report_text": report_text,
            "statistics_reports": period_reports,
            "summary": [
                {"label": "Фойдаланувчилар", "value": total, "note": f"{active_today} бугун фаол", "tone": "info"},
                {"label": "Фаол обуна", "value": paid_users, "note": "ҳозир тўловли", "tone": "good"},
                {"label": "Тўлов текширувда", "value": pending_payments, "note": "админ кўриши керак", "tone": "warn"},
                {
                    "label": "Course иссиқ user",
                    "value": hot_leads,
                    "note": f"бугун {course_hot.get('today_users', 0)} user · 3+ streak {course_hot.get('streak_3_users', 0)}",
                    "tone": "danger",
                },
            ],
            "counts": {
                "users_total": total,
                "paid_users": paid_users,
                "pending_payments": pending_payments,
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
                "pending": pending_payments,
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
        stmt = select(
            Payment.payment_status,
            func.count().label("cnt"),
            func.coalesce(func.sum(Payment.amount), 0).label("total_sum"),
        ).group_by(Payment.payment_status)
        if since is not None:
            stmt = stmt.where(Payment.submitted_at >= since)
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

    async def _period_reports(
        self,
        *,
        now: datetime,
        week_ago: datetime,
        month_ago: datetime,
        all_course_stats,
    ) -> list[dict]:
        return [
            await self._period_report(
                key="weekly",
                title="Ҳафталик",
                note="Охирги 7 кун",
                since=week_ago,
                now=now,
            ),
            await self._period_report(
                key="monthly",
                title="Ойлик",
                note="Охирги 30 кун",
                since=month_ago,
                now=now,
            ),
            await self._period_report(
                key="all_time",
                title="Тўлиқ",
                note="Бутун база",
                since=None,
                now=now,
                course_stats=all_course_stats,
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
    ) -> dict:
        if since is None:
            user_count = await self._count_users()
            active_users = user_count
            bot_blocked = await self._count_users(*_bot_block_filter())
        else:
            user_count = await self._count_users(User.created_at >= since)
            active_users = await self._count_users(User.last_active_at >= since)
            bot_blocked = await self._count_users(User.bot_blocked_at >= since)

        payment_status = await self._payment_status_counts(since)
        pending_payments = int(payment_status.get("pending", {}).get("count", 0))
        approved_payments = int(payment_status.get("approved", {}).get("count", 0))
        rejected_payments = int(payment_status.get("rejected", {}).get("count", 0))
        approved_total_text = _currency_total(await self._approved_currency_totals(since))
        approved_users = await self._approved_payment_user_count(since)
        plan_counts = await self._payment_plan_counts(since)
        course = course_stats or await miniapp_course_stats(self.session, since=since)
        advanced = await self._advanced_stats(since=since, now=now)

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
        }
        report = {
            "key": key,
            "title": title,
            "note": note,
            "generated_at": _dt(now),
            "metrics": metrics,
            "cards": [
                {"label": "Фойдаланувчи", "value": user_count, "note": "янги" if since else "жами база", "tone": "info"},
                {"label": "Фаол", "value": active_users, "note": "шу даврда" if since else "жами база", "tone": "good"},
                {"label": "Тасдиқланган тўлов", "value": approved_users, "note": approved_total_text, "tone": "good"},
                {"label": "Тўлов текширувда", "value": pending_payments, "note": "шу даврда юборилган", "tone": "warn"},
                {"label": "Курс очилди", "value": course.opened_users, "note": f"тугатиш {metrics['course_completion']}%", "tone": "info"},
                {"label": "Дарс тугади", "value": course.completed_users, "note": f"{course.completed_book_lessons} та дарс", "tone": "good"},
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
            },
            "advanced": advanced,
        }
        report["text"] = self._period_report_text(report)
        return report

    async def _advanced_stats(self, *, since: datetime | None, now: datetime) -> dict:
        retention = await self._retention_stats(since=since, now=now)
        session_time = await self._miniapp_session_time(since=since)
        lesson_time = await self._lesson_time(since=since)
        qa = await self._qa_message_stats(since=since)
        voice = await self._voice_minutes(since=since)
        payment = await self._payment_advanced_stats(since=since)
        feature_adoption = await self._feature_adoption(since=since, now=now)
        notifications = await self._notification_open_proxy(since=since)

        return {
            "explain": (
                "Bu blok product health metrikalarini ko'rsatadi: retention, Mini App vaqt, dars vaqti, "
                "QA/Voice ishlatilishi, payment funnel, LTV/CAC, paid/free feature adoption va notification open proxy. "
                "Hamma raqamlar tanlangan davr ichida qayta hisoblanadi."
            ),
            "cards": [
                {
                    "label": "D1 retention",
                    "value": f"{retention['d1']['rate']}%",
                    "note": f"{retention['d1']['retained']}/{retention['d1']['eligible']} user",
                    "tone": "good",
                },
                {
                    "label": "D7 retention",
                    "value": f"{retention['d7']['rate']}%",
                    "note": f"{retention['d7']['retained']}/{retention['d7']['eligible']} user",
                    "tone": "good",
                },
                {
                    "label": "Avg session",
                    "value": session_time["avg_text"],
                    "note": f"{session_time['sessions']} Mini App session",
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
                    "label": "LTV",
                    "value": payment["ltv_text"],
                    "note": f"{payment['paying_users']} pullik user",
                    "tone": "good",
                },
                {
                    "label": "CAC",
                    "value": payment["cac_text"],
                    "note": payment["cac_note"],
                    "tone": "warn" if payment["marketing_expense_usd"] else "info",
                },
                {
                    "label": "Notif open",
                    "value": f"{notifications['open_rate']}%",
                    "note": f"{notifications['opened_after']} / {notifications['sent']} proxy",
                    "tone": "info",
                },
            ],
            "retention": retention,
            "session_time": session_time,
            "lesson_time": lesson_time,
            "qa": qa,
            "voice": voice,
            "payment": payment,
            "feature_adoption": feature_adoption,
            "notifications": notifications,
        }

    async def _retention_stats(self, *, since: datetime | None, now: datetime) -> dict:
        stmt = select(User.created_at, User.last_active_at).select_from(User)
        if since is not None:
            stmt = stmt.where(User.created_at >= since)
        rows = (await self.session.execute(stmt)).all()

        def calc(days: int) -> dict:
            eligible = 0
            retained = 0
            for created_at, last_active_at in rows:
                created = _as_utc(created_at)
                last_active = _as_utc(last_active_at)
                if not created:
                    continue
                threshold = created + timedelta(days=days)
                if threshold > now:
                    continue
                eligible += 1
                if last_active and last_active >= threshold:
                    retained += 1
            return {"eligible": eligible, "retained": retained, "rate": _pct(retained, eligible)}

        return {
            "d1": calc(1),
            "d7": calc(7),
            "explain": (
                "D1/D7 retention = shu davrda ro'yxatdan o'tgan va 1/7 kun o'tishga ulgurgan userlardan "
                "keyin yana aktiv bo'lganlari. Aktivlik User.last_active_at orqali olinadi."
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
        bounds: dict[tuple[int, str], list[datetime | None]] = {}
        for telegram_id, session_id, created_at in rows:
            key = (int(telegram_id), str(session_id))
            if key not in bounds:
                bounds[key] = [created_at, created_at]
                continue
            if created_at < bounds[key][0]:
                bounds[key][0] = created_at
            if created_at > bounds[key][1]:
                bounds[key][1] = created_at
        durations = [_duration_seconds(start, end) for start, end in bounds.values()]
        durations = [seconds for seconds in durations if seconds > 0]
        avg_seconds = round(sum(durations) / len(durations)) if durations else 0
        return {
            "sessions": len(durations),
            "avg_seconds": avg_seconds,
            "avg_text": _duration_text(avg_seconds),
            "total_text": _duration_text(sum(durations)),
            "explain": "Mini App session vaqti session_id bo'yicha birinchi va oxirgi event oralig'idan olinadi.",
        }

    async def _lesson_time(self, *, since: datetime | None) -> dict:
        event_names = (
            "lesson_started",
            "section_started",
            "section_completed",
            "book_lesson_completed",
            "lesson_completed",
        )
        conditions = [CourseMiniAppEvent.event_name.in_(event_names)]
        if since is not None:
            conditions.append(CourseMiniAppEvent.created_at >= since)
        rows = (
            await self.session.execute(
                select(
                    CourseMiniAppEvent.telegram_id,
                    CourseMiniAppEvent.level,
                    CourseMiniAppEvent.lesson_id,
                    CourseMiniAppEvent.lesson_order,
                    CourseMiniAppEvent.event_name,
                    CourseMiniAppEvent.created_at,
                ).where(*conditions)
            )
        ).all()
        started_names = {"lesson_started", "section_started"}
        completed_names = {"section_completed", "book_lesson_completed", "lesson_completed"}
        grouped: dict[tuple, dict[str, datetime | None]] = defaultdict(lambda: {"start": None, "end": None})
        for telegram_id, level, lesson_id, lesson_order, event_name, created_at in rows:
            lesson_ref = lesson_id if lesson_id is not None else f"{level or 'unknown'}:{lesson_order or 0}"
            key = (int(telegram_id), lesson_ref)
            bucket = grouped[key]
            if event_name in started_names and (bucket["start"] is None or created_at < bucket["start"]):
                bucket["start"] = created_at
            if event_name in completed_names and (bucket["end"] is None or created_at > bucket["end"]):
                bucket["end"] = created_at
        durations = [_duration_seconds(item["start"], item["end"]) for item in grouped.values()]
        durations = [seconds for seconds in durations if seconds > 0]
        avg_seconds = round(sum(durations) / len(durations)) if durations else 0
        return {
            "completed_lessons": len(durations),
            "avg_seconds": avg_seconds,
            "avg_text": _duration_text(avg_seconds),
            "total_text": _duration_text(sum(durations)),
            "explain": "Lesson time = dars/qism boshlanganidan shu dars bo'yicha oxirgi completion eventgacha bo'lgan vaqt.",
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
            approved.append(
                {
                    "user_id": int(user_id),
                    "at": at,
                    "usd": _amount_to_usd(amount, currency, base_amount=base_amount),
                }
            )
        in_period = [item for item in approved if since is None or item["at"] >= since]
        revenue_usd = sum(item["usd"] for item in in_period)
        paying_users = len({item["user_id"] for item in in_period})
        ltv = revenue_usd / paying_users if paying_users else 0.0

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
            "ltv_usd": round(ltv, 2),
            "ltv_text": _usd(ltv),
            "first_payment_users": new_paying_users,
            "first_payment_time_seconds": avg_first_seconds,
            "first_payment_time_text": _duration_text(avg_first_seconds),
            "marketing_expense_usd": round(marketing_expense_usd, 2),
            "marketing_expense_text": _usd(marketing_expense_usd),
            "cac_usd": round(cac, 2),
            "cac_text": _usd(cac) if marketing_expense_usd else "—",
            "cac_note": (
                f"{new_paying_users} yangi pullik user"
                if marketing_expense_usd
                else "marketing xarajat kiritilmagan"
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
        event_names = ("paywall_seen", "checkout_opened", "payment_screenshot_submitted", "payment_approved")
        conditions = [ConversionFunnelEvent.event_name.in_(event_names)]
        if since is not None:
            conditions.append(ConversionFunnelEvent.created_at >= since)
        rows = (
            await self.session.execute(
                select(
                    ConversionFunnelEvent.event_name,
                    func.count(func.distinct(ConversionFunnelEvent.telegram_id)).label("users"),
                )
                .where(*conditions)
                .group_by(ConversionFunnelEvent.event_name)
            )
        ).all()
        counts = {str(row.event_name): int(row.users or 0) for row in rows}
        steps = [
            {"key": "paywall_seen", "label": "To'lov oynasi", "users": counts.get("paywall_seen", 0)},
            {"key": "checkout_opened", "label": "Checkout ochdi", "users": counts.get("checkout_opened", 0)},
            {"key": "payment_screenshot_submitted", "label": "Skrinshot yubordi", "users": counts.get("payment_screenshot_submitted", 0)},
            {"key": "payment_approved", "label": "Tasdiqlandi", "users": counts.get("payment_approved", 0)},
        ]
        drops = []
        for current, nxt in zip(steps, steps[1:]):
            lost = max(int(current["users"]) - int(nxt["users"]), 0)
            drops.append(
                {
                    "label": f"{current['label']} → {nxt['label']}",
                    "lost": lost,
                    "rate": _pct(lost, int(current["users"])),
                }
            )
        top_drop = max(drops, key=lambda item: item["lost"], default={"label": "Ma'lumot yetarli emas", "lost": 0, "rate": 0.0})
        status_counts = await self._payment_status_counts(since)
        return {
            "steps": steps,
            "drops": drops,
            "abandon_step": top_drop["label"],
            "abandon_count": top_drop["lost"],
            "abandon_rate": top_drop["rate"],
            "payment_status": status_counts,
            "explain": "Payment abandon step = funnel'dagi ketma-ket bosqichlar orasida eng katta yo'qotish.",
        }

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

    async def _notification_open_proxy(self, *, since: datetime | None) -> dict:
        sent_conditions = [CourseMiniAppEvent.event_name == "motivation_lesson_unfinished_sent"]
        open_conditions = [CourseMiniAppEvent.event_name == "miniapp_opened"]
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
        opens_by_user: dict[int, list[datetime]] = defaultdict(list)
        for telegram_id, created_at in open_rows:
            opens_by_user[int(telegram_id)].append(_as_utc(created_at))
        for values in opens_by_user.values():
            values.sort()
        opened_after = 0
        for telegram_id, sent_at in sent_rows:
            sent = _as_utc(sent_at)
            if not sent:
                continue
            deadline = sent + timedelta(hours=48)
            if any(sent <= opened <= deadline for opened in opens_by_user.get(int(telegram_id), []) if opened):
                opened_after += 1
        sent_count = len(sent_rows)
        return {
            "sent": sent_count,
            "opened_after": opened_after,
            "open_rate": _pct(opened_after, sent_count),
            "explain": "Telegram notification direct open event bermaydi; bu 48 soat ichida Mini App ochilganini proxy sifatida ko'rsatadi.",
        }

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
            "delivered": int(by_status.get("delivered", 0) or by_status.get("sent", 0) or 0),
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
                "Course issiq userlar CourseXpEvent.created_at va CourseMiniAppProfile.last_activity_date "
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
        two_day_start_date,
    ) -> list[dict]:
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
                "plan": _plan_label(item.selected_plan_type),
                "method": _method_label(item.payment_method),
                "end_date": _dt(item.end_date),
                "last_active": _ago(item.last_active_at, now=now),
                "active_today": is_admin_active_today(item, today_start),
                "hot_lead": is_admin_course_hot_user(item, profile, two_day_start_date),
                "questions": f"{item.questions_used}/{item.question_limit}",
                "bonus_left": max((item.bonus_questions or 0) - (item.bonus_questions_used or 0), 0),
                "streak": int(getattr(profile, "current_streak", 0) or 0),
                "course_last_activity_date": str(getattr(profile, "last_activity_date", "") or ""),
            }
            for item, profile in rows
        ]

    async def _latest_payments(self) -> list[dict]:
        rows = (await self.session.execute(
            select(Payment, User)
            .outerjoin(User, User.telegram_id == Payment.user_telegram_id)
            .order_by(Payment.submitted_at.desc())
            .limit(60)
        )).all()
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
            f"Фаол: {metrics.get('active_users', 0)}\n"
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
            f"Курс тугатиш: {metrics.get('course_completion', 0)}%"
        ) + AdminMiniAppService._advanced_report_text(report.get("advanced") or {})

    @staticmethod
    def _advanced_report_text(advanced: dict) -> str:
        if not advanced:
            return ""
        retention = advanced.get("retention") or {}
        d1 = retention.get("d1") or {}
        d7 = retention.get("d7") or {}
        session_time = advanced.get("session_time") or {}
        lesson_time = advanced.get("lesson_time") or {}
        qa = advanced.get("qa") or {}
        voice = advanced.get("voice") or {}
        payment = advanced.get("payment") or {}
        funnel = payment.get("funnel") or {}
        notifications = advanced.get("notifications") or {}
        return (
            "\n\n"
            "📌 ҚЎШИМЧА PRODUCT МЕТРИКАЛАР\n"
            "Бу блок retention, вақт, QA/Voice, payment abandon, LTV/CAC ва feature adoption'ни кўрсатади.\n"
            f"D1 retention: {d1.get('rate', 0)}% ({d1.get('retained', 0)}/{d1.get('eligible', 0)})\n"
            f"D7 retention: {d7.get('rate', 0)}% ({d7.get('retained', 0)}/{d7.get('eligible', 0)})\n"
            f"Avg Mini App session: {session_time.get('avg_text', '—')} · session: {session_time.get('sessions', 0)}\n"
            f"Lesson time: {lesson_time.get('avg_text', '—')} · tugagan dars: {lesson_time.get('completed_lessons', 0)}\n"
            f"AI chat message/user: {qa.get('avg_per_user', 0)} · xabar: {qa.get('messages', 0)} · user: {qa.get('users', 0)}\n"
            f"Voice minutes: {voice.get('minutes_text', '0 min')} · avg: {voice.get('avg_text', '—')}\n"
            f"Payment abandon: {funnel.get('abandon_step', '—')} · yo'qotish: {funnel.get('abandon_count', 0)} ({funnel.get('abandon_rate', 0)}%)\n"
            f"First payment time: {payment.get('first_payment_time_text', '—')} · first pay user: {payment.get('first_payment_users', 0)}\n"
            f"LTV: {payment.get('ltv_text', '—')} · CAC: {payment.get('cac_text', '—')}\n"
            f"Notification open proxy: {notifications.get('open_rate', 0)}% ({notifications.get('opened_after', 0)}/{notifications.get('sent', 0)})"
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
            f"Фойдаланувчи → тўловли: {conversion}%\n"
            f"Лимит ҳисобида савол ишлатган user: {qa_users} ({engagement}%)"
        )
