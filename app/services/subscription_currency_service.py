from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from app.repositories.bot_setting_repo import BotSettingRepository


VISA_LOCAL_RATE_KEYS = {
    "tjs": "subscription_visa_usd_tjs_rate",
    "uzs": "subscription_visa_usd_uzs_rate",
    "rub": "subscription_visa_usd_rub_rate",
}

# Editable defaults based on official rates available on 2026-06-01.
DEFAULT_VISA_LOCAL_RATES = {
    "tjs": Decimal("9.2464"),
    "uzs": Decimal("12001.94"),
    "rub": Decimal("71.0224"),
}

LEGACY_VISA_SOMONI_RATE = DEFAULT_VISA_LOCAL_RATES["tjs"]
LOCAL_RATE_LABELS = {
    "tjs": "TJS",
    "uzs": "UZS",
    "rub": "RUB",
}


def format_subscription_price(amount: int, currency: str) -> str:
    if (currency or "").strip().lower() in {"usd", "$"}:
        return f"${amount}"
    return f"{amount} {currency}"


def normalize_visa_price(amount: int, currency: str) -> tuple[int, str]:
    currency_key = (currency or "").strip().lower()
    if currency_key in {"somoni", "tjs", "сомони"}:
        converted = (Decimal(amount) / LEGACY_VISA_SOMONI_RATE).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        )
        return max(int(converted), 1), "USD"
    if currency_key in {"usd", "$"}:
        return amount, "USD"
    return amount, currency


class SubscriptionCurrencyService:
    def __init__(self, session):
        self.setting_repo = BotSettingRepository(session)

    async def get_rate(self, currency_code: str) -> Decimal:
        default = DEFAULT_VISA_LOCAL_RATES[currency_code]
        raw_value = await self.setting_repo.get(VISA_LOCAL_RATE_KEYS[currency_code])
        if not raw_value:
            return default
        try:
            value = Decimal(raw_value)
        except InvalidOperation:
            return default
        return value if value.is_finite() and value > 0 else default

    async def all_rates(self) -> dict[str, Decimal]:
        return {
            currency_code: await self.get_rate(currency_code)
            for currency_code in VISA_LOCAL_RATE_KEYS
        }

    async def set_rate(self, currency_code: str, value: Decimal) -> bool:
        if currency_code not in VISA_LOCAL_RATE_KEYS or not value.is_finite() or value <= 0:
            return False
        await self.setting_repo.set(
            VISA_LOCAL_RATE_KEYS[currency_code],
            str(value.quantize(Decimal("0.0001"))),
        )
        return True

    async def format_local_equivalents(self, usd_amount: int) -> str:
        rates = await self.all_rates()
        return " · ".join(
            (
                f"{self._format_amount(Decimal(usd_amount) * rates['tjs'], 2)} TJS",
                f"{self._format_amount(Decimal(usd_amount) * rates['uzs'], 0)} UZS",
                f"{self._format_amount(Decimal(usd_amount) * rates['rub'], 2)} RUB",
            )
        )

    async def format_local_equivalent_lines(self, usd_amount: int) -> str:
        rates = await self.all_rates()
        return "\n".join(
            (
                f"= {self._format_amount(Decimal(usd_amount) * rates['tjs'], 2)} TJS 🇹🇯",
                f"= {self._format_amount(Decimal(usd_amount) * rates['uzs'], 0)} UZS 🇺🇿",
                f"= {self._format_amount(Decimal(usd_amount) * rates['rub'], 2)} RUB 🇷🇺",
            )
        )

    @staticmethod
    def rate_label(currency_code: str) -> str:
        return LOCAL_RATE_LABELS.get(currency_code, currency_code.upper())

    @staticmethod
    def format_rate(currency_code: str, value: Decimal) -> str:
        decimals = 2 if currency_code == "uzs" else 4
        return SubscriptionCurrencyService._format_amount(value, decimals)

    @staticmethod
    def _format_amount(value: Decimal, decimals: int) -> str:
        quantizer = Decimal("1") if decimals == 0 else Decimal("1." + ("0" * decimals))
        rounded = value.quantize(quantizer, rounding=ROUND_HALF_UP)
        return f"{rounded:,.{decimals}f}".replace(",", " ")
