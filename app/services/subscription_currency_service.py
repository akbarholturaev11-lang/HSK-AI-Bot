from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import httpx

from app.repositories.bot_setting_repo import BotSettingRepository


VISA_LOCAL_RATE_KEYS = {
    "tjs": "subscription_visa_usd_tjs_rate",
    "uzs": "subscription_visa_usd_uzs_rate",
    "rub": "subscription_visa_usd_rub_rate",
}
SUBSCRIPTION_USD_RATE_KEYS = {
    **VISA_LOCAL_RATE_KEYS,
    "cny": "subscription_usd_cny_rate",
}
VISA_AUTO_RATE_ENABLED_KEY = "subscription_visa_auto_rate_enabled"

# Editable defaults based on official rates available on 2026-06-01.
DEFAULT_VISA_LOCAL_RATES = {
    "tjs": Decimal("9.2464"),
    "uzs": Decimal("12001.94"),
    "rub": Decimal("71.0224"),
}
DEFAULT_USD_CNY_RATE = Decimal("6.80")
DEFAULT_SUBSCRIPTION_USD_RATES = {
    **DEFAULT_VISA_LOCAL_RATES,
    "cny": DEFAULT_USD_CNY_RATE,
}

LEGACY_VISA_SOMONI_RATE = DEFAULT_VISA_LOCAL_RATES["tjs"]
LOCAL_RATE_LABELS = {
    "tjs": "TJS",
    "uzs": "UZS",
    "rub": "RUB",
    "usd": "USD",
}
CARD_COUNTRY_CURRENCY = {
    "tj": "tjs",
    "uz": "uzs",
    "ru": "rub",
    "other": "usd",
}


@dataclass(frozen=True)
class CardCurrencyQuote:
    country: str
    amount: str
    currency: str
    exchange_rate: str
    source: str


def format_subscription_price(amount: int, currency: str) -> str:
    if (currency or "").strip().lower() in {"usd", "$"}:
        return f"${amount}"
    if (currency or "").strip().lower() in {"tjs", "somoni", "сомони"}:
        return f"{amount} TJS 🇹🇯"
    return f"{amount} {currency}"


def normalize_visa_price(amount: int, currency: str) -> tuple[int, str]:
    currency_key = (currency or "").strip().lower()
    if currency_key in {"somoni", "tjs", "сомони"}:
        return amount, "TJS"
    if currency_key in {"usd", "$"}:
        return amount, "USD"
    return amount, currency


class SubscriptionCurrencyService:
    def __init__(self, session):
        self.setting_repo = BotSettingRepository(session)

    async def get_rate(self, currency_code: str) -> Decimal:
        default = DEFAULT_SUBSCRIPTION_USD_RATES[currency_code]
        raw_value = await self.setting_repo.get(SUBSCRIPTION_USD_RATE_KEYS[currency_code])
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
            for currency_code in SUBSCRIPTION_USD_RATE_KEYS
        }

    async def is_auto_rate_enabled(self) -> bool:
        return await self.setting_repo.get_bool(VISA_AUTO_RATE_ENABLED_KEY, default=False)

    async def set_auto_rate_enabled(self, enabled: bool) -> None:
        await self.setting_repo.set_bool(VISA_AUTO_RATE_ENABLED_KEY, enabled)

    async def effective_rates(self) -> tuple[dict[str, Decimal], str]:
        if await self.is_auto_rate_enabled():
            live_rates = await self._fetch_live_usd_rates()
            if live_rates:
                return live_rates, "auto"
        return await self.all_rates(), "manual"

    async def live_or_manual_usd_rates(self) -> tuple[dict[str, Decimal], str]:
        live_rates = await self._fetch_live_usd_rates()
        if live_rates:
            return live_rates, "auto"
        return await self.all_rates(), "manual"

    async def set_rate(self, currency_code: str, value: Decimal) -> bool:
        if currency_code not in SUBSCRIPTION_USD_RATE_KEYS or not value.is_finite() or value <= 0:
            return False
        await self.setting_repo.set(
            SUBSCRIPTION_USD_RATE_KEYS[currency_code],
            str(value.quantize(Decimal("0.0001"))),
        )
        return True

    async def quote_card_amount(self, tjs_amount: int, country: str | None) -> CardCurrencyQuote:
        normalized_country = country if country in CARD_COUNTRY_CURRENCY else "tj"
        target_currency = CARD_COUNTRY_CURRENCY[normalized_country]
        if target_currency == "tjs":
            return CardCurrencyQuote(
                country=normalized_country,
                amount=str(int(tjs_amount)),
                currency="TJS",
                exchange_rate="1 TJS = 1 TJS",
                source="base",
            )

        rates, source = await self.effective_rates()
        usd_amount = Decimal(tjs_amount) / rates["tjs"]
        if target_currency == "usd":
            local_amount = self._format_amount(usd_amount, 2)
            exchange_rate = self._direct_tjs_rate_label(
                Decimal("1") / rates["tjs"],
                target_currency,
            )
            return CardCurrencyQuote(
                country=normalized_country,
                amount=local_amount,
                currency="USD",
                exchange_rate=exchange_rate,
                source=source,
            )

        local_amount = usd_amount * rates[target_currency]
        decimals = 0 if target_currency == "uzs" else 2
        exchange_rate = self._direct_tjs_rate_label(
            rates[target_currency] / rates["tjs"],
            target_currency,
        )
        return CardCurrencyQuote(
            country=normalized_country,
            amount=self._format_amount(local_amount, decimals),
            currency=self.rate_label(target_currency),
            exchange_rate=exchange_rate,
            source=source,
        )

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

    @classmethod
    def _direct_tjs_rate_label(cls, value: Decimal, currency_code: str) -> str:
        decimals = 4 if currency_code == "usd" else 2
        return f"1 TJS = {cls._format_amount(value, decimals)} {cls.rate_label(currency_code)}"

    async def _fetch_live_usd_rates(self) -> dict[str, Decimal] | None:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("https://open.er-api.com/v6/latest/USD")
                response.raise_for_status()
                payload = response.json()
        except Exception:
            return None

        rates = payload.get("rates") if isinstance(payload, dict) else None
        if not isinstance(rates, dict):
            return None
        try:
            result = {
                "tjs": Decimal(str(rates["TJS"])),
                "uzs": Decimal(str(rates["UZS"])),
                "rub": Decimal(str(rates["RUB"])),
            }
        except (KeyError, InvalidOperation):
            return None
        try:
            result["cny"] = Decimal(str(rates.get("CNY", DEFAULT_USD_CNY_RATE)))
        except InvalidOperation:
            result["cny"] = DEFAULT_USD_CNY_RATE
        if not all(value.is_finite() and value > 0 for value in result.values()):
            return None
        return result
