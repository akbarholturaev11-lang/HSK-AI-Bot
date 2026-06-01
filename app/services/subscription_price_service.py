from dataclasses import dataclass

from app.repositories.subscription_price_repo import SubscriptionPriceRepository
from app.services.subscription_currency_service import normalize_visa_price


PAYMENT_METHODS = ("visa", "alipay", "wechat")
PLANS = ("10_days", "1_month")

DEFAULT_SUBSCRIPTION_PRICES: dict[tuple[str, str], tuple[int, str]] = {
    ("visa", "10_days"): (3, "USD"),
    ("visa", "1_month"): (10, "USD"),
    ("alipay", "10_days"): (29, "¥"),
    ("alipay", "1_month"): (66, "¥"),
    ("wechat", "10_days"): (29, "¥"),
    ("wechat", "1_month"): (66, "¥"),
}


@dataclass(frozen=True)
class SubscriptionPriceValue:
    payment_method: str
    plan_type: str
    amount: int
    currency: str


class SubscriptionPriceService:
    def __init__(self, session):
        self.session = session
        self.repo = SubscriptionPriceRepository(session)

    def normalize_method(self, payment_method: str | None) -> str:
        return payment_method if payment_method in PAYMENT_METHODS else "visa"

    async def get_price(self, payment_method: str | None, plan_type: str) -> SubscriptionPriceValue | None:
        method = self.normalize_method(payment_method)
        if plan_type not in PLANS:
            return None

        price = await self.repo.get(method, plan_type)
        if price:
            amount, currency = self._normalize_price(method, price.amount, price.currency)
            return SubscriptionPriceValue(method, plan_type, amount, currency)

        default = DEFAULT_SUBSCRIPTION_PRICES.get((method, plan_type))
        if not default:
            return None
        amount, currency = default
        return SubscriptionPriceValue(method, plan_type, amount, currency)

    async def set_price(
        self,
        *,
        payment_method: str,
        plan_type: str,
        amount: int,
        updated_by_telegram_id: int | None = None,
    ) -> SubscriptionPriceValue | None:
        method = self.normalize_method(payment_method)
        if plan_type not in PLANS or amount <= 0:
            return None

        currency = "¥" if method in {"alipay", "wechat"} else "USD"
        price = await self.repo.set_price(
            payment_method=method,
            plan_type=plan_type,
            amount=amount,
            currency=currency,
            updated_by_telegram_id=updated_by_telegram_id,
        )
        return SubscriptionPriceValue(method, plan_type, price.amount, price.currency)

    async def all_prices(self) -> list[SubscriptionPriceValue]:
        rows = {
            (row.payment_method, row.plan_type): self._normalize_price(
                row.payment_method,
                row.amount,
                row.currency,
            )
            for row in await self.repo.list_all()
        }
        result = []
        for method in PAYMENT_METHODS:
            for plan in PLANS:
                amount, currency = rows.get((method, plan), DEFAULT_SUBSCRIPTION_PRICES[(method, plan)])
                result.append(SubscriptionPriceValue(method, plan, amount, currency))
        return result

    @staticmethod
    def _normalize_price(method: str, amount: int, currency: str) -> tuple[int, str]:
        if method == "visa":
            return normalize_visa_price(amount, currency)
        return amount, currency
