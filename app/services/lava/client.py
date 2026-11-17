"""Minimal lava.top Public API client (OpenAPI v1.22.0).

Rules: the API key is sent only in ``X-Api-Key`` and never logged; POST is
never retried automatically (an uncertain create may already exist on lava);
GET is idempotent and may be retried by callers. No database work happens here.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from decimal import Decimal
from urllib.parse import quote

import httpx

from app.services.lava.terms import is_uuid, money

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


class LavaError(Exception):
    """Provider failure. ``uncertain`` means the request may have taken effect."""

    def __init__(self, code: str, *, http_status: int | None = None, uncertain: bool = False):
        super().__init__(code)
        self.code = code
        self.http_status = http_status
        self.uncertain = uncertain


class LavaNotFound(LavaError):
    def __init__(self, code: str = "not_found"):
        super().__init__(code, http_status=404)


@dataclass(frozen=True)
class LavaInvoiceInfo:
    contract_id: str
    invoice_type: str | None  # INVOICE | SUBSCRIPTION_FIRST_INVOICE | SUBSCRIPTION_RENEWAL
    status: str | None  # NEW | IN_PROGRESS | COMPLETED | FAILED
    amount: Decimal | None
    currency: str | None
    parent_contract_id: str | None
    buyer_email: str | None
    subscription_status: str | None
    expired_at: str | None = None
    cancelled_at: str | None = None

    @property
    def completed(self) -> bool:
        return self.status == "COMPLETED"


@dataclass(frozen=True)
class LavaCreatedInvoice:
    contract_id: str
    payment_url: str
    amount: Decimal | None
    currency: str | None
    status: str | None


@dataclass(frozen=True)
class LavaOfferPrice:
    amount: Decimal | None
    currency: str | None
    periodicity: str | None


@dataclass(frozen=True)
class LavaOffer:
    offer_id: str
    name: str
    prices: tuple[LavaOfferPrice, ...]

    def price_for(self, currency: str, periodicity: str) -> LavaOfferPrice | None:
        for price in self.prices:
            if price.currency == currency and price.periodicity == periodicity and price.amount is not None:
                return price
        return None


@dataclass(frozen=True)
class LavaProduct:
    product_id: str
    title: str
    product_type: str | None
    offers: tuple[LavaOffer, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class LavaSubscriptionInfo:
    parent_contract_id: str
    subscription_status: str | None
    cancelled_at: str | None
    expired_at: str | None
    renewals: tuple[tuple[str, str | None], ...]  # (contract_id, status)


def _text(value, limit: int = 255) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value[:limit] if value else None


def _upper(value) -> str | None:
    text = _text(value, 40)
    return text.upper() if text else None


def parse_invoice(data) -> LavaInvoiceInfo:
    if not isinstance(data, dict) or not is_uuid(data.get("id")):
        raise LavaError("invalid_invoice_response")
    receipt = data.get("receipt") if isinstance(data.get("receipt"), dict) else {}
    buyer = data.get("buyer") if isinstance(data.get("buyer"), dict) else {}
    parent = data.get("parentInvoice") if isinstance(data.get("parentInvoice"), dict) else {}
    details = data.get("subscriptionDetails") if isinstance(data.get("subscriptionDetails"), dict) else {}
    parent_id = parent.get("id") if is_uuid(parent.get("id")) else None
    return LavaInvoiceInfo(
        contract_id=data["id"].lower(),
        invoice_type=_upper(data.get("type")),
        status=_upper(data.get("status")),
        amount=money(receipt.get("amount")),
        currency=_upper(receipt.get("currency")),
        parent_contract_id=parent_id.lower() if parent_id else None,
        buyer_email=_text(buyer.get("email"), 254),
        subscription_status=_upper(data.get("subscriptionStatus")),
        expired_at=_text(details.get("expiredAt"), 40),
        cancelled_at=_text(details.get("cancelledAt"), 40),
    )


def parse_products(data) -> list[LavaProduct]:
    items = data.get("items") if isinstance(data, dict) else None
    products: list[LavaProduct] = []
    for item in items if isinstance(items, list) else []:
        product = item.get("data") if isinstance(item, dict) and isinstance(item.get("data"), dict) else item
        if not isinstance(product, dict) or not is_uuid(product.get("id")):
            continue
        offers = []
        for offer in product.get("offers") or []:
            if not isinstance(offer, dict) or not is_uuid(offer.get("id")):
                continue
            prices = tuple(
                LavaOfferPrice(
                    amount=money(price.get("amount")),
                    currency=_upper(price.get("currency")),
                    periodicity=_upper(price.get("periodicity")),
                )
                for price in offer.get("prices") or [] if isinstance(price, dict)
            )
            offers.append(LavaOffer(offer_id=offer["id"].lower(), name=_text(offer.get("name"), 120) or "", prices=prices))
        products.append(LavaProduct(
            product_id=product["id"].lower(),
            title=_text(product.get("title"), 160) or "",
            product_type=_upper(product.get("type")),
            offers=tuple(offers),
        ))
    return products


def parse_subscription(data) -> LavaSubscriptionInfo:
    if not isinstance(data, dict) or not is_uuid(data.get("id")):
        raise LavaError("invalid_subscription_response")
    renewals = []
    for row in data.get("recurrentPayments") or []:
        if isinstance(row, dict) and is_uuid(row.get("id")):
            renewals.append((row["id"].lower(), _upper(row.get("status"))))
    return LavaSubscriptionInfo(
        parent_contract_id=data["id"].lower(),
        subscription_status=_upper(data.get("subscriptionStatus")),
        cancelled_at=_text(data.get("cancelledAt"), 40),
        expired_at=_text(data.get("expiredAt"), 40),
        renewals=tuple(renewals),
    )


class LavaClient:
    def __init__(self, *, api_key: str, base_url: str = "https://gate.lava.top",
                 transport: httpx.AsyncBaseTransport | None = None,
                 timeout: httpx.Timeout = DEFAULT_TIMEOUT):
        if not api_key:
            raise LavaError("api_key_missing")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._transport = transport
        self._timeout = timeout

    async def _request(self, method: str, path: str, *, params=None, json_body=None,
                       retries: int = 0) -> httpx.Response:
        attempt = 0
        while True:
            try:
                async with httpx.AsyncClient(base_url=self._base_url, transport=self._transport,
                                             timeout=self._timeout) as client:
                    response = await client.request(
                        method, path, params=params, json=json_body,
                        headers={"X-Api-Key": self._api_key, "Accept": "application/json"},
                    )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                # A POST may have reached lava; callers must treat it as uncertain.
                if method == "GET" and attempt < retries:
                    attempt += 1
                    await asyncio.sleep(0.5 * attempt)
                    continue
                logger.warning("lava.top %s %s transport failure: %s", method, path.split("?")[0],
                               type(exc).__name__)
                raise LavaError("provider_unreachable", uncertain=method != "GET") from None
            if response.status_code >= 500 or response.status_code == 429:
                if method == "GET" and attempt < retries:
                    attempt += 1
                    await asyncio.sleep(0.5 * attempt)
                    continue
                logger.warning("lava.top %s %s -> %s", method, path.split("?")[0], response.status_code)
                raise LavaError("provider_unavailable", http_status=response.status_code,
                                uncertain=method != "GET")
            return response

    @staticmethod
    def _json(response: httpx.Response):
        try:
            return response.json()
        except ValueError:
            raise LavaError("invalid_json", http_status=response.status_code) from None

    @staticmethod
    def _raise_for_client_error(response: httpx.Response) -> None:
        if response.status_code == 404:
            raise LavaNotFound()
        if response.status_code in (401, 403):
            raise LavaError("unauthorized", http_status=response.status_code)
        if response.status_code >= 400:
            raise LavaError("rejected", http_status=response.status_code)

    async def create_invoice(self, *, email: str, offer_id: str, currency: str, periodicity: str,
                             buyer_language: str = "RU", success_url: str | None = None,
                             failure_url: str | None = None, cancel_url: str | None = None,
                             promo_code: str | None = None) -> LavaCreatedInvoice:
        body = {
            "email": email, "offerId": offer_id, "currency": currency,
            "periodicity": periodicity, "buyerLanguage": buyer_language,
        }
        for key, value in (("successful_return_url", success_url), ("failure_return_url", failure_url),
                           ("cancel_return_url", cancel_url), ("promoCode", promo_code)):
            if value:
                body[key] = value
        response = await self._request("POST", "/api/v3/invoice", json_body=body)
        self._raise_for_client_error(response)
        data = self._json(response)
        contract_id = data.get("id") if isinstance(data, dict) else None
        payment_url = data.get("paymentUrl") if isinstance(data, dict) else None
        if not is_uuid(contract_id) or not isinstance(payment_url, str) or not payment_url.startswith("https://"):
            # Created but unusable: the contract may exist, so this is uncertain.
            raise LavaError("invalid_create_response", http_status=response.status_code, uncertain=True)
        total = data.get("amountTotal") if isinstance(data.get("amountTotal"), dict) else {}
        return LavaCreatedInvoice(
            contract_id=contract_id.lower(), payment_url=payment_url,
            amount=money(total.get("amount")), currency=_upper(total.get("currency")),
            status=_text(data.get("status"), 32),
        )

    async def get_invoice(self, contract_id: str) -> LavaInvoiceInfo:
        if not is_uuid(contract_id):
            raise LavaError("invalid_contract_id")
        response = await self._request("GET", f"/api/v2/invoices/{quote(contract_id)}", retries=1)
        self._raise_for_client_error(response)
        return parse_invoice(self._json(response))

    async def list_products(self, *, max_pages: int = 5) -> list[LavaProduct]:
        products: list[LavaProduct] = []
        params = {"showAllSubscriptionPeriods": "true", "feedVisibility": "ALL"}
        path = "/api/v2/products"
        for _ in range(max_pages):
            response = await self._request("GET", path, params=params, retries=1)
            self._raise_for_client_error(response)
            data = self._json(response)
            products.extend(parse_products(data))
            next_page = data.get("nextPage") if isinstance(data, dict) else None
            if not isinstance(next_page, str) or not next_page.startswith(self._base_url + "/"):
                break
            path, params = next_page[len(self._base_url):], None
        return products

    async def get_subscription(self, parent_contract_id: str) -> LavaSubscriptionInfo:
        if not is_uuid(parent_contract_id):
            raise LavaError("invalid_contract_id")
        response = await self._request("GET", f"/api/v1/subscriptions/{quote(parent_contract_id)}", retries=1)
        self._raise_for_client_error(response)
        return parse_subscription(self._json(response))

    async def list_subscription_ids(self, *, begin_date: str, page: int = 1, size: int = 50) -> tuple[list[str], int]:
        response = await self._request("GET", "/api/v1/subscriptions", params={
            "beginDate": begin_date, "page": page, "size": size,
        }, retries=1)
        self._raise_for_client_error(response)
        data = self._json(response)
        items = data.get("items") if isinstance(data, dict) else None
        ids = [row["id"].lower() for row in items or [] if isinstance(row, dict) and is_uuid(row.get("id"))]
        pages = data.get("pages") if isinstance(data, dict) and isinstance(data.get("pages"), int) else 1
        return ids, pages

    async def cancel_subscription(self, *, parent_contract_id: str, email: str) -> None:
        if not is_uuid(parent_contract_id):
            raise LavaError("invalid_contract_id")
        response = await self._request("DELETE", "/api/v1/subscriptions", params={
            "contractId": parent_contract_id, "email": email,
        })
        self._raise_for_client_error(response)
