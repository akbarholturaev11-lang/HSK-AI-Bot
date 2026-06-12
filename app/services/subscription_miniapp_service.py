from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aiogram import Bot

from app.config import settings
from app.repositories.bot_setting_repo import BotSettingRepository
from app.repositories.payment_repo import PaymentRepository
from app.repositories.user_repo import UserRepository
from app.services.admin_notify_service import AdminNotifyService
from app.services.discount_service import DiscountService
from app.services.payment_qr_code_service import PaymentQrCodeService
from app.services.payment_service import PaymentService
from app.services.subscription_currency_service import SubscriptionCurrencyService
from app.services.subscription_price_service import PLANS, SubscriptionPriceService
from app.services.support_contact_service import get_admin_contact_url


CARD_COUNTRIES = {"tj", "uz", "ru", "other"}
MINIAPP_METHODS = {"visa", "alipay", "wechat"}
MINIAPP_MODES = {"subscription", "referral_discount", "admin_discount", "feedback_discount"}
PAYMENT_DETAILS_KEY = "subscription_payment_details"
MAX_SCREENSHOT_BYTES = 8 * 1024 * 1024
_STATIC_PAYMENTS = Path(__file__).parent.parent / "static" / "payments"
_BOT_USERNAME_CACHE: str | None = None

QR_PHOTO_PATHS = {
    "alipay_10_days": _STATIC_PAYMENTS / "alipay_10_days.jpg",
    "alipay_10_days_discount": _STATIC_PAYMENTS / "alipay_10_days_discount.jpg",
    "alipay_1_month": _STATIC_PAYMENTS / "alipay_1_month.jpg",
    "alipay_1_month_discount": _STATIC_PAYMENTS / "alipay_1_month_discount.jpg",
    "wechat_10_days": _STATIC_PAYMENTS / "wechat_10_days.jpg",
    "wechat_10_days_discount": _STATIC_PAYMENTS / "wechat_10_days_discount.jpg",
    "wechat_1_month": _STATIC_PAYMENTS / "wechat_1_month.jpg",
    "wechat_1_month_discount": _STATIC_PAYMENTS / "wechat_1_month_discount.jpg",
}


@dataclass(frozen=True)
class ScreenshotPayload:
    data: bytes
    mime_type: str
    filename: str


class SubscriptionMiniAppService:
    def __init__(self, session):
        self.session = session
        self.user_repo = UserRepository(session)
        self.payment_repo = PaymentRepository(session)
        self.price_service = SubscriptionPriceService(session)
        self.payment_service = PaymentService(session)
        self.currency_service = SubscriptionCurrencyService(session)
        self.setting_repo = BotSettingRepository(session)

    async def payment_details(self) -> str:
        stored = await self.setting_repo.get(PAYMENT_DETAILS_KEY)
        if stored and stored.strip():
            return stored.strip()
        return settings.PAYMENT_DETAILS.strip()

    async def overview(
        self,
        telegram_id: int,
        bot: Bot | None = None,
        mode: str | None = None,
        campaign_id: int | None = None,
        feedback_id: int | None = None,
    ) -> dict[str, Any]:
        mode = self._normalize_mode(mode)
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return {"ok": False, "error": "access_start_first"}

        pending_payment = await self.payment_repo.get_latest_pending_by_user(telegram_id)
        if pending_payment:
            return {
                "ok": True,
                "language": getattr(user, "language", None) or "uz",
                "mode": mode,
                "support_url": await get_admin_contact_url(self.session),
                "pending_payment": self._pending_payment_payload(pending_payment),
                "offer": None,
                "discount": None,
                "prices": {},
                "card_countries": ["tj", "uz", "ru", "other"],
                "payment_details": "",
                "payment_details_configured": False,
            }

        await self.user_repo.ensure_referral_code(user)
        discount_service = DiscountService(self.session)
        await discount_service.sync_referral_discount_progress(user)
        await self.session.commit()
        payment_details = await self.payment_details()
        prices = await self._prices_payload(
            user,
            mode=mode,
            campaign_id=campaign_id,
            feedback_id=feedback_id,
        )

        return {
            "ok": True,
            "language": getattr(user, "language", None) or "uz",
            "mode": mode,
            "support_url": await get_admin_contact_url(self.session),
            "pending_payment": None,
            "offer": self._offer_payload(mode, prices),
            "discount": await self._discount_payload(user, bot=bot),
            "prices": prices,
            "card_countries": ["tj", "uz", "ru", "other"],
            "payment_details": payment_details,
            "payment_details_configured": bool(payment_details),
        }

    async def start_discount(self, telegram_id: int, bot: Bot | None = None) -> dict[str, Any]:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return {"ok": False, "error": "access_start_first"}

        await self.user_repo.ensure_referral_code(user)
        if not user.discount_used and not user.discount_offer_started_at:
            await self.user_repo.start_discount_offer(user)
        await DiscountService(self.session).sync_referral_discount_progress(user)
        await self.session.commit()

        return {"ok": True, "discount": await self._discount_payload(user, bot=bot)}

    async def quote(
        self,
        *,
        telegram_id: int,
        plan_type: str,
        payment_method: str,
        card_country: str | None = None,
        bot: Bot | None = None,
        include_qr: bool = True,
        mode: str | None = None,
        campaign_id: int | None = None,
        feedback_id: int | None = None,
    ) -> dict[str, Any]:
        mode = self._normalize_mode(mode)
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return {"ok": False, "error": "access_start_first"}

        checkout_info = await self._checkout_info(
            user,
            plan_type,
            payment_method,
            mode=mode,
            campaign_id=campaign_id,
            feedback_id=feedback_id,
        )
        if not checkout_info:
            return {"ok": False, "error": "payment_invalid_plan"}
        payment_details = await self.payment_details() if payment_method == "visa" else ""
        if payment_method == "visa" and not payment_details:
            return {"ok": False, "error": "payment_details_missing"}

        payload = {
            "ok": True,
            "quote": await self._quote_payload(
                user=user,
                plan_type=plan_type,
                payment_method=payment_method,
                card_country=card_country,
                checkout_info=checkout_info,
                payment_details=payment_details,
            ),
        }
        if include_qr and PaymentQrCodeService.is_qr_method(payment_method):
            payload["quote"]["qr"] = await self._qr_payload(
                bot=bot,
                user=user,
                payment_method=payment_method,
                plan_type=plan_type,
                checkout_info=checkout_info,
            )
        return payload

    async def submit(
        self,
        *,
        telegram_id: int,
        plan_type: str,
        payment_method: str,
        card_country: str | None,
        screenshot_data_url: str,
        bot: Bot,
        mode: str | None = None,
        campaign_id: int | None = None,
        feedback_id: int | None = None,
    ) -> dict[str, Any]:
        mode = self._normalize_mode(mode)
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return {"ok": False, "error": "access_start_first"}

        pending_payment = await self.payment_repo.get_latest_pending_by_user(telegram_id)
        if pending_payment:
            return {
                "ok": True,
                "payment_id": pending_payment.id,
                "status": "pending",
                "already_pending": True,
            }

        screenshot = self._decode_screenshot(screenshot_data_url)
        if not screenshot:
            return {"ok": False, "error": "invalid_screenshot"}

        checkout_info = await self._checkout_info(
            user,
            plan_type,
            payment_method,
            mode=mode,
            campaign_id=campaign_id,
            feedback_id=feedback_id,
        )
        if not checkout_info:
            return {"ok": False, "error": "payment_invalid_plan"}
        payment_details = await self.payment_details() if payment_method == "visa" else ""
        if payment_method == "visa" and not payment_details:
            return {"ok": False, "error": "payment_details_missing"}

        if PaymentQrCodeService.is_qr_method(payment_method):
            qr_payload = await self._qr_payload(
                bot=bot,
                user=user,
                payment_method=payment_method,
                plan_type=plan_type,
                checkout_info=checkout_info,
            )
            if not qr_payload.get("available"):
                return {"ok": False, "error": "qr_not_ready"}

        quote = await self._quote_payload(
            user=user,
            plan_type=plan_type,
            payment_method=payment_method,
            card_country=card_country,
            checkout_info=checkout_info,
            payment_details=payment_details,
        )

        user.payment_method = payment_method
        user.selected_plan_type = None
        payment = await self.payment_repo.create(
            user_telegram_id=telegram_id,
            plan_type=plan_type,
            amount=int(checkout_info["final_amount"]),
            currency=str(checkout_info["currency"]),
            payment_status="pending",
            payment_method=payment_method,
            base_amount=int(checkout_info["base_amount"]),
            discount_source=str(checkout_info["discount_source"]),
            discount_percent=int(checkout_info["discount_percent"]),
            discount_campaign_id=checkout_info["discount_campaign_id"],
            discount_title=checkout_info["discount_title"],
            discount_details=checkout_info["discount_details"],
            card_country=quote.get("card_country") if payment_method == "visa" else None,
            local_amount=quote.get("pay_amount") if payment_method == "visa" else None,
            local_currency=quote.get("pay_currency") if payment_method == "visa" else None,
            exchange_rate=quote.get("exchange_rate") if payment_method == "visa" else None,
        )

        pending_count = await self.payment_repo.count_pending()
        try:
            file_id = await AdminNotifyService().notify_payment_review(
                bot=bot,
                payment=payment,
                user=user,
                ai_result=None,
                pending_count=pending_count,
                screenshot_bytes=screenshot.data,
                screenshot_filename=screenshot.filename,
                require_delivery=True,
            )
        except Exception:
            await self.session.rollback()
            return {"ok": False, "error": "admin_notification_failed"}
        if file_id:
            payment.screenshot_file_id = file_id
        await self.session.commit()

        return {
            "ok": True,
            "payment_id": payment.id,
            "status": "pending",
        }

    async def _prices_payload(
        self,
        user,
        *,
        mode: str,
        campaign_id: int | None = None,
        feedback_id: int | None = None,
    ) -> dict[str, dict[str, dict[str, Any]]]:
        result: dict[str, dict[str, dict[str, Any]]] = {}
        for method in MINIAPP_METHODS:
            result[method] = {}
            for plan in PLANS:
                info = await self._checkout_info(
                    user,
                    plan,
                    method,
                    mode=mode,
                    campaign_id=campaign_id,
                    feedback_id=feedback_id,
                )
                if not info:
                    continue
                result[method][plan] = {
                    "base_amount": info["base_amount"],
                    "final_amount": info["final_amount"],
                    "currency": info["currency"],
                    "discount_applied": info["discount_applied"],
                    "discount_percent": info["discount_percent"],
                    "discount_source": info["discount_source"],
                    "discount_campaign_id": info["discount_campaign_id"],
                    "discount_title": info["discount_title"],
                    "discount_title_tj": info["discount_title_tj"],
                    "discount_title_ru": info["discount_title_ru"],
                    "discount_title_uz": info["discount_title_uz"],
                    "discount_reason": info["discount_reason"],
                    "discount_reason_tj": info["discount_reason_tj"],
                    "discount_reason_ru": info["discount_reason_ru"],
                    "discount_reason_uz": info["discount_reason_uz"],
                    "discount_details": info["discount_details"],
                }
        return result

    def _offer_payload(self, mode: str, prices: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any] | None:
        if mode not in {"admin_discount", "feedback_discount"}:
            return None

        offers = [
            item
            for plans in prices.values()
            for item in plans.values()
            if item.get("discount_applied")
        ]
        if not offers:
            return {
                "type": mode,
                "available": False,
                "percent": 0,
            }

        best = max(offers, key=lambda item: int(item.get("discount_percent") or 0))
        return {
            "type": mode,
            "available": True,
            "percent": int(best.get("discount_percent") or 0),
            "campaign_id": best.get("discount_campaign_id"),
            "title": best.get("discount_title"),
            "title_tj": best.get("discount_title_tj"),
            "title_ru": best.get("discount_title_ru"),
            "title_uz": best.get("discount_title_uz"),
            "reason": best.get("discount_reason"),
            "reason_tj": best.get("discount_reason_tj"),
            "reason_ru": best.get("discount_reason_ru"),
            "reason_uz": best.get("discount_reason_uz"),
            "details": best.get("discount_details"),
        }

    async def _discount_payload(self, user, bot: Bot | None = None) -> dict[str, Any] | None:
        if getattr(user, "discount_used", False):
            return None
        referral_count, referral_available = await DiscountService(self.session).sync_referral_discount_progress(user)
        referral_code = getattr(user, "referral_code", None)
        bot_username = await self._bot_username(bot)
        referral_link = (
            f"https://t.me/{bot_username}?start={referral_code}"
            if referral_code and bot_username
            else ""
        )
        return {
            "referral_20_available": bool(referral_available and not user.discount_used),
            "referral_count": int(referral_count),
            "referral_required": 3,
            "discount_used": bool(getattr(user, "discount_used", False)),
            "offer_started": bool(getattr(user, "discount_offer_started_at", None)),
            "referral_link": referral_link,
        }

    @staticmethod
    def _pending_payment_payload(payment) -> dict[str, Any]:
        return {
            "id": payment.id,
            "plan_type": payment.plan_type,
            "payment_method": payment.payment_method,
            "amount": payment.amount,
            "currency": payment.currency,
            "submitted_at": payment.submitted_at.isoformat() if payment.submitted_at else "",
        }

    async def _checkout_info(
        self,
        user,
        plan_type: str,
        payment_method: str,
        *,
        mode: str = "subscription",
        campaign_id: int | None = None,
        feedback_id: int | None = None,
    ) -> dict[str, Any] | None:
        if plan_type not in PLANS or payment_method not in MINIAPP_METHODS:
            return None
        price = await self.price_service.get_price(payment_method, plan_type)
        if not price:
            return None
        discount_service = DiscountService(self.session)
        if mode == "admin_discount":
            if campaign_id:
                discount = await discount_service.get_campaign_discount(
                    campaign_id=campaign_id,
                    user=user,
                    plan_type=plan_type,
                    payment_method=payment_method,
                )
            else:
                discount = await discount_service.get_best_admin_discount(
                    user=user,
                    plan_type=plan_type,
                    payment_method=payment_method,
                )
            if discount.source != "admin_campaign":
                return None
        elif mode == "feedback_discount":
            discount = await discount_service.get_feedback_price_discount(
                user=user,
                feedback_id=feedback_id,
            )
            if discount.source != "feedback_price_offer":
                return None
        else:
            discount = await discount_service.get_best_discount(
                user=user,
                plan_type=plan_type,
                payment_method=payment_method,
                include_admin_campaigns=False,
            )
        final_amount = self.payment_service.calculate_percent_discounted_price(price.amount, discount.percent)
        return {
            "plan_type": plan_type,
            "base_amount": price.amount,
            "final_amount": final_amount,
            "currency": price.currency,
            "discount_applied": discount.percent > 0,
            "discount_percent": discount.percent,
            "discount_source": discount.source,
            "discount_campaign_id": discount.campaign_id,
            "discount_title": discount.title,
            "discount_title_tj": discount.title_tj,
            "discount_title_ru": discount.title_ru,
            "discount_title_uz": discount.title_uz,
            "discount_reason": discount.reason,
            "discount_reason_tj": discount.reason_tj,
            "discount_reason_ru": discount.reason_ru,
            "discount_reason_uz": discount.reason_uz,
            "discount_details": discount.details,
        }

    @staticmethod
    def _normalize_mode(value: str | None) -> str:
        mode = (value or "subscription").strip().lower()
        return mode if mode in MINIAPP_MODES else "subscription"

    async def _quote_payload(
        self,
        *,
        user,
        plan_type: str,
        payment_method: str,
        card_country: str | None,
        checkout_info: dict[str, Any],
        payment_details: str | None = None,
    ) -> dict[str, Any]:
        pay_amount = str(checkout_info["final_amount"])
        pay_currency = str(checkout_info["currency"])
        exchange_rate = ""
        normalized_country = None
        if payment_method == "visa":
            normalized_country = card_country if card_country in CARD_COUNTRIES else "tj"
            card_quote = await self.currency_service.quote_card_amount(
                int(checkout_info["final_amount"]),
                normalized_country,
            )
            pay_amount = card_quote.amount
            pay_currency = card_quote.currency
            exchange_rate = card_quote.exchange_rate

        return {
            "plan_type": plan_type,
            "payment_method": payment_method,
            "card_country": normalized_country,
            "base_amount": checkout_info["base_amount"],
            "base_currency": checkout_info["currency"],
            "final_amount": checkout_info["final_amount"],
            "final_currency": checkout_info["currency"],
            "pay_amount": pay_amount,
            "pay_currency": pay_currency,
            "exchange_rate": exchange_rate,
            "discount_applied": checkout_info["discount_applied"],
            "discount_percent": checkout_info["discount_percent"],
            "discount_source": checkout_info["discount_source"],
            "payment_details": (payment_details or "") if payment_method == "visa" else "",
        }

    async def _bot_username(self, bot: Bot | None) -> str:
        global _BOT_USERNAME_CACHE
        if _BOT_USERNAME_CACHE:
            return _BOT_USERNAME_CACHE
        if bot:
            try:
                me = await bot.get_me()
                username = (getattr(me, "username", None) or "").strip().lstrip("@")
                if username:
                    _BOT_USERNAME_CACHE = username
                    return username
            except Exception:
                pass
        username = (settings.BOT_USERNAME or "").strip().lstrip("@")
        _BOT_USERNAME_CACHE = username
        return username

    async def _qr_payload(
        self,
        *,
        bot: Bot | None,
        user,
        payment_method: str,
        plan_type: str,
        checkout_info: dict[str, Any],
    ) -> dict[str, Any]:
        if not PaymentQrCodeService.is_qr_method(payment_method):
            return {"available": False}

        image_bytes = self._static_qr_bytes(payment_method, plan_type, checkout_info)
        if image_bytes:
            return {
                "available": True,
                "image_data_url": self._data_url(image_bytes, "image/jpeg"),
            }

        if not bot:
            return {"available": False}

        file_id = await self._uploaded_qr_file_id(payment_method, plan_type, checkout_info)
        if not file_id:
            return {"available": False}
        try:
            file = await bot.get_file(file_id)
            file_buffer = await bot.download_file(file.file_path)
            file_buffer.seek(0)
            return {
                "available": True,
                "image_data_url": self._data_url(file_buffer.read(), "image/jpeg"),
            }
        except Exception:
            return {"available": False}

    def _static_qr_bytes(self, payment_method: str, plan_type: str, checkout_info: dict[str, Any]) -> bytes | None:
        discount_source = checkout_info.get("discount_source") or "none"
        if discount_source not in {"none", "referral", "feedback_price_offer"}:
            return None
        amount = int(checkout_info["final_amount"])
        currency = str(checkout_info["currency"])
        if checkout_info.get("discount_applied"):
            if int(checkout_info.get("discount_percent") or 0) != 20:
                return None
            if not PaymentQrCodeService.is_default_subscription_amount(
                payment_method=payment_method,
                plan_type=plan_type,
                amount=amount,
                currency=currency,
                discount_percent=20,
            ):
                return None
            key = f"{payment_method}_{plan_type}_discount"
        else:
            if not PaymentQrCodeService.is_default_subscription_amount(
                payment_method=payment_method,
                plan_type=plan_type,
                amount=amount,
                currency=currency,
            ):
                return None
            key = f"{payment_method}_{plan_type}"

        path = QR_PHOTO_PATHS.get(key)
        if path and path.exists():
            return path.read_bytes()
        return None

    async def _uploaded_qr_file_id(
        self,
        payment_method: str,
        plan_type: str,
        checkout_info: dict[str, Any],
    ) -> str | None:
        scope = PaymentQrCodeService.checkout_scope(
            discount_source=checkout_info.get("discount_source") or "none",
            discount_percent=int(checkout_info.get("discount_percent") or 0),
            discount_campaign_id=checkout_info.get("discount_campaign_id"),
        )
        if not scope:
            return None
        return await PaymentQrCodeService(self.session).get_file_id(
            scope=scope,
            payment_method=payment_method,
            plan_type=plan_type,
            amount=int(checkout_info["final_amount"]),
            currency=str(checkout_info["currency"]),
        )

    @staticmethod
    def _decode_screenshot(value: str) -> ScreenshotPayload | None:
        prefix, _, raw_base64 = (value or "").partition(",")
        if not raw_base64 or ";base64" not in prefix:
            return None
        mime_type = prefix.replace("data:", "").replace(";base64", "").strip().lower()
        if mime_type not in {"image/jpeg", "image/jpg", "image/png", "image/webp"}:
            return None
        try:
            data = base64.b64decode(raw_base64, validate=True)
        except Exception:
            return None
        if not data or len(data) > MAX_SCREENSHOT_BYTES:
            return None
        extension = "jpg" if mime_type in {"image/jpeg", "image/jpg"} else mime_type.rsplit("/", 1)[-1]
        return ScreenshotPayload(
            data=data,
            mime_type=mime_type,
            filename=f"payment.{extension}",
        )

    @staticmethod
    def _data_url(data: bytes, mime_type: str) -> str:
        encoded = base64.b64encode(data).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"
