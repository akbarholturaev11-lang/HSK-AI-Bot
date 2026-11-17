"""Connection preflight: can this lava.top account really sell the configured
subscription terms? Read-only unless ``create_test_invoice`` is requested
(an unpaid invoice charges nothing). Secrets are never returned."""
from __future__ import annotations

from dataclasses import dataclass, field

from app.services.lava.client import LavaClient, LavaError, LavaProduct
from app.services.lava.config import LavaConfig
from app.services.lava.terms import LAVA_PLAN_TYPES, LAVA_TERMS, normalize_email


@dataclass
class PreflightCheck:
    code: str
    ok: bool
    detail: str = ""


@dataclass
class PreflightReport:
    checks: list[PreflightCheck] = field(default_factory=list)
    offers: list[dict] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.checks) and all(check.ok for check in self.checks)

    def as_dict(self) -> dict:
        return {"ok": self.ok, "checks": [vars(check) for check in self.checks], "offers": self.offers}


def offer_catalog(products: list[LavaProduct]) -> list[dict]:
    rows = []
    for product in products:
        for offer in product.offers:
            rows.append({
                "product_id": product.product_id, "product_title": product.title,
                "product_type": product.product_type, "offer_id": offer.offer_id,
                "offer_name": offer.name,
                "prices": [{"amount": None if price.amount is None else str(price.amount),
                            "currency": price.currency, "periodicity": price.periodicity}
                           for price in offer.prices],
            })
    return rows


def find_offer(products: list[LavaProduct], offer_id: str):
    for product in products:
        for offer in product.offers:
            if offer.offer_id == offer_id:
                return product, offer
    return None, None


def check_config_against_catalog(config: LavaConfig, products: list[LavaProduct]) -> list[PreflightCheck]:
    checks = []
    enabled = [config.terms[plan] for plan in LAVA_PLAN_TYPES if config.terms[plan].enabled]
    if config.checkout_mode != "manual_only" and not enabled:
        checks.append(PreflightCheck("terms_enabled", False, "no_enabled_term"))
    for term in enabled:
        product, offer = find_offer(products, term.offer_id)
        if offer is None:
            checks.append(PreflightCheck(f"offer_{term.plan_type}", False, "offer_not_found"))
            continue
        if product.product_type != "SUBSCRIPTION":
            checks.append(PreflightCheck(f"offer_{term.plan_type}", False, "product_not_subscription"))
            continue
        periodicity = LAVA_TERMS[term.plan_type][0]
        price = offer.price_for(config.currency, periodicity)
        if price is None:
            checks.append(PreflightCheck(f"offer_{term.plan_type}", False,
                                         f"no_{config.currency}_{periodicity}_price"))
            continue
        checks.append(PreflightCheck(f"offer_{term.plan_type}", True, f"{price.amount} {price.currency}"))
    return checks


async def run_preflight(client: LavaClient | None, config: LavaConfig, *, settings_obj,
                        test_invoice_email: str | None = None) -> PreflightReport:
    report = PreflightReport()
    report.checks.append(PreflightCheck("sales_flag", getattr(settings_obj, "LAVA_ENABLED", False) is True,
                                        "LAVA_ENABLED"))
    report.checks.append(PreflightCheck("webhook_secret", bool(getattr(settings_obj, "LAVA_WEBHOOK_SECRET", "")),
                                        "LAVA_WEBHOOK_SECRET"))
    if client is None:
        report.checks.append(PreflightCheck("api_key", False, "LAVA_API_KEY"))
        return report
    try:
        products = await client.list_products()
    except LavaError as exc:
        report.checks.append(PreflightCheck("api_access", False,
                                            "unauthorized" if exc.code == "unauthorized" else exc.code))
        return report
    report.checks.append(PreflightCheck("api_access", True, "products"))
    report.offers = offer_catalog(products)
    has_subscription = any(product.product_type == "SUBSCRIPTION" and product.offers for product in products)
    report.checks.append(PreflightCheck("subscription_product", has_subscription,
                                        "" if has_subscription else "no_subscription_product"))
    report.checks.extend(check_config_against_catalog(config, products))
    email = normalize_email(test_invoice_email) if test_invoice_email else None
    if test_invoice_email is not None:
        sellable = config.sellable_terms()
        if email is None or not sellable:
            report.checks.append(PreflightCheck("test_invoice", False, "email_or_term_missing"))
        else:
            term = sellable[0]
            try:
                created = await client.create_invoice(email=email, offer_id=term.offer_id, currency=config.currency,
                                                      periodicity=term.periodicity)
                report.checks.append(PreflightCheck("test_invoice", True, created.contract_id))
            except LavaError as exc:
                report.checks.append(PreflightCheck("test_invoice", False, exc.code))
    return report
