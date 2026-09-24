from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.db.models.bot_outbound_event import BotOutboundEvent
from app.db.models.bot_reachability_event import BotReachabilityEvent
from app.db.models.conversion_funnel_event import ConversionFunnelEvent
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.message import Message
from app.services.app_error_context_service import APP_ERROR_CONTENT_TYPE
from app.services.bot_block_status_service import BotBlockStatusService


class BotBlockCauseService:
    """Build an evidence-based *probable* block cause for the admin panel.

    Telegram does not expose a human-written "reason for blocking the bot".
    Therefore this service never claims causation as fact. It ranks hypotheses
    from events around the block timestamp and explicitly reports data quality.
    """

    BEFORE_WINDOW = timedelta(hours=24)
    TECH_WINDOW = timedelta(hours=2)
    FRICTION_WINDOW = timedelta(hours=2)

    APP_OPEN_EVENTS = (
        "miniapp_opened",
        "android_app_opened",
        "desktop_app_opened",
    )
    FRICTION_EVENTS = (
        "paywall_seen",
        "checkout_opened",
        "limit_hit",
        "trial_expired",
        "payment_rejected",
        "plan_choice_seen",
    )

    SOURCE_LABELS = {
        "broadcast": "ommaviy xabar",
        "feedback_prompt": "feedback savoli",
        "feedback_price_offer": "feedback taklifi",
        "course_reminder": "dars eslatmasi",
        "course_weekly_progress": "haftalik o'qish hisoboti",
        "motivation_reminder": "motivatsion eslatma",
        "trial_reminder": "Pro trial eslatmasi",
        "daily_reset": "kunlik limit xabari",
        "expiry_reminder": "obuna tugash eslatmasi",
        "ad_campaign": "reklama xabari",
        "discount_notification": "chegirma xabari",
        "release_feedback": "yangilanish feedback xabari",
        "subscription_churn_followup": "obuna follow-up xabari",
        "onboarding_tip": "onboarding maslahati",
        "partner_notification": "hamkorlik xabari",
        "gemini_switch": "AI yangilanish xabari",
        "payment_approved": "to'lov tasdiqlangan xabari",
        "payment_rejected": "to'lov rad etilgan xabari",
        "referral_bonus": "referral bonus xabari",
        "referral_trial_unlocked": "referral orqali ochilgan trial xabari",
        "limit_notice": "limit haqida xabar",
    }

    FRICTION_LABELS = {
        "paywall_seen": "to'lov oynasi ko'rilgan",
        "checkout_opened": "to'lov jarayoni ochilgan",
        "limit_hit": "bepul limit tugagan",
        "trial_expired": "Pro trial tugagan",
        "payment_rejected": "to'lov rad etilgan",
        "plan_choice_seen": "tarif tanlash oynasi ko'rilgan",
    }

    def __init__(self, session):
        self.session = session

    @staticmethod
    def _aware(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _minutes(delta: timedelta) -> int:
        return max(0, int(delta.total_seconds() // 60))

    @staticmethod
    def _confidence(score: int) -> str:
        if score >= 80:
            return "yuqori"
        if score >= 60:
            return "o'rta"
        return "past"

    @staticmethod
    def _candidate(
        *,
        key: str,
        title: str,
        score: int,
        evidence: list[str],
        note: str,
    ) -> dict:
        bounded = max(0, min(100, int(score)))
        return {
            "key": key,
            "title": title,
            "score": bounded,
            "confidence": BotBlockCauseService._confidence(bounded),
            "evidence": evidence,
            "note": note,
        }

    async def analyze(self, user) -> dict:
        if not BotBlockStatusService.is_bot_blocked(user):
            return {
                "available": False,
                "title": "Telegram aloqasi ochiq",
                "confidence": "—",
                "score": 0,
                "data_quality": "not_blocked",
                "data_quality_label": "Block holati yo'q",
                "evidence": [],
                "alternatives": [],
                "disclaimer": "Ehtimoliy sabab faqat Telegram xabari yopiq userlar uchun hisoblanadi.",
            }

        block_at = self._aware(getattr(user, "bot_blocked_at", None))
        if not block_at:
            return self._unknown("Block vaqti saqlanmagan.", data_quality="insufficient")

        episode_event = await self._current_episode_event(user, block_at)
        episode_source = str(getattr(episode_event, "source", "") or "")
        if episode_source == "my_chat_member_blocked":
            data_quality = "direct"
            quality_label = "Yangi tracking · Telegram block eventi aniq"
            score_cap = 95
        elif episode_event is not None:
            data_quality = "detected"
            quality_label = "Yangi tracking · block yuborish xatosida aniqlangan"
            score_cap = 78
        else:
            data_quality = "legacy"
            quality_label = "Eski yozuv · birinchi block vaqti aniq bo'lmasligi mumkin"
            score_cap = 45

        candidates: list[dict] = []

        app_candidate = await self._app_continuation_candidate(user, block_at)
        if app_candidate:
            candidates.append(app_candidate)

        tech_candidate = await self._technical_candidate(user, block_at)
        if tech_candidate:
            candidates.append(tech_candidate)

        notification_candidate = await self._notification_candidate(user, block_at)
        if notification_candidate:
            candidates.append(notification_candidate)

        friction_candidate = await self._friction_candidate(user, block_at)
        if friction_candidate:
            candidates.append(friction_candidate)

        onboarding_candidate = await self._onboarding_candidate(user, block_at)
        if onboarding_candidate:
            candidates.append(onboarding_candidate)

        # Historical rows were overwritten by the old implementation. Never
        # show an artificially strong conclusion for them.
        for item in candidates:
            item["score"] = min(int(item["score"]), score_cap)
            item["confidence"] = self._confidence(item["score"])

        candidates.sort(key=lambda item: (-int(item["score"]), item["title"]))

        if not candidates:
            result = self._unknown(
                "Block atrofida sababni ajratishga yetarli event topilmadi.",
                data_quality=data_quality,
            )
            result["data_quality_label"] = quality_label
            return result

        primary = candidates[0]
        return {
            "available": True,
            "title": primary["title"],
            "key": primary["key"],
            "confidence": primary["confidence"],
            "score": primary["score"],
            "data_quality": data_quality,
            "data_quality_label": quality_label,
            "block_at": block_at.isoformat(),
            "evidence": primary["evidence"],
            "note": primary["note"],
            "alternatives": candidates[1:3],
            "disclaimer": (
                "Bu Telegram bergan aniq sabab emas. Tizim block oldi/ketidagi real eventlarni "
                "solishtirib eng kuchli ehtimolni ko'rsatadi."
            ),
        }

    async def _current_episode_event(self, user, block_at: datetime):
        row = (
            await self.session.execute(
                select(BotReachabilityEvent)
                .where(
                    BotReachabilityEvent.telegram_id == int(user.telegram_id),
                    BotReachabilityEvent.event_type == "blocked",
                    BotReachabilityEvent.created_at >= block_at - timedelta(minutes=2),
                    BotReachabilityEvent.created_at <= block_at + timedelta(minutes=2),
                )
                .order_by(BotReachabilityEvent.created_at.desc(), BotReachabilityEvent.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        return row

    async def _app_continuation_candidate(self, user, block_at: datetime) -> dict | None:
        rows = (
            await self.session.execute(
                select(
                    CourseMiniAppEvent.event_name,
                    func.min(CourseMiniAppEvent.created_at).label("first_at"),
                    func.max(CourseMiniAppEvent.created_at).label("last_at"),
                    func.count().label("cnt"),
                )
                .where(
                    CourseMiniAppEvent.telegram_id == int(user.telegram_id),
                    CourseMiniAppEvent.event_name.in_(self.APP_OPEN_EVENTS),
                    CourseMiniAppEvent.created_at >= block_at,
                )
                .group_by(CourseMiniAppEvent.event_name)
            )
        ).all()
        if not rows:
            return None

        label_by_event = {
            "miniapp_opened": "Mini App",
            "android_app_opened": "Android",
            "desktop_app_opened": "Desktop",
        }
        evidence = []
        total = 0
        earliest = None
        for row in rows:
            total += int(row.cnt or 0)
            first_at = self._aware(row.first_at)
            if first_at and (earliest is None or first_at < earliest):
                earliest = first_at
            evidence.append(
                f"{label_by_event.get(str(row.event_name), str(row.event_name))} blockdan keyin "
                f"{int(row.cnt or 0)} marta ochilgan"
            )

        minutes = self._minutes(earliest - block_at) if earliest else 0
        if earliest:
            evidence.append(f"Birinchi app faolligi blockdan {minutes} daqiqa keyin qayd etilgan")

        score = 88 if minutes <= 24 * 60 else 78
        return self._candidate(
            key="channel_migration",
            title="Telegram kerak bo'lmay qolgan yoki ilovaga o'tgan bo'lishi mumkin",
            score=score,
            evidence=evidence[:4],
            note=(
                "Bu user HSK AI'ni tashlaganini ko'rsatmaydi: Telegram yopilgandan keyin ham "
                "HSK AI clientlaridan foydalanish davom etgan."
            ),
        )

    async def _technical_candidate(self, user, block_at: datetime) -> dict | None:
        start = block_at - self.TECH_WINDOW
        rows = list(
            (
                await self.session.execute(
                    select(Message)
                    .where(
                        Message.user_id == int(user.id),
                        Message.content_type == APP_ERROR_CONTENT_TYPE,
                        Message.created_at >= start,
                        Message.created_at <= block_at,
                    )
                    .order_by(Message.created_at.desc())
                    .limit(5)
                )
            ).scalars().all()
        )
        if not rows:
            return None

        closest = self._aware(rows[0].created_at)
        minutes = self._minutes(block_at - closest) if closest else 120
        if minutes <= 15:
            score = 92
        elif minutes <= 60:
            score = 80
        else:
            score = 66

        evidence = [
            f"Blockdan {minutes} daqiqa oldin ilova xatosi qayd etilgan",
            f"Oxirgi 2 soatda {len(rows)} ta texnik xato qayd etilgan",
        ]
        return self._candidate(
            key="technical_issue",
            title="Texnik xato sabab bo'lgan bo'lishi mumkin",
            score=score,
            evidence=evidence,
            note=(
                "Vaqt bo'yicha xato blockka juda yaqin. Bu kuchli signal, lekin userning o'zi "
                "sababni tasdiqlamagan."
            ),
        )

    async def _notification_candidate(self, user, block_at: datetime) -> dict | None:
        start = block_at - self.BEFORE_WINDOW
        rows = list(
            (
                await self.session.execute(
                    select(BotOutboundEvent)
                    .where(
                        BotOutboundEvent.telegram_id == int(user.telegram_id),
                        BotOutboundEvent.status == "sent",
                        BotOutboundEvent.created_at >= start,
                        BotOutboundEvent.created_at <= block_at,
                    )
                    .order_by(BotOutboundEvent.created_at.desc())
                    .limit(30)
                )
            ).scalars().all()
        )
        if not rows:
            return None

        latest_at = self._aware(rows[0].created_at)
        latest_minutes = self._minutes(block_at - latest_at) if latest_at else 24 * 60
        counts = Counter(str(row.source or "unknown") for row in rows)
        top_source, top_count = counts.most_common(1)[0]

        if len(rows) >= 4 and latest_minutes <= 30:
            score = 90
        elif len(rows) >= 3 and latest_minutes <= 60:
            score = 82
        elif len(rows) >= 2 and latest_minutes <= 30:
            score = 72
        elif latest_minutes <= 10:
            score = 58
        else:
            return None

        source_label = self.SOURCE_LABELS.get(top_source, top_source)
        evidence = [
            f"Blockdan oldingi 24 soatda {len(rows)} ta avtomatik Telegram xabari muvaffaqiyatli yetgan",
            f"Oxirgi xabar blockdan {latest_minutes} daqiqa oldin yetgan",
        ]
        if top_count > 1:
            evidence.append(f"Eng ko'p takrorlangan tur: {source_label} · {top_count} marta")

        return self._candidate(
            key="notification_pressure",
            title="Xabarlar ko'pligi bezovta qilgan bo'lishi mumkin",
            score=score,
            evidence=evidence,
            note=(
                "Bu xulosada faqat blockdan OLDIN muvaffaqiyatli yetgan xabarlar hisoblanadi. "
                "Blockni aniqlagan muvaffaqiyatsiz xabarning o'zi sabab deb olinmaydi."
            ),
        )

    async def _friction_candidate(self, user, block_at: datetime) -> dict | None:
        start = block_at - self.FRICTION_WINDOW
        rows = (
            await self.session.execute(
                select(ConversionFunnelEvent)
                .where(
                    ConversionFunnelEvent.telegram_id == int(user.telegram_id),
                    ConversionFunnelEvent.event_name.in_(self.FRICTION_EVENTS),
                    ConversionFunnelEvent.created_at >= start,
                    ConversionFunnelEvent.created_at <= block_at,
                )
                .order_by(ConversionFunnelEvent.created_at.desc())
                .limit(8)
            )
        ).scalars().all()
        rows = list(rows)
        if not rows:
            return None

        latest = rows[0]
        latest_at = self._aware(latest.created_at)
        minutes = self._minutes(block_at - latest_at) if latest_at else 120
        if minutes <= 15:
            score = 86
        elif minutes <= 60:
            score = 74
        else:
            score = 62

        labels = []
        seen = set()
        for row in rows:
            name = str(row.event_name)
            if name in seen:
                continue
            seen.add(name)
            labels.append(self.FRICTION_LABELS.get(name, name))

        return self._candidate(
            key="paywall_or_limit",
            title="To'lov, limit yoki trial bosqichi ta'sir qilgan bo'lishi mumkin",
            score=score,
            evidence=[
                f"Blockdan {minutes} daqiqa oldin: {self.FRICTION_LABELS.get(str(latest.event_name), str(latest.event_name))}",
                "Yaqin eventlar: " + ", ".join(labels[:4]),
            ],
            note=(
                "Paywall/limit eventining yaqinligi friction signalidir; bu narx yoki paywall aniq "
                "sabab bo'lganini isbotlamaydi."
            ),
        )

    async def _onboarding_candidate(self, user, block_at: datetime) -> dict | None:
        created_at = self._aware(getattr(user, "created_at", None))
        if not created_at:
            return None
        account_age = block_at - created_at
        if account_age > timedelta(hours=24):
            return None

        lesson_started = int(
            (
                await self.session.execute(
                    select(func.count())
                    .select_from(CourseMiniAppEvent)
                    .where(
                        CourseMiniAppEvent.telegram_id == int(user.telegram_id),
                        CourseMiniAppEvent.event_name.in_(("lesson_started", "android_lesson_started")),
                        CourseMiniAppEvent.created_at <= block_at,
                    )
                )
            ).scalar()
            or 0
        )
        if lesson_started:
            return None

        minutes = self._minutes(account_age)
        score = 74 if minutes <= 60 else 62
        return self._candidate(
            key="onboarding_mismatch",
            title="Onboarding yoki kutilgan mahsulot mos kelmagan bo'lishi mumkin",
            score=score,
            evidence=[
                f"User ro'yxatdan o'tgandan {minutes} daqiqa ichida Telegram yopilgan",
                "Blockdan oldin birorta dars boshlangani qayd etilmagan",
            ],
            note=(
                "Bu odatda birinchi taassurot, trafik sifati yoki onboarding mos kelmaganini ko'rsatishi "
                "mumkin; userning o'zi sababni aytmagan."
            ),
        )

    @staticmethod
    def _unknown(message: str, *, data_quality: str) -> dict:
        return {
            "available": False,
            "title": "Sababni ishonchli ajratib bo'lmadi",
            "key": "unknown",
            "confidence": "past",
            "score": 0,
            "data_quality": data_quality,
            "data_quality_label": "Yetarli dalil yo'q",
            "evidence": [message],
            "alternatives": [],
            "disclaimer": (
                "Telegram user nega block qilganini bermaydi. Dalil yetarli bo'lmasa tizim taxminni "
                "fakt sifatida ko'rsatmaydi."
            ),
        }
