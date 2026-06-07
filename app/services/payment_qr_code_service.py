from app.repositories.payment_qr_code_repo import PaymentQrCodeRepository
from app.services.subscription_price_service import DEFAULT_SUBSCRIPTION_PRICES


QR_PAYMENT_METHODS = {"alipay", "wechat"}
SUBSCRIPTION_QR_SCOPE = "subscription"
SUBSCRIPTION_DISCOUNT_20_QR_SCOPE = "subscription_20"
ADMIN_CAMPAIGN_QR_SCOPE_PREFIX = "admin_campaign:"


class PaymentQrCodeService:
    def __init__(self, session):
        self.session = session
        self.repo = PaymentQrCodeRepository(session)

    @staticmethod
    def admin_campaign_scope(campaign_id: int) -> str:
        return f"{ADMIN_CAMPAIGN_QR_SCOPE_PREFIX}{campaign_id}"

    @staticmethod
    def is_qr_method(payment_method: str | None) -> bool:
        return payment_method in QR_PAYMENT_METHODS

    @staticmethod
    def is_default_subscription_amount(
        *,
        payment_method: str,
        plan_type: str,
        amount: int,
        currency: str,
        discount_percent: int = 0,
    ) -> bool:
        default = DEFAULT_SUBSCRIPTION_PRICES.get((payment_method, plan_type))
        if not default:
            return False
        default_amount, default_currency = default
        if discount_percent > 0:
            default_amount = int(round(default_amount * (100 - discount_percent) / 100))
        return amount == default_amount and currency == default_currency

    @staticmethod
    def checkout_scope(
        *,
        discount_source: str,
        discount_percent: int,
        discount_campaign_id: int | None,
    ) -> str | None:
        if discount_source == "admin_campaign" and discount_campaign_id:
            return PaymentQrCodeService.admin_campaign_scope(discount_campaign_id)
        if discount_source in {"referral", "feedback_price_offer"} and discount_percent == 20:
            return SUBSCRIPTION_DISCOUNT_20_QR_SCOPE
        if discount_source in {None, "", "none"} and discount_percent == 0:
            return SUBSCRIPTION_QR_SCOPE
        return None

    async def get_file_id(
        self,
        *,
        scope: str,
        payment_method: str,
        plan_type: str,
        amount: int,
        currency: str,
    ) -> str | None:
        qr_code = await self.repo.get(
            scope=scope,
            payment_method=payment_method,
            plan_type=plan_type,
            amount=amount,
            currency=currency,
        )
        return qr_code.file_id if qr_code else None

    async def save_qr_codes(
        self,
        items: list[dict],
        *,
        created_by_telegram_id: int | None = None,
    ) -> None:
        for item in items:
            file_id = str(item.get("file_id") or "").strip()
            if not file_id:
                continue
            await self.repo.set_qr_code(
                scope=str(item["scope"]),
                payment_method=str(item["payment_method"]),
                plan_type=str(item["plan_type"]),
                amount=int(item["amount"]),
                currency=str(item["currency"]),
                file_id=file_id,
                created_by_telegram_id=created_by_telegram_id,
            )

    @staticmethod
    def method_label(payment_method: str) -> str:
        return {
            "alipay": "Alipay",
            "wechat": "WeChat",
        }.get(payment_method, payment_method)
