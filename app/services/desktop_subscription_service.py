from __future__ import annotations

import secrets
from datetime import datetime
from typing import Any

from aiogram import Bot
from sqlalchemy import select

from app.db.models.conversion_funnel_event import ConversionFunnelEvent
from app.services.conversion_funnel_service import ConversionFunnelService
from app.services.desktop_auth_service import DesktopAuthService
from app.services.subscription_entry_analytics_service import (
    SubscriptionEntryAnalyticsService,
)
from app.services.subscription_miniapp_service import SubscriptionMiniAppService
from app.services.user_access_state_service import (
    UserAccessState,
    UserAccessStateService,
)


DESKTOP_SUBSCRIPTION_SOURCE = "desktop_subscription"
DESKTOP_SUBSCRIPTION_MODE = "subscription"
DESKTOP_SUBSCRIPTION_STAGES = {
    "payment_instructions_viewed",
    "payment_receipt_selected",
}


class DesktopSubscriptionError(RuntimeError):
    def __init__(self, code: str, *, status_code: int):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


class DesktopSubscriptionService:
    """Bearer-authenticated adapter around the canonical checkout service.

    Prices, discounts, QR payloads, payment creation and admin delivery remain
    owned by ``SubscriptionMiniAppService``. This adapter only binds those
    operations to the user from a verified desktop session and applies the
    desktop-specific read-only policy for active paid accounts.
    """

    def __init__(self, session, settings_obj, *, bot: Bot):
        self.session = session
        self.settings = settings_obj
        self.bot = bot
        self.checkout = SubscriptionMiniAppService(session)

    async def _context(self, access_token: str):
        return await DesktopAuthService(
            self.session,
            self.settings,
        ).authenticate(access_token)

    @staticmethod
    def _expires_at(user) -> str | None:
        value = UserAccessStateService.as_utc(getattr(user, "end_date", None))
        if not isinstance(value, datetime):
            return None
        return value.isoformat().replace("+00:00", "Z")

    @classmethod
    def _access_payload(cls, user) -> dict[str, Any]:
        state = UserAccessStateService.classify(user)
        return {
            "state": state,
            "is_paid": state == UserAccessState.PAID,
            "expires_at": cls._expires_at(user),
        }

    @classmethod
    def _checkout_restriction(cls, user) -> tuple[str, int] | None:
        state = UserAccessStateService.classify(user)
        if state == UserAccessState.PAID:
            # The existing activation flow starts a fresh period instead of
            # extending the remaining one. Keep active subscriptions read-only
            # until renewal semantics are changed centrally and tested.
            return "desktop_subscription_active", 409
        if state == UserAccessState.BLOCKED:
            return "desktop_subscription_blocked", 403
        return None

    @classmethod
    def _ensure_checkout_allowed(cls, user) -> None:
        restriction = cls._checkout_restriction(user)
        if restriction:
            code, status_code = restriction
            raise DesktopSubscriptionError(code, status_code=status_code)

    @staticmethod
    def _service_error(result: dict[str, Any]) -> DesktopSubscriptionError:
        code = str(result.get("error") or "desktop_subscription_failed")
        status_by_code = {
            "access_start_first": 401,
            "payment_invalid_plan": 422,
            "invalid_screenshot": 422,
            "payment_details_missing": 503,
            "qr_not_ready": 503,
            "admin_notification_failed": 503,
        }
        return DesktopSubscriptionError(
            code,
            status_code=status_by_code.get(code, 400),
        )

    @classmethod
    def _checked_result(cls, result: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(result, dict) or result.get("ok") is not True:
            raise cls._service_error(result if isinstance(result, dict) else {})
        return result

    @staticmethod
    def _attempt_id() -> str:
        return f"desktop-{secrets.token_urlsafe(18)}"

    async def _record_checkout_opened(self, *, user, attempt_id: str) -> None:
        await ConversionFunnelService().record(
            event_name="checkout_opened",
            user=user,
            telegram_id=user.telegram_id,
            source=DESKTOP_SUBSCRIPTION_SOURCE,
            payload={
                "attempt_id": attempt_id,
                "mode": DESKTOP_SUBSCRIPTION_MODE,
            },
        )

    async def overview(self, access_token: str) -> dict[str, Any]:
        context = await self._context(access_token)
        result = self._checked_result(
            await self.checkout.overview(
                context.user.telegram_id,
                bot=self.bot,
                mode=DESKTOP_SUBSCRIPTION_MODE,
            )
        )
        access = self._access_payload(context.user)
        restriction = self._checkout_restriction(context.user)
        pending = result.get("pending_payment") is not None
        read_only_reason = restriction[0] if restriction else None
        if not read_only_reason and pending:
            read_only_reason = "desktop_subscription_pending"

        if restriction:
            # Never expose actionable prices/details for an account that this
            # adapter will refuse to charge.
            result["offer"] = None
            result["discount"] = None
            result["prices"] = {}
            result["payment_details"] = ""
            result["payment_details_configured"] = False

        result.update(
            {
                "source": DESKTOP_SUBSCRIPTION_SOURCE,
                "mode": DESKTOP_SUBSCRIPTION_MODE,
                "access": access,
                "checkout_allowed": read_only_reason is None,
                "read_only_reason": read_only_reason,
                "attempt_id": None,
            }
        )

        await SubscriptionEntryAnalyticsService(self.session).record_entry(
            telegram_id=context.user.telegram_id,
            user=context.user,
            source=DESKTOP_SUBSCRIPTION_SOURCE,
            mode=DESKTOP_SUBSCRIPTION_MODE,
        )

        if result["checkout_allowed"]:
            attempt_id = self._attempt_id()
            result["attempt_id"] = attempt_id
            await self._record_checkout_opened(
                user=context.user,
                attempt_id=attempt_id,
            )
        return result

    async def start_discount(self, access_token: str) -> dict[str, Any]:
        context = await self._context(access_token)
        self._ensure_checkout_allowed(context.user)
        result = self._checked_result(
            await self.checkout.start_discount(
                context.user.telegram_id,
                bot=self.bot,
            )
        )
        result.update(
            {
                "source": DESKTOP_SUBSCRIPTION_SOURCE,
                "mode": DESKTOP_SUBSCRIPTION_MODE,
                "access": self._access_payload(context.user),
            }
        )
        return result

    async def quote(
        self,
        access_token: str,
        *,
        plan_type: str,
        payment_method: str,
        card_country: str | None,
    ) -> dict[str, Any]:
        context = await self._context(access_token)
        self._ensure_checkout_allowed(context.user)
        if payment_method != "visa" and card_country is not None:
            raise DesktopSubscriptionError(
                "desktop_subscription_request_invalid",
                status_code=422,
            )
        result = self._checked_result(
            await self.checkout.quote(
                telegram_id=context.user.telegram_id,
                plan_type=plan_type,
                payment_method=payment_method,
                card_country=card_country,
                bot=self.bot,
                mode=DESKTOP_SUBSCRIPTION_MODE,
            )
        )
        result.update(
            {
                "source": DESKTOP_SUBSCRIPTION_SOURCE,
                "mode": DESKTOP_SUBSCRIPTION_MODE,
                "access": self._access_payload(context.user),
            }
        )
        return result

    async def record_event(
        self,
        access_token: str,
        *,
        attempt_id: str,
        stage: str,
        plan_type: str,
        payment_method: str,
    ) -> dict[str, Any]:
        context = await self._context(access_token)
        self._ensure_checkout_allowed(context.user)
        if stage not in DESKTOP_SUBSCRIPTION_STAGES:
            raise DesktopSubscriptionError(
                "invalid_subscription_stage",
                status_code=422,
            )

        base_event = (
            await self.session.execute(
                select(ConversionFunnelEvent.id)
                .where(
                    ConversionFunnelEvent.telegram_id
                    == int(context.user.telegram_id),
                    ConversionFunnelEvent.event_name == "checkout_opened",
                    ConversionFunnelEvent.source == DESKTOP_SUBSCRIPTION_SOURCE,
                    ConversionFunnelEvent.payload_json.like(
                        f'%"attempt_id": "{attempt_id}"%'
                    ),
                    ConversionFunnelEvent.payload_json.not_like('%"stage":%'),
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if not base_event:
            raise DesktopSubscriptionError(
                "checkout_attempt_not_opened",
                status_code=409,
            )

        recorded = await ConversionFunnelService().record(
            event_name="checkout_opened",
            user=context.user,
            telegram_id=context.user.telegram_id,
            source=DESKTOP_SUBSCRIPTION_SOURCE,
            payload={
                "attempt_id": attempt_id,
                "stage": stage,
                "plan_type": plan_type,
                "payment_method": payment_method,
                "mode": DESKTOP_SUBSCRIPTION_MODE,
            },
        )
        return {
            "ok": bool(recorded),
            "source": DESKTOP_SUBSCRIPTION_SOURCE,
        }

    async def submit(
        self,
        access_token: str,
        *,
        plan_type: str,
        payment_method: str,
        card_country: str | None,
        screenshot_data_url: str,
        attempt_id: str | None = None,
    ) -> dict[str, Any]:
        context = await self._context(access_token)
        self._ensure_checkout_allowed(context.user)
        if payment_method != "visa" and card_country is not None:
            raise DesktopSubscriptionError(
                "desktop_subscription_request_invalid",
                status_code=422,
            )
        result = self._checked_result(
            await self.checkout.submit(
                telegram_id=context.user.telegram_id,
                plan_type=plan_type,
                payment_method=payment_method,
                card_country=card_country,
                screenshot_data_url=screenshot_data_url,
                bot=self.bot,
                mode=DESKTOP_SUBSCRIPTION_MODE,
            )
        )
        result.update(
            {
                "source": DESKTOP_SUBSCRIPTION_SOURCE,
                "mode": DESKTOP_SUBSCRIPTION_MODE,
                "access": self._access_payload(context.user),
            }
        )
        if result.get("payment_id") and not result.get("already_pending"):
            await ConversionFunnelService().record(
                event_name="payment_screenshot_submitted",
                user=context.user,
                telegram_id=context.user.telegram_id,
                source=DESKTOP_SUBSCRIPTION_SOURCE,
                payment_id=int(result["payment_id"]),
                payload={
                    "attempt_id": attempt_id,
                    "plan_type": plan_type,
                    "payment_method": payment_method,
                    "mode": DESKTOP_SUBSCRIPTION_MODE,
                },
            )
        return result
