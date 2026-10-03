from datetime import datetime, timezone, timedelta, date
from typing import Optional
import secrets

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_by_telegram_id_for_update(self, telegram_id: int) -> Optional[User]:
        result = await self.session.execute(
            select(User)
            .where(User.telegram_id == telegram_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def find_by_identifier(self, identifier: str) -> Optional[User]:
        value = (identifier or "").strip()
        if not value:
            return None
        if value.startswith("@"):
            value = value[1:]
        if value.isdigit():
            return await self.get_by_telegram_id(int(value))

        result = await self.session.execute(
            select(User).where(func.lower(User.username) == value.lower())
        )
        return result.scalar_one_or_none()

    async def search_by_identifier(self, identifier: str, limit: int = 10) -> list[User]:
        value = (identifier or "").strip()
        if not value:
            return []
        if value.startswith("@"):
            value = value[1:]
        if value.isdigit():
            user = await self.get_by_telegram_id(int(value))
            return [user] if user else []

        pattern = f"%{value.lower()}%"
        result = await self.session.execute(
            select(User)
            .where(
                (func.lower(User.username).like(pattern))
                | (func.lower(User.full_name).like(pattern))
            )
            .order_by(User.last_active_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_referral_code(self, referral_code: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.referral_code == referral_code)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        telegram_id: int,
        full_name: Optional[str] = None,
        username: Optional[str] = None,
        language: str = "tj",
        level: str = "beginner",
        learning_mode: str = "qa",
    ) -> User:
        now = datetime.now(timezone.utc)

        user = User(
            telegram_id=telegram_id,
            full_name=full_name,
            username=username,
            language=language,
            level=level,
            learning_mode=learning_mode,
            voice_mode="none",
            status="trial",
            payment_status="none",
            question_limit=5,
            questions_used=0,
            bonus_questions=0,
            bonus_questions_used=0,
            referral_code=self._generate_referral_code(),
            start_date=None,
            end_date=None,
            discount_referral_count=0,
            discount_eligible=False,
            discount_used=False,
            referral_trial_count_started_at=now,
            created_at=now,
            last_active_at=now,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def update_last_active(self, user: User) -> None:
        user.last_active_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def set_voice_mode(self, user: User, mode: str) -> None:
        user.voice_mode = mode
        await self.session.flush()

    async def set_subscription_currency(self, user: User, currency: str) -> None:
        user.subscription_currency = currency
        await self.session.flush()

    async def set_referred_by(
        self,
        user: User,
        referrer_telegram_id: int,
    ) -> None:
        # already set → skip
        if user.referrer_id:
            return

        user.referred_by_telegram_id = referrer_telegram_id

        referrer = await self.get_by_telegram_id(referrer_telegram_id)
        if referrer:
            user.referrer_id = referrer.id

        await self.session.flush()

    async def add_bonus_questions(
        self,
        user: User,
        amount: int,
    ) -> None:
        user.bonus_questions += amount
        await self.session.flush()

    async def consume_bonus_question(
        self,
        user: User,
    ) -> None:
        user.bonus_questions_used += 1
        await self.session.flush()

    def get_bonus_balance(self, user: User) -> int:
        return max(user.bonus_questions - user.bonus_questions_used, 0)

    async def start_discount_offer(
        self,
        user: User,
    ) -> None:
        user.discount_offer_started_at = datetime.now(timezone.utc)
        user.discount_referral_count = 0
        user.discount_eligible = False
        await self.session.flush()

    async def increment_discount_referral_count(
        self,
        user: User,
        amount: int = 1,
    ) -> None:
        user.discount_referral_count += amount
        if user.discount_referral_count >= 3 and not user.discount_used:
            user.discount_eligible = True
        await self.session.flush()

    async def mark_discount_used(
        self,
        user: User,
    ) -> None:
        user.discount_used = True
        user.discount_eligible = False
        await self.session.flush()

    async def ensure_referral_code(self, user: User) -> None:
        if user.referral_code:
            return

        user.referral_code = self._generate_referral_code()
        await self.session.flush()

    async def set_referral_trial_progress_message(
        self,
        user: User,
        chat_id: int,
        message_id: int,
    ) -> None:
        user.referral_trial_progress_chat_id = chat_id
        user.referral_trial_progress_message_id = message_id
        await self.session.flush()

    async def clear_referral_trial_progress_message(self, user: User) -> None:
        user.referral_trial_progress_chat_id = None
        user.referral_trial_progress_message_id = None
        await self.session.flush()

    async def was_daily_limit_offer_sent_today(self, user: User) -> bool:
        if not user.daily_limit_offer_sent_at:
            return False

        return user.daily_limit_offer_sent_at.date() == datetime.now(timezone.utc).date()

    async def mark_daily_limit_offer_sent(self, user: User) -> None:
        user.daily_limit_offer_sent_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def set_discount_progress_message(
        self,
        user: User,
        chat_id: int,
        message_id: int,
    ) -> None:
        user.discount_progress_chat_id = chat_id
        user.discount_progress_message_id = message_id
        await self.session.flush()

    async def clear_discount_progress_message(
        self,
        user: User,
    ) -> None:
        user.discount_progress_chat_id = None
        user.discount_progress_message_id = None
        await self.session.flush()

    async def set_selected_plan_type(
        self,
        user: User,
        plan_type: Optional[str],
    ) -> None:
        user.selected_plan_type = plan_type
        await self.session.flush()

    async def set_pending_checkout_msg_id(
        self,
        user: User,
        msg_id: Optional[int],
    ) -> None:
        user.pending_checkout_msg_id = msg_id
        await self.session.flush()

    async def get_all_users(self) -> list[User]:
        result = await self.session.execute(select(User))
        return list(result.scalars().all())

    async def get_filtered_users(
        self,
        language: Optional[str] = None,
        languages: Optional[list[str]] = None,
        status: Optional[str] = None,
        course_track: Optional[str] = None,
        level: Optional[str] = None,
        learning_mode: Optional[str] = None,
        payment_status: Optional[str] = None,
        payment_method: Optional[str] = None,
        selected_plan_type: Optional[str] = None,
        discount_filter: Optional[str] = None,
        course_promo_filter: Optional[str] = None,
        activity_filter: Optional[str] = None,
    ) -> list[User]:
        query = select(User)
        if languages:
            query = query.where(User.language.in_(languages))
        elif language:
            query = query.where(User.language == language)
        if status:
            query = query.where(User.status == status)
        if course_track == "hsk30":
            query = query.where(User.level.like("nhsk%"))
        elif course_track == "hsk20":
            query = query.where(
                or_(
                    User.level.is_(None),
                    ~User.level.like("nhsk%"),
                )
            )
        if level:
            query = query.where(User.level == level)
        if learning_mode:
            query = query.where(User.learning_mode == learning_mode)
        if payment_status:
            query = query.where(User.payment_status == payment_status)
        if payment_method:
            query = query.where(User.payment_method == payment_method)
        if selected_plan_type:
            query = query.where(User.selected_plan_type == selected_plan_type)
        if discount_filter == "eligible":
            query = query.where(User.discount_eligible.is_(True))
        elif discount_filter == "used":
            query = query.where(User.discount_used.is_(True))
        elif discount_filter == "none":
            query = query.where(User.discount_eligible.is_(False), User.discount_used.is_(False))
        if course_promo_filter == "sent":
            query = query.where(User.course_promo_sent.is_(True))
        elif course_promo_filter == "not_sent":
            query = query.where(User.course_promo_sent.is_(False))
        if activity_filter:
            now = datetime.now(timezone.utc)
            since_7d = now - timedelta(days=7)
            if activity_filter == "active_7d":
                query = query.where(User.last_active_at >= since_7d)
            elif activity_filter == "inactive_7d":
                query = query.where(User.last_active_at < since_7d)
            elif activity_filter == "new_7d":
                query = query.where(User.created_at >= since_7d)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_ad_target_users(
        self,
        *,
        languages: Optional[list[str]] = None,
        course_track: Optional[str] = None,
        level: Optional[str] = None,
        include_active_subscribers: bool = False,
    ) -> list[User]:
        query = select(User).where(User.status != "blocked")
        if languages:
            query = query.where(User.language.in_(languages))
        if course_track == "hsk30":
            query = query.where(User.level.like("nhsk%"))
        elif course_track == "hsk20":
            query = query.where(
                or_(
                    User.level.is_(None),
                    ~User.level.like("nhsk%"),
                )
            )
        if level:
            query = query.where(User.level == level)
        if not include_active_subscribers:
            query = query.where(User.status != "active")
        result = await self.session.execute(query.order_by(User.id.asc()))
        return list(result.scalars().all())

    async def list_active_users_expiring_on(
        self,
        target_date: date,
    ) -> list[User]:
        result = await self.session.execute(
            select(User).where(
                User.status == "active",
                User.payment_status == "approved",
            )
        )
        users = list(result.scalars().all())
        return [
            user for user in users
            if user.end_date and user.end_date.date() == target_date
        ]

    async def delete_by_telegram_id(self, telegram_id: int) -> bool:
        """Foydalanuvchi accountini tizimda yetim iz qoldirmasdan o'chiradi.

        Accountga tegishli progress, sessiya, identity, notification, analytics,
        referral va AI holatlari to'liq tozalanadi. Kompaniyaning umumiy moliyaviy
        ledgeri esa tarixiy hisobot buzilmasligi uchun saqlanadi, lekin o'chirilgan
        user/payment bilan bog'lovchi identifikatorlar undan uziladi.

        Barcha amallar caller ochgan BITTA DB transaction ichida bajariladi.
        """
        from sqlalchemy import delete as sql_delete, update as sql_update

        from app.db.models.account_notice_delivery import AccountNoticeDelivery
        from app.db.models.ad_campaign import AdCampaignDelivery
        from app.db.models.ai_usage import AIUsageBudget, AIUsageEvent
        from app.db.models.android_push import AndroidPushToken
        from app.db.models.assistant import (
            AssistantAssessment,
            AssistantConversation,
            AssistantRequest,
        )
        from app.db.models.bot_feedback import BotFeedback
        from app.db.models.bot_outbound_event import BotOutboundEvent
        from app.db.models.bot_reachability_event import BotReachabilityEvent
        from app.db.models.conversion_funnel_event import ConversionFunnelEvent
        from app.db.models.course_ad import CourseAdView
        from app.db.models.course_attempts import CourseAttempt
        from app.db.models.course_challenge import CourseChallenge
        from app.db.models.course_feature_usage import CourseFeatureUsage
        from app.db.models.course_miniapp_event import CourseMiniAppEvent
        from app.db.models.course_miniapp_profile import CourseMiniAppProfile
        from app.db.models.course_mistake import CourseMistake
        from app.db.models.course_mistake_target import CourseMistakeTarget
        from app.db.models.course_pilot_event import CoursePilotEvent
        from app.db.models.course_progress import CourseProgress
        from app.db.models.course_track_state import CourseTrackState
        from app.db.models.course_user_notification import CourseUserNotification
        from app.db.models.course_word_mastery import CourseWordMastery
        from app.db.models.course_xp_event import CourseXpEvent
        from app.db.models.desktop import DesktopDevice, DesktopLinkRequest, DesktopSession
        from app.db.models.entitlement_shadow_event import EntitlementShadowEvent
        from app.db.models.message import Message
        from app.db.models.onboarding_tip_event import OnboardingTipEvent
        from app.db.models.partner import Partner, PartnerReferral
        from app.db.models.payment import Payment
        from app.db.models.portfolio import PortfolioTransaction
        from app.db.models.referral import Referral
        from app.db.models.release_feedback import (
            ReleaseFeedbackDelivery,
            ReleaseFeedbackResponse,
        )
        from app.db.models.subscription_entry_event import SubscriptionEntryEvent
        from app.db.models.trial_risk_event import TrialRiskEvent
        from app.db.models.user_client_presence import AppPromoState, UserClientPresence
        from app.db.models.user_identity import UserIdentity
        from app.db.models.voice_practice_session import VoicePracticeSession

        # Row lock bir vaqtda payment/auth/event yozilishi bilan delete poygasini
        # kamaytiradi. Commit/rollbackni caller boshqaradi.
        user = await self.get_by_telegram_id_for_update(telegram_id)
        if not user:
            return False

        uid = int(user.id)

        # O'chirilayotgan user boshqa accountlarda referrer bo'lib qolmasin.
        # Bu ustunlar tarixan FK emas, shuning uchun DB CASCADE yordam bermaydi.
        await self.session.execute(
            sql_update(User)
            .where(User.referrer_id == uid)
            .values(referrer_id=None)
        )
        await self.session.execute(
            sql_update(User)
            .where(User.referred_by_telegram_id == telegram_id)
            .values(referred_by_telegram_id=None)
        )

        # Tasdiqlangan to'lovlar kompaniyaning accounting/business tarixi.
        # Ularni fizik o'chirsak finance stats kamayadi va PortfolioService keyingi
        # sync'da subscription_profit rowlarini ham stale deb o'chiradi. Shuning
        # uchun account identifikatori hamda Telegram message/screenshot izlari
        # uziladi, ammo anonim moliyaviy fakt saqlanadi.
        #
        # Manfiy users.id real Telegram user ID bo'la olmaydi va har bir o'chirilgan
        # account uchun unique bo'ladi.
        anonymous_telegram_id = -uid
        approved_payment_ids = select(Payment.id).where(
            Payment.user_telegram_id == telegram_id,
            Payment.payment_status == "approved",
        )
        await self.session.execute(
            sql_update(PortfolioTransaction)
            .where(
                or_(
                    PortfolioTransaction.user_telegram_id == telegram_id,
                    PortfolioTransaction.payment_id.in_(approved_payment_ids),
                )
            )
            .values(user_telegram_id=anonymous_telegram_id)
        )
        await self.session.execute(
            sql_update(Payment)
            .where(
                Payment.user_telegram_id == telegram_id,
                Payment.payment_status == "approved",
            )
            .values(
                user_telegram_id=anonymous_telegram_id,
                screenshot_file_id=None,
                admin_comment=None,
                checkout_msg_id=None,
                screenshot_msg_id=None,
                waiting_msg_id=None,
            )
        )
        # Draft/pending/rejected payment account state; accountingga kirmaydi.
        await self.session.execute(
            sql_delete(Payment).where(
                Payment.user_telegram_id == telegram_id,
                Payment.payment_status != "approved",
            )
        )

        # Partner ledgeri (credit/payout) system-level moliyaviy tarix. Uni
        # kaskad bilan yo'qotmasdan user identifikatorini anonim sentinelga
        # almashtiramiz.
        await self.session.execute(
            sql_update(PartnerReferral)
            .where(PartnerReferral.invited_user_telegram_id == telegram_id)
            .values(invited_user_telegram_id=anonymous_telegram_id)
        )
        await self.session.execute(
            sql_update(Partner)
            .where(Partner.user_telegram_id == telegram_id)
            .values(
                user_telegram_id=anonymous_telegram_id,
                status="blocked",
                promotion_channel="[deleted]",
                audience_size="[deleted]",
                contact_username="[deleted]",
            )
        )

        # Native/desktop auth zanjiri. SQLite test muhitida ham FK CASCADEga
        # suyanib qolmaslik uchun child rowlar aniq tartibda o'chiriladi.
        device_ids = select(DesktopDevice.id).where(
            or_(
                DesktopDevice.user_id == uid,
                DesktopDevice.telegram_id == telegram_id,
            )
        )
        await self.session.execute(
            sql_delete(AndroidPushToken).where(AndroidPushToken.device_id.in_(device_ids))
        )
        await self.session.execute(
            sql_delete(DesktopSession).where(DesktopSession.device_id.in_(device_ids))
        )
        await self.session.execute(
            sql_delete(DesktopDevice).where(
                or_(
                    DesktopDevice.user_id == uid,
                    DesktopDevice.telegram_id == telegram_id,
                )
            )
        )
        await self.session.execute(
            sql_delete(DesktopLinkRequest).where(
                or_(
                    DesktopLinkRequest.bind_user_id == uid,
                    DesktopLinkRequest.approved_user_id == uid,
                    DesktopLinkRequest.approved_telegram_id == telegram_id,
                )
            )
        )

        # Assistant child rowlari conversationdan oldin tozalanadi.
        await self.session.execute(
            sql_delete(AssistantRequest).where(AssistantRequest.user_id == uid)
        )
        await self.session.execute(
            sql_delete(AssistantAssessment).where(AssistantAssessment.user_id == uid)
        )
        await self.session.execute(
            sql_delete(AssistantConversation).where(AssistantConversation.user_id == uid)
        )

        # Faqat users.id bilan bog'langan account state.
        by_user_id = [
            (OnboardingTipEvent, OnboardingTipEvent.user_id),
            (CourseAttempt, CourseAttempt.user_id),
            (CourseProgress, CourseProgress.user_id),
            (CourseFeatureUsage, CourseFeatureUsage.user_id),
            (CourseMiniAppProfile, CourseMiniAppProfile.user_id),
            (CourseMistake, CourseMistake.user_id),
            (CourseMistakeTarget, CourseMistakeTarget.user_id),
            (CourseTrackState, CourseTrackState.user_id),
            (CourseWordMastery, CourseWordMastery.user_id),
            (CourseXpEvent, CourseXpEvent.user_id),
            (Message, Message.user_id),
            (UserIdentity, UserIdentity.user_id),
            (UserClientPresence, UserClientPresence.user_id),
            (AppPromoState, AppPromoState.user_id),
        ]
        for model, column in by_user_id:
            await self.session.execute(sql_delete(model).where(column == uid))

        # Faqat Telegram ID bilan bog'langan account state.
        by_telegram_id = [
            (AIUsageBudget, AIUsageBudget.user_telegram_id),
            (AIUsageEvent, AIUsageEvent.user_telegram_id),
            (VoicePracticeSession, VoicePracticeSession.user_telegram_id),
            (ReleaseFeedbackDelivery, ReleaseFeedbackDelivery.user_telegram_id),
            (ReleaseFeedbackResponse, ReleaseFeedbackResponse.user_telegram_id),
            (AdCampaignDelivery, AdCampaignDelivery.user_telegram_id),
            (EntitlementShadowEvent, EntitlementShadowEvent.telegram_id),
        ]
        for model, column in by_telegram_id:
            await self.session.execute(
                sql_delete(model).where(column == telegram_id)
            )

        # user_id SET NULL bo'lishi mumkin bo'lgan yoki legacy rowlarda user_id
        # yo'q bo'lib, Telegram ID saqlanib qolishi mumkin bo'lgan jadvallar.
        await self.session.execute(
            sql_delete(AccountNoticeDelivery).where(
                or_(
                    AccountNoticeDelivery.user_id == uid,
                    AccountNoticeDelivery.telegram_id == telegram_id,
                )
            )
        )
        await self.session.execute(
            sql_delete(BotOutboundEvent).where(
                or_(
                    BotOutboundEvent.user_id == uid,
                    BotOutboundEvent.telegram_id == telegram_id,
                )
            )
        )
        await self.session.execute(
            sql_delete(BotReachabilityEvent).where(
                or_(
                    BotReachabilityEvent.user_id == uid,
                    BotReachabilityEvent.telegram_id == telegram_id,
                )
            )
        )
        await self.session.execute(
            sql_delete(ConversionFunnelEvent).where(
                or_(
                    ConversionFunnelEvent.user_id == uid,
                    ConversionFunnelEvent.telegram_id == telegram_id,
                )
            )
        )
        await self.session.execute(
            sql_delete(CourseMiniAppEvent).where(
                or_(
                    CourseMiniAppEvent.user_id == uid,
                    CourseMiniAppEvent.telegram_id == telegram_id,
                )
            )
        )
        await self.session.execute(
            sql_delete(CoursePilotEvent).where(
                or_(
                    CoursePilotEvent.user_id == uid,
                    CoursePilotEvent.telegram_id == telegram_id,
                )
            )
        )
        await self.session.execute(
            sql_delete(CourseUserNotification).where(
                or_(
                    CourseUserNotification.user_id == uid,
                    CourseUserNotification.telegram_id == telegram_id,
                )
            )
        )
        await self.session.execute(
            sql_delete(SubscriptionEntryEvent).where(
                or_(
                    SubscriptionEntryEvent.user_id == uid,
                    SubscriptionEntryEvent.telegram_id == telegram_id,
                )
            )
        )
        await self.session.execute(
            sql_delete(TrialRiskEvent).where(
                or_(
                    TrialRiskEvent.user_id == uid,
                    TrialRiskEvent.telegram_id == telegram_id,
                )
            )
        )
        await self.session.execute(
            sql_delete(BotFeedback).where(
                or_(
                    BotFeedback.user_id == uid,
                    BotFeedback.telegram_id == telegram_id,
                )
            )
        )
        await self.session.execute(
            sql_delete(CourseAdView).where(
                or_(
                    CourseAdView.user_id == uid,
                    CourseAdView.user_telegram_id == telegram_id,
                )
            )
        )

        # Shared challenge: user participant bo'lsa challenge ham account datasi.
        # Faqat winner sifatida turgan boshqa userlarning challenge'i saqlanadi.
        await self.session.execute(
            sql_update(CourseChallenge)
            .where(CourseChallenge.winner_user_id == uid)
            .values(winner_user_id=None)
        )
        await self.session.execute(
            sql_delete(CourseChallenge).where(
                or_(
                    CourseChallenge.challenger_user_id == uid,
                    CourseChallenge.opponent_user_id == uid,
                )
            )
        )

        # Referral rowning ikki tomoni ham o'chirilayotgan userga tegishli iz.
        await self.session.execute(
            sql_delete(Referral).where(
                or_(
                    Referral.referrer_telegram_id == telegram_id,
                    Referral.invited_user_telegram_id == telegram_id,
                )
            )
        )

        await self.session.delete(user)
        await self.session.flush()
        return True

    async def set_blocked(self, telegram_id: int, blocked: bool) -> Optional[User]:
        """Foydalanuvchini admin tomonidan bloklaydi yoki blokdan chiqaradi.

        Blokdan chiqarilganda holat obuna muddatiga qarab tiklanadi:
        muddati o'tmagan tasdiqlangan obuna bo'lsa "active", aks holda "free".
        """
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return None
        if blocked:
            user.status = "blocked"
        else:
            now = datetime.now(timezone.utc)
            end_date = user.end_date
            if end_date is not None and end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)
            is_active_sub = (
                user.payment_status == "approved"
                and end_date is not None
                and end_date > now
            )
            user.status = "active" if is_active_sub else "free"
        await self.session.flush()
        return user

    def _generate_referral_code(self) -> str:
        return secrets.token_hex(4)
