"""lava.top business settings and the server-owned effective checkout mode.

Secrets and kill-switches live in env (``LAVA_*``). Business settings live in
``bot_settings[lava_top_config_v1]`` and are written only by the passkey-bound
Admin PWA ``lava.settings`` command. Every unsafe or unsupported state falls
back to ``manual_only`` so a buyer always has a working checkout.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from decimal import Decimal

from app.repositories.bot_setting_repo import BotSettingRepository
from app.services.lava.terms import (
    CHECKOUT_MODES, LAVA_CURRENCIES, LAVA_PLAN_TYPES, LAVA_TERMS, is_uuid, money, term_days,
)

logger = logging.getLogger(__name__)

LAVA_CONFIG_KEY = "lava_top_config_v1"


class LavaConfigError(ValueError):
    pass


@dataclass(frozen=True)
class LavaTermConfig:
    plan_type: str
    enabled: bool = False
    offer_id: str = ""
    price_amount: Decimal | None = None
    price_currency: str | None = None

    @property
    def periodicity(self) -> str:
        return LAVA_TERMS[self.plan_type][0]

    @property
    def months(self) -> int:
        return LAVA_TERMS[self.plan_type][1]

    @property
    def days(self) -> int:
        return int(term_days(self.plan_type) or 0)

    @property
    def sellable(self) -> bool:
        return bool(self.enabled and is_uuid(self.offer_id))


@dataclass(frozen=True)
class LavaConfig:
    checkout_mode: str = "manual_only"
    currency: str = "USD"
    terms: dict[str, LavaTermConfig] = field(default_factory=lambda: {
        plan: LavaTermConfig(plan_type=plan) for plan in LAVA_PLAN_TYPES
    })

    def sellable_terms(self) -> list[LavaTermConfig]:
        return [term for plan in LAVA_PLAN_TYPES if (term := self.terms.get(plan)) and term.sellable]

    def to_json(self) -> dict:
        return {
            "version": 1,
            "checkout_mode": self.checkout_mode,
            "currency": self.currency,
            "plans": {
                plan: {
                    "enabled": term.enabled,
                    "offer_id": term.offer_id,
                    "price": (None if term.price_amount is None else
                              {"amount": str(term.price_amount), "currency": term.price_currency}),
                }
                for plan, term in self.terms.items()
            },
        }


def parse_config(raw: str | None, *, strict: bool = False) -> LavaConfig:
    """Parse stored JSON. Non-strict parsing of corrupt data degrades to manual."""
    if raw is None or raw == "":
        return LavaConfig()
    try:
        data = json.loads(raw)
        return config_from_dict(data)
    except (ValueError, TypeError, LavaConfigError) as exc:
        if strict:
            raise LavaConfigError("invalid_lava_config") from exc
        logger.error("Stored lava.top config is invalid; falling back to manual_only")
        return LavaConfig()


def config_from_dict(data) -> LavaConfig:
    if not isinstance(data, dict):
        raise LavaConfigError("invalid_lava_config")
    mode = data.get("checkout_mode", "manual_only")
    if mode not in CHECKOUT_MODES:
        raise LavaConfigError("invalid_checkout_mode")
    currency = data.get("currency", "USD")
    if currency not in LAVA_CURRENCIES:
        raise LavaConfigError("invalid_currency")
    plans = data.get("plans") or {}
    if not isinstance(plans, dict) or set(plans) - set(LAVA_PLAN_TYPES):
        raise LavaConfigError("invalid_plans")
    terms = {}
    for plan in LAVA_PLAN_TYPES:
        row = plans.get(plan) or {}
        if not isinstance(row, dict):
            raise LavaConfigError("invalid_plans")
        enabled = row.get("enabled", False)
        offer_id = (row.get("offer_id") or "").strip().lower()
        if not isinstance(enabled, bool) or (offer_id and not is_uuid(offer_id)):
            raise LavaConfigError("invalid_plans")
        if enabled and not offer_id:
            raise LavaConfigError("enabled_term_requires_offer")
        price = row.get("price")
        amount = price_currency = None
        if price is not None:
            if not isinstance(price, dict):
                raise LavaConfigError("invalid_plans")
            amount = money(price.get("amount"))
            price_currency = price.get("currency")
            if amount is None or price_currency not in LAVA_CURRENCIES:
                raise LavaConfigError("invalid_plans")
        terms[plan] = LavaTermConfig(plan_type=plan, enabled=enabled, offer_id=offer_id,
                                     price_amount=amount, price_currency=price_currency)
    return LavaConfig(checkout_mode=mode, currency=currency, terms=terms)


def sales_configured(settings_obj) -> bool:
    return bool(
        getattr(settings_obj, "LAVA_ENABLED", False) is True
        and getattr(settings_obj, "LAVA_API_KEY", "")
        and getattr(settings_obj, "LAVA_WEBHOOK_SECRET", "")
    )


def effective_mode(config: LavaConfig, settings_obj, *, client_supports_lava: bool) -> str:
    """Server-owned mode. Anything unsafe/unsupported means manual_only."""
    if config.checkout_mode == "manual_only":
        return "manual_only"
    if not client_supports_lava or not sales_configured(settings_obj):
        return "manual_only"
    terms = config.sellable_terms()
    if not terms or any(term.price_currency not in (None, config.currency) for term in terms):
        return "manual_only"
    return config.checkout_mode


class LavaConfigService:
    def __init__(self, session):
        self.session = session
        self.repo = BotSettingRepository(session)

    async def load(self) -> LavaConfig:
        return parse_config(await self.repo.get(LAVA_CONFIG_KEY))

    async def record(self):
        return await self.repo.get_record(LAVA_CONFIG_KEY)

    async def save(self, config: LavaConfig) -> None:
        await self.repo.set(LAVA_CONFIG_KEY, json.dumps(config.to_json(), sort_keys=True,
                                                         separators=(",", ":")))
