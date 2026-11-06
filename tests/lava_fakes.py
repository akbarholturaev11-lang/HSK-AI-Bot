"""In-memory lava.top API double (httpx.MockTransport) and helpers for tests."""
from __future__ import annotations

import json
import uuid
from types import SimpleNamespace

import httpx

from app.services.lava.client import LavaClient
from app.services.lava.events import LavaRuntime

OFFER_ID = "11111111-2222-3333-4444-555555555555"
PRODUCT_ID = "99999999-8888-7777-6666-555555555555"
API_KEY = "test-api-key"
WEBHOOK_SECRET = "test-webhook-secret"


def lava_settings(**overrides):
    values = dict(
        LAVA_ENABLED=True, LAVA_API_KEY=API_KEY, LAVA_WEBHOOK_SECRET=WEBHOOK_SECRET,
        LAVA_API_BASE="https://gate.lava.top", LAVA_PROCESSING_PAUSED=False,
        LAVA_WEBHOOK_ALLOWED_IPS="", LAVA_RECONCILE_ENABLED=True,
        PUBLIC_SITE_URL="https://hsk.example", MINI_APP_BASE_URL="https://hsk.example/course-v3.html",
    )
    values.update(overrides)
    return SimpleNamespace(**values)


class FakeLava:
    def __init__(self):
        self.invoices: dict[str, dict] = {}
        self.subscriptions: dict[str, dict] = {}
        self.calls: list[tuple[str, str]] = []
        self.unavailable = False
        self.prices = {
            "MONTHLY": "10.00", "PERIOD_90_DAYS": "27.00", "PERIOD_180_DAYS": "50.00", "PERIOD_YEAR": "90.00",
        }
        self.product_type = "SUBSCRIPTION"
        self.promo_codes: dict[str, int] = {}  # code -> percent known to the fake cabinet
        self.last_create_body: dict | None = None

    # -- helpers used by tests -------------------------------------------
    def complete(self, contract_id: str, *, amount=None, currency=None):
        invoice = self.invoices[contract_id]
        invoice["status"] = "COMPLETED"
        if amount is not None:
            invoice["amount"] = amount
        if currency is not None:
            invoice["currency"] = currency

    def add_external(self, *, amount="10.00", currency="USD", email="x@example.com") -> str:
        contract_id = str(uuid.uuid4())
        self.invoices[contract_id] = dict(type="SUBSCRIPTION_FIRST_INVOICE", status="COMPLETED",
                                          amount=amount, currency=currency, email=email, parent=None)
        return contract_id

    def add_renewal(self, parent_id: str, *, status="COMPLETED") -> str:
        contract_id = str(uuid.uuid4())
        parent = self.invoices[parent_id]
        self.invoices[contract_id] = dict(type="SUBSCRIPTION_RENEWAL", status=status, amount=parent["amount"],
                                          currency=parent["currency"], email=parent["email"], parent=parent_id)
        self.subscriptions.setdefault(parent_id, {"renewals": [], "status": "ACTIVE"})["renewals"].append(contract_id)
        return contract_id

    # -- transport --------------------------------------------------------
    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls.append((request.method, request.url.path))
        if request.headers.get("X-Api-Key") != API_KEY:
            return httpx.Response(401, json={"error": "unauthorized"})
        if self.unavailable:
            return httpx.Response(503, json={"error": "down"})
        path = request.url.path
        if request.method == "POST" and path == "/api/v3/invoice":
            body = json.loads(request.content)
            self.last_create_body = body
            contract_id = str(uuid.uuid4())
            amount = self.prices.get(body.get("periodicity"), "10.00")
            if body.get("promoCode"):
                percent = self.promo_codes.get(body["promoCode"])
                if percent is None:
                    return httpx.Response(400, json={"error": "promo code not found"})
                amount = "%.2f" % (float(amount) * (100 - percent) / 100)
            self.invoices[contract_id] = dict(
                type="SUBSCRIPTION_FIRST_INVOICE", status="NEW", amount=amount, currency=body["currency"],
                email=body["email"], parent=None, offer=body["offerId"], periodicity=body.get("periodicity"))
            return httpx.Response(201, json={
                "id": contract_id, "status": "new",
                "amountTotal": {"amount": float(amount), "currency": body["currency"]},
                "paymentUrl": f"https://pay.lava.top/{contract_id}",
            })
        if request.method == "GET" and path.startswith("/api/v2/invoices/"):
            contract_id = path.rsplit("/", 1)[1]
            invoice = self.invoices.get(contract_id)
            if invoice is None:
                return httpx.Response(404, json={"error": "not found"})
            return httpx.Response(200, json={
                "id": contract_id, "type": invoice["type"], "status": invoice["status"],
                "receipt": {"amount": float(invoice["amount"]), "currency": invoice["currency"], "fee": 0},
                "buyer": {"email": invoice["email"]},
                "parentInvoice": {"id": invoice["parent"]} if invoice["parent"] else None,
            })
        if request.method == "GET" and path == "/api/v2/products":
            return httpx.Response(200, json={"items": [{"type": "PRODUCT", "data": {
                "id": PRODUCT_ID, "title": "HSK AI Pro", "type": self.product_type,
                "offers": [{"id": OFFER_ID, "name": "Pro", "prices": [
                    {"amount": float(amount), "currency": "USD", "periodicity": periodicity}
                    for periodicity, amount in self.prices.items()
                ]}],
            }}], "nextPage": None})
        if request.method == "GET" and path.startswith("/api/v1/subscriptions/"):
            parent_id = path.rsplit("/", 1)[1]
            sub = self.subscriptions.get(parent_id, {"renewals": [], "status": "ACTIVE"})
            return httpx.Response(200, json={
                "id": parent_id, "subscriptionStatus": sub["status"],
                "recurrentPayments": [{"id": rid, "status": self.invoices[rid]["status"]} for rid in sub["renewals"]],
            })
        if request.method == "DELETE" and path == "/api/v1/subscriptions":
            parent_id = request.url.params.get("contractId")
            if parent_id not in self.invoices:
                return httpx.Response(404, json={"error": "nf"})
            self.subscriptions.setdefault(parent_id, {"renewals": [], "status": "ACTIVE"})["status"] = "CANCELLED"
            return httpx.Response(204)
        return httpx.Response(404, json={"error": "unknown route"})

    def client(self) -> LavaClient:
        return LavaClient(api_key=API_KEY, transport=httpx.MockTransport(self.handler))


class RecordingNotifier:
    def __init__(self):
        self.alerts: list[tuple[str, int | None]] = []
        self.notices: list[tuple[int | None, str]] = []

    async def admin_alert(self, code, *, invoice_id=None, detail=None, throttle_seconds=0):
        self.alerts.append((code, invoice_id))

    async def user_notice(self, user, kind, *, end_date=None):
        self.notices.append((getattr(user, "id", None), kind))


def make_runtime(sessions, fake: FakeLava, **settings_overrides) -> LavaRuntime:
    return LavaRuntime(settings=lava_settings(**settings_overrides), session_factory=sessions,
                       notifier=RecordingNotifier(), client_factory=fake.client)


def payment_webhook(event_type: str, contract_id: str, *, parent: str | None = None, amount="10.00",
                    currency="USD", email="buyer@example.com", status="completed") -> bytes:
    body = {
        "eventType": event_type, "product": {"id": PRODUCT_ID, "title": "HSK AI Pro"},
        "buyer": {"email": email}, "contractId": contract_id, "amount": float(amount),
        "currency": currency, "timestamp": "2026-11-06T10:00:00Z", "status": status, "errorMessage": "",
    }
    if parent:
        body["parentContractId"] = parent
    return json.dumps(body).encode()


def refund_webhook(*, amount="10.00", currency="USD", email="buyer@example.com", refund_type="full",
                   event_type="refund.success") -> bytes:
    event_id = str(uuid.uuid4())
    return json.dumps({
        "event_id": event_id, "event_type": event_type, "created_at": "2026-11-07T10:00:00Z",
        "data": {"refund_id": event_id, "chargeback_id": event_id, "refund_type": refund_type,
                 "initiator": "creator", "amount": float(amount), "currency": currency,
                 "product": {"product_name": "HSK AI Pro", "product_id": PRODUCT_ID,
                             "product_type": "SUBSCRIPTION", "tier_id": OFFER_ID},
                 "customer_email": email, "subscription_cancelled": False},
    }).encode()
