"""Fixed lava.top term/periodicity contract shared by every lava module."""
from __future__ import annotations

import re
from decimal import Decimal, ROUND_HALF_UP

from app.services.subscription_service import SUBSCRIPTION_PLAN_DURATIONS

# plan_type -> (lava periodicity, months shown to the buyer)
LAVA_TERMS: dict[str, tuple[str, int]] = {
    "1_month": ("MONTHLY", 1),
    "3_months": ("PERIOD_90_DAYS", 3),
    "6_months": ("PERIOD_180_DAYS", 6),
    "12_months": ("PERIOD_YEAR", 12),
}
LAVA_PLAN_TYPES = tuple(LAVA_TERMS)
PERIODICITY_TO_PLAN = {periodicity: plan for plan, (periodicity, _) in LAVA_TERMS.items()}
# Phase 1 money contract: amounts convert to TJS/USD for AI budget/revenue.
LAVA_CURRENCIES = ("USD", "RUB")
CHECKOUT_MODES = ("manual_only", "lava_only", "both")
LAVA_PAYMENT_METHOD = "lava"
LAVA_SOURCES = ("miniapp", "pwa", "android", "desktop", "admin_link", "reconcile")

_UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_EMAIL_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$")
LOCAL_CONTRACT_PREFIX = "local-"


def term_days(plan_type: str) -> int | None:
    if plan_type not in LAVA_TERMS:
        return None
    return SUBSCRIPTION_PLAN_DURATIONS.get(plan_type)


def is_uuid(value) -> bool:
    return isinstance(value, str) and bool(_UUID_RE.match(value))


def normalize_email(value) -> str | None:
    if not isinstance(value, str):
        return None
    email = value.strip().lower()
    if not email or len(email) > 254 or not _EMAIL_RE.match(email):
        return None
    local, _, domain = email.partition("@")
    if len(local) > 64 or ".." in email:
        return None
    return email


def money(value) -> Decimal | None:
    """Parse a provider amount into a 2-decimal Decimal; reject junk."""
    if value is None or isinstance(value, bool):
        return None
    try:
        amount = Decimal(str(value))
    except Exception:  # noqa: BLE001 - provider data is untrusted
        return None
    if not amount.is_finite() or amount < 0 or amount > Decimal("10000000"):
        return None
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def amounts_equal(left, right) -> bool:
    a, b = money(left), money(right)
    return a is not None and b is not None and abs(a - b) <= Decimal("0.01")
