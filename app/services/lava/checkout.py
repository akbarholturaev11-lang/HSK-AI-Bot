"""Buyer-facing lava.top checkout: overview block, start, status, cancel.

Provider IO never runs inside a DB transaction. ``start`` reserves a local row
under the user lock first (so parallel taps cannot create two subscriptions),
calls lava, then stores the real contract id.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from sqlalchemy import and_, func, or_, select

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.db.models.lava import LavaInvoice
from app.repositories.payment_repo import PaymentRepository
from app.repositories.user_repo import UserRepository
from app.services.discount_service import DiscountService
from app.services.lava import events, ledger
from app.services.lava.client import LavaError
from app.services.lava.config import LavaConfig, LavaConfigService, effective_mode
from app.services.lava.terms import LAVA_PAYMENT_METHOD, LAVA_SOURCES, LOCAL_CONTRACT_PREFIX, normalize_email

logger = logging.getLogger(__name__)

RESERVATION_SECONDS = 90
STARTS_PER_HOUR = 6
STATUS_RECHECK_SECONDS = 8
# lava's payment widget supports EN/RU/ES only; RU is the closest for UZ/RU/TJ buyers.
BUYER_LANGUAGE = "RU"


class LavaCheckoutError(Exception):
    def __init__(self, code: str, status: int = 409):
        super().__init__(code)
        self.code = code
        self.status = status


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    value = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
    return value.astimezone(timezone.utc).isoformat()


DISCOUNT_MODES = ("referral_discount", "admin_discount", "feedback_discount", "exit_discount")
CHECKOUT_CONTEXT_MODES = ("", "subscription", *DISCOUNT_MODES)


@dataclass(frozen=True)
class LavaDiscount:
    source: str
    percent: int
    campaign_id: int | None
    promo_code: str


def discounted(amount: Decimal | None, percent: int) -> Decimal | None:
    if amount is None:
        return None
    return (amount * Decimal(100 - percent) / Decimal(100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _active_subscription_clause(user_id: int):
    return and_(
        LavaInvoice.user_id == user_id, LavaInvoice.kind.in_(("first", "external")),
        LavaInvoice.status == "paid",
        or_(LavaInvoice.subscription_status.is_(None), LavaInvoice.subscription_status == "active"),
    )


class LavaCheckoutService:
    def __init__(self, runtime: events.LavaRuntime):
        self.runtime = runtime
        self.settings = runtime.settings

    async def _blocked_reason(self, session, user) -> str | None:
        if await PaymentRepository(session).get_latest_pending_by_user(user):
            return "payment_pending"
        open_chargeback = await session.scalar(select(func.count(LavaInvoice.id)).where(
            LavaInvoice.user_id == user.id, LavaInvoice.status == "chargeback_open"))
        if open_chargeback:
            return "chargeback_open"
        active = await session.scalar(select(func.count(LavaInvoice.id)).where(
            _active_subscription_clause(user.id)))
        if active:
            return "subscription_active"
        return None

    async def _subscription(self, session, user) -> dict | None:
        row = (await session.execute(select(LavaInvoice).where(
            LavaInvoice.user_id == user.id, LavaInvoice.kind.in_(("first", "external")),
            LavaInvoice.status.in_(("paid", "chargeback_won")),
        ).order_by(LavaInvoice.paid_at.desc()).limit(1))).scalar_one_or_none()
        if row is None:
            return None
        return {
            "plan_type": row.plan_type,
            "status": row.subscription_status or "active",
            "auto_renew": (row.subscription_status or "active") == "active",
            "pro_until": _iso(getattr(user, "end_date", None)),
        }

    async def resolve_discount(self, session, user, config: LavaConfig, *, plan_type: str,
                               mode: str | None, campaign_id: int | None = None,
                               feedback_id: int | None = None) -> LavaDiscount | None:
        """The same server-owned discount rules as the manual checkout, but a
        discount reaches lava only through an admin-mapped promo code."""
        if not config.promo_codes:
            return None
        service = DiscountService(session)
        mode = mode or "subscription"
        if mode == "exit_discount":
            # Never trust the client mode alone. A per-account accepted,
            # unexpired PWA offer and an actual provider promo are mandatory.
            from app.services.pwa_exit_offer_service import PwaExitOfferService, EXIT_PERCENT
            if not await PwaExitOfferService(session, self.settings).active(user):
                return None
            choice = await service.get_best_discount(
                user=user, plan_type=plan_type, payment_method=LAVA_PAYMENT_METHOD,
                include_admin_campaigns=True,
            )
            if choice.percent > EXIT_PERCENT and config.promo_code(choice.source, choice.percent):
                return LavaDiscount(
                    source=choice.source, percent=int(choice.percent),
                    campaign_id=choice.campaign_id,
                    promo_code=config.promo_code(choice.source, choice.percent),
                )
            promo = config.promo_code("exit_offer", EXIT_PERCENT)
            return LavaDiscount(
                source="exit_offer", percent=EXIT_PERCENT, campaign_id=None, promo_code=promo
            ) if promo else None
        if mode == "admin_discount":
            choice = (await service.get_campaign_discount(
                campaign_id=campaign_id, user=user, plan_type=plan_type, payment_method=LAVA_PAYMENT_METHOD)
                if campaign_id else await service.get_best_admin_discount(
                    user=user, plan_type=plan_type, payment_method=LAVA_PAYMENT_METHOD))
        elif mode == "feedback_discount":
            choice = await service.get_feedback_price_discount(user=user, feedback_id=feedback_id)
        else:
            choice = await service.get_best_discount(user=user, plan_type=plan_type,
                                                     payment_method=LAVA_PAYMENT_METHOD,
                                                     include_admin_campaigns=True)
        if not choice or choice.percent <= 0:
            return None
        code = config.promo_code(choice.source, choice.percent)
        if not code:
            return None
        return LavaDiscount(source=choice.source, percent=int(choice.percent),
                            campaign_id=choice.campaign_id, promo_code=code)

    async def overview_block(self, session, user, *, supports_lava: bool, context_mode: str | None = None,
                             campaign_id: int | None = None, feedback_id: int | None = None) -> dict | None:
        """``None`` keeps the existing overview byte-identical (manual only).
        Discount flows get a lava block only when a promo code carries the
        same discount; otherwise they stay on the manual path."""
        config = await LavaConfigService(session).load()
        mode = effective_mode(config, self.settings, client_supports_lava=supports_lava)
        discount_flow = (context_mode or "subscription") in DISCOUNT_MODES
        subscription = await self._subscription(session, user) if supports_lava and not discount_flow else None
        plans = []
        if mode != "manual_only":
            for term in config.sellable_terms():
                row = {"plan_type": term.plan_type, "months": term.months, "days": term.days,
                       "amount": None if term.price_amount is None else str(term.price_amount),
                       "currency": term.price_currency or config.currency}
                discount = await self.resolve_discount(session, user, config, plan_type=term.plan_type,
                                                       mode=context_mode, campaign_id=campaign_id,
                                                       feedback_id=feedback_id)
                if discount is not None:
                    row["discount_percent"] = discount.percent
                    row["base_amount"] = row["amount"]
                    estimate = discounted(term.price_amount, discount.percent)
                    row["amount"] = None if estimate is None else str(estimate)
                elif discount_flow:
                    continue
                plans.append(row)
            if discount_flow and not plans:
                return None
        if mode == "manual_only" and subscription is None:
            return None
        last_email = await session.scalar(select(LavaInvoice.buyer_email).where(
            LavaInvoice.user_id == user.id, LavaInvoice.buyer_email.is_not(None),
        ).order_by(LavaInvoice.id.desc()).limit(1))
        return {
            "mode": mode,
            "currency": config.currency,
            "plans": plans,
            "blocked_reason": await self._blocked_reason(session, user),
            "subscription": subscription,
            "email": last_email,
        }

    async def start(self, session_factory, *, user_id: int, plan_type: str, email: str,
                    source: str, language: str | None, supports_lava: bool = True,
                    context_mode: str | None = None, campaign_id: int | None = None,
                    feedback_id: int | None = None,
                    analytics_attempt_id: str | None = None,
                    analytics_source: str | None = None,
                    pwa_inline_return: bool = False) -> dict:
        if source not in LAVA_SOURCES:
            raise LavaCheckoutError("invalid_source", 400)
        if (context_mode or "") not in CHECKOUT_CONTEXT_MODES:
            raise LavaCheckoutError("invalid_request", 400)
        if context_mode == "exit_discount" and source not in {"pwa", "android"}:
            raise LavaCheckoutError("invalid_request", 400)
        buyer_email = normalize_email(email)
        if buyer_email is None:
            raise LavaCheckoutError("invalid_email", 400)
        now = _now()
        reservation = f"{LOCAL_CONTRACT_PREFIX}{uuid.uuid4().hex[:29]}"
        async with session_factory() as session:
            async with session.begin():
                user = await UserRepository(session).get_by_user_id(user_id, lock=True)
                if user is None or user.status == "blocked":
                    raise LavaCheckoutError("user_not_found", 404)
                config = await LavaConfigService(session).load()
                if effective_mode(config, self.settings, client_supports_lava=supports_lava) == "manual_only":
                    raise LavaCheckoutError("lava_unavailable")
                term = config.terms.get(plan_type)
                if term is None or not term.sellable:
                    raise LavaCheckoutError("plan_unavailable")
                if source == "android" and await session.scalar(select(LavaInvoice.id).where(
                        LavaInvoice.user_id == user.id, LavaInvoice.source == "android",
                        LavaInvoice.review_reason == "create_uncertain").limit(1)):
                    raise LavaCheckoutError("checkout_needs_review")
                reason = await self._blocked_reason(session, user)
                if reason:
                    raise LavaCheckoutError(reason)
                in_flight = await session.scalar(select(func.count(LavaInvoice.id)).where(
                    LavaInvoice.user_id == user.id, LavaInvoice.status == "created",
                    LavaInvoice.contract_id.like(f"{LOCAL_CONTRACT_PREFIX}%"),
                    LavaInvoice.created_at > now - timedelta(seconds=RESERVATION_SECONDS)))
                if in_flight:
                    raise LavaCheckoutError("checkout_in_progress")
                recent = await session.scalar(select(func.count(LavaInvoice.id)).where(
                    LavaInvoice.user_id == user.id, LavaInvoice.kind == "first",
                    LavaInvoice.created_at > now - timedelta(hours=1)))
                if recent >= STARTS_PER_HOUR:
                    raise LavaCheckoutError("too_many_attempts", 429)
                discount = await self.resolve_discount(session, user, config, plan_type=plan_type,
                                                       mode=context_mode, campaign_id=campaign_id,
                                                       feedback_id=feedback_id)
                if (context_mode or "subscription") in DISCOUNT_MODES and discount is None:
                    # A discount link must never silently become a full price.
                    raise LavaCheckoutError("discount_unavailable")
                row = LavaInvoice(
                    contract_id=reservation, kind="first", user_id=user.id, plan_type=plan_type,
                    offer_id=term.offer_id, periodicity=term.periodicity, currency=config.currency,
                    expected_amount=(discounted(term.price_amount, discount.percent) if discount
                                     else term.price_amount),
                    buyer_email=buyer_email, source=source,
                    pwa_inline_attempt_id=(analytics_attempt_id if source == "pwa" else None),
                    pwa_inline_source=(analytics_source if source == "pwa" else None),
                    promo_code=discount.promo_code if discount else None,
                    discount_source=discount.source if discount else None,
                    discount_percent=discount.percent if discount else None,
                    discount_campaign_id=discount.campaign_id if discount else None,
                    status="created", review_reason="reserving", created_at=now, updated_at=now,
                )
                session.add(row)
                await session.flush()
                reserved_id = row.id
                offer_id, periodicity, currency = term.offer_id, term.periodicity, config.currency
                promo_code = discount.promo_code if discount else None
        if pwa_inline_return and source == "pwa":
            # The PWA paywall navigates to the provider in the same window, so
            # the provider must bring the learner back into the app. The
            # outcome hint is UI-only; access still comes from the webhook.
            success_url = self._return_url(language, pwa_checkout_id=reserved_id, outcome="success")
            failure_url = self._return_url(language, pwa_checkout_id=reserved_id, outcome="fail")
            cancel_url = self._return_url(language, pwa_checkout_id=reserved_id, outcome="cancel")
        else:
            success_url = failure_url = cancel_url = self._return_url(language)
        try:
            created = await self.runtime.client().create_invoice(
                email=buyer_email, offer_id=offer_id, currency=currency, periodicity=periodicity,
                buyer_language=BUYER_LANGUAGE, promo_code=promo_code,
                success_url=success_url, failure_url=failure_url, cancel_url=cancel_url,
            )
        except LavaError as exc:
            # Keep the upstream failure diagnosable without logging email,
            # API keys, provider response bodies, or buyer/invoice identifiers.
            logger.warning(
                "lava invoice create failed: code=%s upstream_status=%s uncertain=%s",
                exc.code, exc.http_status, exc.uncertain,
            )
            async with session_factory() as session, session.begin():
                row = await session.get(LavaInvoice, reserved_id, with_for_update=True)
                row.status = "failed"
                row.review_reason = "create_uncertain" if exc.uncertain else "create_rejected"
            if exc.uncertain:
                await self.runtime.notifier.admin_alert("needs_review", invoice_id=reserved_id,
                                                        detail="invoice create uncertain")
            elif promo_code:
                # Most likely an unknown/expired promo code in the lava cabinet.
                await self.runtime.notifier.admin_alert("promo_rejected", invoice_id=reserved_id,
                                                        detail=promo_code, throttle_seconds=600)
            raise LavaCheckoutError("provider_unavailable", 503) from None
        async with session_factory() as session, session.begin():
            row = await session.get(LavaInvoice, reserved_id, with_for_update=True)
            row.contract_id = created.contract_id
            row.review_reason = None
            if created.amount is not None and created.currency == currency:
                row.expected_amount = created.amount
        return {"ok": True, "checkout_id": reserved_id, "payment_url": created.payment_url,
                "amount": None if created.amount is None else str(created.amount),
                "currency": created.currency or currency}

    def _return_url(self, language: str | None, *, pwa_checkout_id: int | None = None,
                    outcome: str | None = None) -> str | None:
        lang = (language or "ru")[:2]
        lang = lang if lang in {"uz", "ru", "tj"} else "ru"
        try:
            from app.public_site.render import public_origin
            origin = public_origin(self.settings)
        except ValueError:
            return None
        if pwa_checkout_id is not None:
            # Fixed same-origin app path (no client-supplied redirect target).
            query = urlencode({"lang": lang, "pro_checkout": int(pwa_checkout_id),
                               "pro_return": outcome if outcome in {"success", "fail", "cancel"} else "cancel"})
            return origin + "/iphone-pwa/course?" + query
        return origin + f"/pay/lava/return?lang={lang}"

    async def status(self, session_factory, *, user_id: int, checkout_id: int) -> dict:
        async with session_factory() as session:
            row = await session.get(LavaInvoice, checkout_id)
            if row is None or row.user_id != user_id:
                raise LavaCheckoutError("checkout_not_found", 404)
            contract_id, status, checked = row.contract_id, row.status, row.last_checked_at
        recheck = (
            status in ledger.APPLICABLE_STATUSES and not contract_id.startswith(LOCAL_CONTRACT_PREFIX)
            and (checked is None or _now() - (checked if checked.tzinfo else checked.replace(tzinfo=timezone.utc))
                 > timedelta(seconds=STATUS_RECHECK_SECONDS))
        )
        if recheck:
            async with session_factory() as session, session.begin():
                locked = await session.get(LavaInvoice, checkout_id, with_for_update=True)
                locked.last_checked_at = _now()
            result, _, _ = await events.verify_and_apply(self.runtime, contract_id)
            logger.info("lava.top status recheck for checkout %s: %s", checkout_id, result)
        async with session_factory() as session:
            row = await session.get(LavaInvoice, checkout_id)
            user = await UserRepository(session).get_by_user_id(user_id)
            public = {"paid": "paid", "chargeback_won": "paid", "failed": "failed", "expired": "failed"}
            return {"ok": True, "checkout_id": checkout_id,
                    "status": public.get(row.status, "pending" if row.status == "created" else row.status),
                    "plan_type": row.plan_type,
                    "pro_until": _iso(getattr(user, "end_date", None)) if row.status == "paid" else None}

    async def cancel(self, session_factory, *, user_id: int) -> dict:
        async with session_factory() as session:
            row = (await session.execute(select(LavaInvoice).where(
                _active_subscription_clause(user_id)).order_by(LavaInvoice.paid_at.desc()).limit(1)
            )).scalar_one_or_none()
            if row is None:
                raise LavaCheckoutError("subscription_not_found", 404)
            contract_id, email = row.contract_id, row.buyer_email
        if not email:
            raise LavaCheckoutError("subscription_email_missing", 409)
        try:
            await self.runtime.client().cancel_subscription(parent_contract_id=contract_id, email=email)
        except LavaError as exc:
            if exc.http_status == 404:
                # lava no longer has an active subscription: record cancellation.
                pass
            elif exc.uncertain:
                return {"ok": False, "error": "cancel_uncertain"}
            else:
                raise LavaCheckoutError("provider_unavailable", 503) from None
        row, _ = await ledger.mark_subscription(session_factory, contract_id, status="cancelled")
        async with session_factory() as session:
            user = await UserRepository(session).get_by_user_id(user_id)
            return {"ok": True, "status": "cancelled",
                    "pro_until": _iso(getattr(user, "end_date", None))}
