from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select

from app.db.models.ad_campaign import AdCampaign, AdCampaignDelivery
from app.db.models.bot_feedback import BotFeedback
from app.db.models.payment import Payment
from app.db.models.referral import Referral
from app.db.models.required_channel import RequiredChannel
from app.db.models.user import User
from app.services.admin_stats_service import miniapp_course_stats
from app.services.required_channel_service import RequiredChannelService
from app.services.subscription_entry_analytics_service import SubscriptionEntryAnalyticsService
from app.services.subscription_price_service import SubscriptionPriceService
from app.services.subscription_currency_service import format_subscription_price


ADMIN_MINIAPP_TZ = ZoneInfo("Asia/Shanghai")


def _pct(part: int, total: int) -> float:
    return round(part / total * 100, 1) if total > 0 else 0.0


def _dt(value: datetime | None) -> str | None:
    if not value:
        return None
    try:
        return value.astimezone(ADMIN_MINIAPP_TZ).strftime("%d.%m.%Y %H:%M")
    except Exception:
        return str(value)


def _ago(value: datetime | None, *, now: datetime) -> str:
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
        today_start = now.astimezone(ADMIN_MINIAPP_TZ).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        ).astimezone(timezone.utc)
        last_24h = now - timedelta(hours=24)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

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
        latest_users = await self._latest_users(now)
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
        wants_pay = await self._count_users(
            User.status.in_(("free", "trial", "expired")),
            User.payment_status.in_(("none", "draft", "rejected")),
        )
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

        return {
            "ok": True,
            "generated_at": _dt(now),
            "report_text": report_text,
            "summary": [
                {"label": "Фойдаланувчилар", "value": total, "note": f"{active_today} бугун фаол", "tone": "info"},
                {"label": "Фаол обуна", "value": paid_users, "note": "ҳозир тўловли", "tone": "good"},
                {"label": "Тўлов текширувда", "value": pending_payments, "note": "админ кўриши керак", "tone": "warn"},
                {"label": "Иссиқ мижозлар", "value": wants_pay + expired_hot, "note": "обунага яқин", "tone": "danger"},
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
                "expiring_soon": expiring_soon,
                "conversion": conversion,
                "engagement": engagement,
            },
            "segments": {
                "all": total,
                "paid": paid_users,
                "pending": pending_payments,
                "wants_pay": wants_pay,
                "trial": int(status_counts.get("trial", 0)),
                "expired": int(status_counts.get("expired", 0)),
                "blocked": int(status_counts.get("blocked", 0)),
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

    async def _payment_status_counts(self) -> dict[str, dict[str, int]]:
        rows = (await self.session.execute(
            select(
                Payment.payment_status,
                func.count().label("cnt"),
                func.coalesce(func.sum(Payment.amount), 0).label("total_sum"),
            ).group_by(Payment.payment_status)
        )).fetchall()
        return {
            str(row.payment_status or "—"): {
                "count": int(row.cnt or 0),
                "amount": int(row.total_sum or 0),
            }
            for row in rows
        }

    async def _payment_plan_counts(self) -> dict[str, int]:
        rows = (await self.session.execute(
            select(Payment.plan_type, func.count().label("cnt"))
            .where(Payment.payment_status == "approved")
            .group_by(Payment.plan_type)
        )).fetchall()
        return {str(row.plan_type or "—"): int(row.cnt or 0) for row in rows}

    async def _approved_currency_totals(self):
        return (await self.session.execute(
            select(Payment.currency, func.sum(Payment.amount).label("total_sum"))
            .where(Payment.payment_status == "approved")
            .group_by(Payment.currency)
        )).fetchall()

    async def _paid_user_count(self, now: datetime) -> int:
        return await self._count_users(
            User.payment_status == "approved",
            User.status == "active",
            User.end_date.is_not(None),
            User.end_date > now,
        )

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

    async def _latest_users(self, now: datetime) -> list[dict]:
        rows = (await self.session.execute(
            select(User).order_by(User.last_active_at.desc()).limit(120)
        )).scalars().all()
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
                "payment_status": item.payment_status,
                "payment_label": _payment_label(item.payment_status),
                "plan": _plan_label(item.selected_plan_type),
                "method": _method_label(item.payment_method),
                "end_date": _dt(item.end_date),
                "last_active": _ago(item.last_active_at, now=now),
                "questions": f"{item.questions_used}/{item.question_limit}",
                "bonus_left": max((item.bonus_questions or 0) - (item.bonus_questions_used or 0), 0),
                "streak": item.daily_practice_streak or 0,
            }
            for item in rows
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
            f"Савол берганлар: {qa_users} ({engagement}%)"
        )
