from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from html import escape
from typing import Optional

from aiogram import Bot
from sqlalchemy import func, select

from app.bot.utils.i18n import t
from app.config import settings
from app.db.models.partner import Partner, PartnerCredit, PartnerPayout, PartnerReferral
from app.db.models.user import User
from app.repositories.bot_setting_repo import BotSettingRepository
from app.repositories.partner_repo import PartnerRepository
from app.repositories.user_repo import UserRepository
from app.services.portfolio_service import PortfolioService


PARTNER_LINK_PREFIX = "partner_"
PARTNER_USDT_TJS_RATE_KEY = "partner_usd_rate"
PARTNER_COMMISSION_MODE_KEY = "partner_commission_mode"
PARTNER_COMMISSION_PERCENT_KEY = "partner_commission_percent"
PARTNER_COMMISSION_USD_KEY = "partner_commission_usd"
PARTNER_SIGNUP_BONUS_USD_KEY = "partner_signup_bonus_usd"
PARTNER_MIN_PAYOUT_USD_KEY = "partner_min_payout_usd"
DEFAULT_PARTNER_USDT_TJS_RATE = Decimal("10.90")
DEFAULT_PARTNER_COMMISSION_MODE = "percent"
DEFAULT_PARTNER_COMMISSION_PERCENT = Decimal("20.00")
DEFAULT_PARTNER_COMMISSION_USD = Decimal("1.00")
DEFAULT_PARTNER_SIGNUP_BONUS_USD = Decimal("1.00")
DEFAULT_PARTNER_MIN_PAYOUT_USD = Decimal("5.00")
OPEN_PAYOUT_STATUSES = ("pending", "deadline_set")


@dataclass(frozen=True)
class PartnerBalance:
    balance_usd: Decimal
    in_progress_usd: Decimal
    withdrawn_usd: Decimal
    referrals: int
    paid_referrals: int


class PartnerService:
    def __init__(self, session):
        self.session = session
        self.repo = PartnerRepository(session)
        self.user_repo = UserRepository(session)
        self.setting_repo = BotSettingRepository(session)

    def _money(self, value) -> Decimal:
        return Decimal(value or 0).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _compact_decimal(self, value: Decimal) -> str:
        return format(value.normalize(), "f")

    async def _get_decimal_setting(self, key: str, default: Decimal, *, allow_zero: bool = False) -> Decimal:
        raw_value = await self.setting_repo.get(key)
        if raw_value is None:
            return default
        try:
            value = Decimal(raw_value)
        except (InvalidOperation, TypeError):
            return default
        if value > 0 or (allow_zero and value == 0):
            return value
        return default

    async def get_usdt_tjs_rate(self) -> Decimal:
        return await self._get_decimal_setting(PARTNER_USDT_TJS_RATE_KEY, DEFAULT_PARTNER_USDT_TJS_RATE)

    async def set_usdt_tjs_rate(self, value: Decimal) -> None:
        await self.setting_repo.set(PARTNER_USDT_TJS_RATE_KEY, str(value.quantize(Decimal("0.0001"))))

    async def get_commission_mode(self) -> str:
        value = await self.setting_repo.get(PARTNER_COMMISSION_MODE_KEY)
        return value if value in {"percent", "fixed"} else DEFAULT_PARTNER_COMMISSION_MODE

    async def set_commission_mode(self, value: str) -> None:
        if value not in {"percent", "fixed"}:
            raise ValueError("Unsupported partner commission mode")
        await self.setting_repo.set(PARTNER_COMMISSION_MODE_KEY, value)

    async def get_commission_percent(self) -> Decimal:
        return self._money(
            await self._get_decimal_setting(
                PARTNER_COMMISSION_PERCENT_KEY,
                DEFAULT_PARTNER_COMMISSION_PERCENT,
                allow_zero=True,
            )
        )

    async def set_commission_percent(self, value: Decimal) -> None:
        await self.setting_repo.set(PARTNER_COMMISSION_PERCENT_KEY, str(self._money(value)))

    async def get_commission_usd(self) -> Decimal:
        return self._money(
            await self._get_decimal_setting(
                PARTNER_COMMISSION_USD_KEY,
                DEFAULT_PARTNER_COMMISSION_USD,
                allow_zero=True,
            )
        )

    async def set_commission_usd(self, value: Decimal) -> None:
        await self.setting_repo.set(PARTNER_COMMISSION_USD_KEY, str(self._money(value)))

    async def get_signup_bonus_usd(self) -> Decimal:
        return self._money(
            await self._get_decimal_setting(
                PARTNER_SIGNUP_BONUS_USD_KEY,
                DEFAULT_PARTNER_SIGNUP_BONUS_USD,
                allow_zero=True,
            )
        )

    async def set_signup_bonus_usd(self, value: Decimal) -> None:
        await self.setting_repo.set(PARTNER_SIGNUP_BONUS_USD_KEY, str(self._money(value)))

    async def get_min_payout_usd(self) -> Decimal:
        return self._money(
            await self._get_decimal_setting(PARTNER_MIN_PAYOUT_USD_KEY, DEFAULT_PARTNER_MIN_PAYOUT_USD)
        )

    async def set_min_payout_usd(self, value: Decimal) -> None:
        await self.setting_repo.set(PARTNER_MIN_PAYOUT_USD_KEY, str(self._money(value)))

    async def get_commission_offer(self) -> str:
        if await self.get_commission_mode() == "fixed":
            return f"${await self.get_commission_usd():.2f}"
        return f"{self._compact_decimal(await self.get_commission_percent())}%"

    async def calculate_commission_usd(self, payment) -> Decimal:
        if await self.get_commission_mode() == "fixed":
            return await self.get_commission_usd()
        currency_key = (payment.currency or "").strip().lower()
        if currency_key in {"somoni", "tjs", "сомони"}:
            revenue_usd = Decimal(str(payment.amount)) / await self.get_usdt_tjs_rate()
        else:
            converted = PortfolioService(None).amount_to_usd(payment.amount, payment.currency)
            revenue_usd = Decimal(str(converted)) if converted is not None else None
        if revenue_usd is None:
            return Decimal("0.00")
        percent = await self.get_commission_percent()
        return self._money(revenue_usd * percent / Decimal("100"))

    async def submit_application(
        self,
        *,
        telegram_id: int,
        promotion_channel: str,
        audience_size: str,
        contact_username: str,
    ) -> Partner:
        return await self.repo.submit_application(
            telegram_id=telegram_id,
            promotion_channel=promotion_channel,
            audience_size=audience_size,
            contact_username=contact_username,
        )

    async def approve(self, partner: Partner, admin_telegram_id: int) -> None:
        await self.repo.set_status(partner, "active", admin_telegram_id)
        if not await self.repo.get_signup_bonus(partner.id):
            bonus = await self.get_signup_bonus_usd()
            if bonus > 0:
                await self.repo.add_credit(
                    partner_id=partner.id,
                    credit_type="signup_bonus",
                    amount_usd=bonus,
                    is_locked=True,
                )

    async def block(self, partner: Partner, admin_telegram_id: int) -> None:
        await self.repo.set_status(partner, "blocked", admin_telegram_id)

    async def unblock(self, partner: Partner, admin_telegram_id: int) -> None:
        await self.repo.set_status(partner, "active", admin_telegram_id)

    async def build_partner_link(self, partner: Partner) -> Optional[str]:
        user = await self.user_repo.get_by_telegram_id(partner.user_telegram_id)
        if not user:
            return None
        await self.user_repo.ensure_referral_code(user)
        return f"https://t.me/{settings.BOT_USERNAME}?start={PARTNER_LINK_PREFIX}{user.referral_code}"

    async def attach_referral_if_needed(self, invited_user_telegram_id: int, referral_code: Optional[str]) -> None:
        if not referral_code or not referral_code.startswith(PARTNER_LINK_PREFIX):
            return
        code = referral_code[len(PARTNER_LINK_PREFIX):]
        if not code:
            return
        referrer_user = await self.user_repo.get_by_referral_code(code)
        if not referrer_user or referrer_user.telegram_id == invited_user_telegram_id:
            return
        partner = await self.repo.get_by_telegram_id(referrer_user.telegram_id)
        if not partner or partner.status != "active":
            return
        if await self.repo.get_referral_by_invited_user(invited_user_telegram_id):
            return
        await self.repo.create_referral(partner.id, invited_user_telegram_id)
        await self.session.flush()

    async def record_approved_payment(self, payment) -> tuple[Optional[Partner], Decimal, bool]:
        if not payment or payment.payment_status != "approved":
            return None, Decimal("0.00"), False
        if await self.repo.get_credit_by_payment(payment.id):
            return None, Decimal("0.00"), False
        referral = await self.repo.get_referral_by_invited_user(payment.user_telegram_id)
        if not referral:
            return None, Decimal("0.00"), False
        partner = await self.repo.get_by_id(referral.partner_id)
        if not partner or partner.status != "active":
            return None, Decimal("0.00"), False

        commission = await self.calculate_commission_usd(payment)
        await self.repo.add_credit(
            partner_id=partner.id,
            credit_type="paid_referral_commission",
            amount_usd=commission,
            payment_id=payment.id,
        )
        if not referral.first_paid_at:
            referral.first_paid_at = payment.reviewed_at or datetime.now(timezone.utc)
        unlocked_bonus = await self.repo.unlock_signup_bonus(partner.id)
        await self.session.flush()
        return partner, commission, unlocked_bonus

    async def get_balance(self, partner: Partner) -> PartnerBalance:
        credits = await self.repo.sum_unlocked_credits(partner.id)
        in_progress = await self.repo.sum_payouts(partner.id, OPEN_PAYOUT_STATUSES)
        withdrawn = await self.repo.sum_payouts(partner.id, ("paid",))
        return PartnerBalance(
            balance_usd=self._money(credits - in_progress - withdrawn),
            in_progress_usd=self._money(in_progress),
            withdrawn_usd=self._money(withdrawn),
            referrals=await self.repo.count_referrals(partner.id),
            paid_referrals=await self.repo.count_paid_referrals(partner.id),
        )

    async def create_payout_request(
        self,
        *,
        partner: Partner,
        payment_method: str,
        bank_name: Optional[str],
        account_details: str,
        holder_name: Optional[str],
        note: Optional[str],
    ) -> Optional[PartnerPayout]:
        balance = await self.get_balance(partner)
        if balance.balance_usd < await self.get_min_payout_usd():
            return None
        rate = await self.get_usdt_tjs_rate()
        local_amount = (balance.balance_usd * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return await self.repo.create_payout(
            partner_id=partner.id,
            amount_usd=balance.balance_usd,
            exchange_rate=rate,
            local_amount=local_amount,
            payment_method=payment_method,
            bank_name=bank_name,
            account_details=account_details,
            holder_name=holder_name,
            note=note,
        )

    async def notify_application(self, bot: Bot, partner: Partner) -> None:
        from app.bot.handlers.admin_partner import admin_partner_detail_keyboard

        text = (
            "🤝 <b>Yangi hamkorlik arizasi</b>\n\n"
            f"Telegram ID: <code>{partner.user_telegram_id}</code>\n"
            f"Reklama joyi: {escape(partner.promotion_channel)}\n"
            f"Auditoriya: {escape(partner.audience_size)}\n"
            f"Aloqa: {escape(partner.contact_username)}"
        )
        for admin_id in settings.admin_id_list:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=text,
                    reply_markup=admin_partner_detail_keyboard(partner),
                )
            except Exception:
                pass

    async def notify_payout_request(self, bot: Bot, payout: PartnerPayout) -> None:
        from app.bot.handlers.admin_partner import admin_payout_keyboard

        text = await self.build_admin_payout_text(payout)
        for admin_id in settings.admin_id_list:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=text,
                    reply_markup=admin_payout_keyboard(payout.id),
                )
            except Exception:
                pass

    async def build_admin_payout_text(self, payout: PartnerPayout) -> str:
        partner = await self.repo.get_by_id(payout.partner_id)
        user = await self.user_repo.get_by_telegram_id(partner.user_telegram_id) if partner else None
        balance = await self.get_balance(partner) if partner else None
        username = f"@{escape(user.username)}" if user and user.username else "—"
        return (
            "💸 <b>Hamkor pul yechish so'rovi</b>\n\n"
            f"Hamkor: <b>{username}</b>\n"
            f"Telegram ID: <code>{partner.user_telegram_id if partner else '—'}</code>\n"
            f"So'ralgan summa: <b>${payout.amount_usd:.2f}</b>\n"
            f"Kurs: <code>1 USDT = {payout.exchange_rate:.4f} TJS</code>\n"
            f"To'lanadi: <b>{payout.local_amount:.2f} somoni</b>\n\n"
            f"Balans: <b>${balance.balance_usd:.2f}</b>\n"
            f"Jarayonda: <b>${balance.in_progress_usd:.2f}</b>\n"
            f"Yechilgan jami: <b>${balance.withdrawn_usd:.2f}</b>\n"
            f"Kelganlar: <b>{balance.referrals}</b>\n"
            f"To'lov qilganlar: <b>{balance.paid_referrals}</b>\n\n"
            f"To'lov turi: <b>{escape(payout.payment_method)}</b>\n"
            f"Bank: <b>{escape(payout.bank_name or '—')}</b>\n"
            f"Rekvizit: <code>{escape(payout.account_details)}</code>\n"
            f"Ism: <b>{escape(payout.holder_name or '—')}</b>\n"
            f"Izoh: {escape(payout.note or '—')}"
        )

    async def send_due_payout_reminders(self, bot: Bot) -> None:
        for payout in await self.repo.list_due_payout_reminders():
            for admin_id in settings.admin_id_list:
                try:
                    await bot.send_message(
                        chat_id=admin_id,
                        text=f"⏰ Hamkor payout #{payout.id} muddati keldi.\n\n{await self.build_admin_payout_text(payout)}",
                    )
                except Exception:
                    pass
            await self.repo.mark_reminder_sent(payout)
        await self.session.commit()

    async def notify_partner(self, bot: Bot, partner: Partner, key: str, **kwargs) -> None:
        user = await self.user_repo.get_by_telegram_id(partner.user_telegram_id)
        if not user:
            return
        lang = user.language or "ru"
        include_bonus_line = kwargs.pop("include_bonus_line", False)
        if key == "partner_commission_notification":
            signup_bonus = await self.repo.get_signup_bonus(partner.id) if include_bonus_line else None
            kwargs["bonus_line"] = (
                t("partner_bonus_unlocked_line", lang, bonus=f"${signup_bonus.amount_usd:.2f}")
                if signup_bonus
                else ""
            )
        try:
            await bot.send_message(
                chat_id=user.telegram_id,
                text=t(key, lang, **kwargs),
            )
        except Exception:
            pass

    async def overall_stats(self) -> dict[str, object]:
        partner_counts = {
            row.status: row.count
            for row in (
                await self.session.execute(
                    select(Partner.status, func.count().label("count")).group_by(Partner.status)
                )
            ).all()
        }
        total_referrals = (
            await self.session.execute(select(func.count()).select_from(PartnerReferral))
        ).scalar() or 0
        paid_referrals = (
            await self.session.execute(
                select(func.count()).select_from(PartnerReferral).where(PartnerReferral.first_paid_at.is_not(None))
            )
        ).scalar() or 0
        question_users = (
            await self.session.execute(
                select(func.count())
                .select_from(PartnerReferral)
                .join(User, User.telegram_id == PartnerReferral.invited_user_telegram_id)
                .where(User.questions_used > 0)
            )
        ).scalar() or 0
        course_users = (
            await self.session.execute(
                select(func.count())
                .select_from(PartnerReferral)
                .join(User, User.telegram_id == PartnerReferral.invited_user_telegram_id)
                .where(User.learning_mode == "course")
            )
        ).scalar() or 0
        trial_users = (
            await self.session.execute(
                select(func.count())
                .select_from(PartnerReferral)
                .join(User, User.telegram_id == PartnerReferral.invited_user_telegram_id)
                .where(User.payment_status != "approved")
            )
        ).scalar() or 0
        credited_usd = (
            await self.session.execute(select(func.sum(PartnerCredit.amount_usd)))
        ).scalar() or 0
        reserved_usd = (
            await self.session.execute(
                select(func.sum(PartnerPayout.amount_usd)).where(PartnerPayout.status.in_(OPEN_PAYOUT_STATUSES))
            )
        ).scalar() or 0
        withdrawn_usd = (
            await self.session.execute(
                select(func.sum(PartnerPayout.amount_usd)).where(PartnerPayout.status == "paid")
            )
        ).scalar() or 0
        return {
            "pending": int(partner_counts.get("pending", 0)),
            "active": int(partner_counts.get("active", 0)),
            "blocked": int(partner_counts.get("blocked", 0)),
            "referrals": int(total_referrals),
            "paid_referrals": int(paid_referrals),
            "question_users": int(question_users),
            "course_users": int(course_users),
            "trial_users": int(trial_users),
            "credited_usd": self._money(credited_usd),
            "reserved_usd": self._money(reserved_usd),
            "withdrawn_usd": self._money(withdrawn_usd),
        }
