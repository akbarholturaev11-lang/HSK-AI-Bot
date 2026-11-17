"""Exact major-unit amount of a payment.

``payments.amount`` is an integer column (manual prices are whole TJS/¥).
lava.top charges decimal prices (e.g. 7.90 USD); the activation stores the
rounded integer in ``amount`` and the exact provider value in
``local_amount``/``local_currency``. Revenue, commission and AI budget
calculations must use the exact value so no cent is invented or lost.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation


def payment_amount(payment) -> float:
    amount = getattr(payment, "amount", 0) or 0
    if getattr(payment, "payment_method", None) != "lava":
        return float(amount)
    local = getattr(payment, "local_amount", None)
    if not local or getattr(payment, "local_currency", None) != getattr(payment, "currency", None):
        return float(amount)
    try:
        exact = Decimal(str(local))
    except (InvalidOperation, ValueError):
        return float(amount)
    if not exact.is_finite() or exact < 0:
        return float(amount)
    return float(exact)
