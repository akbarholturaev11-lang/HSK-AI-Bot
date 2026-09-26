"""Admin Mini App uchun chuqur moliyaviy va biznes statistikasi.

Bu xizmat yangi admin panel (admin.html) uchun 3 ta davr (7 kun / 30 kun / to'liq)
bo'yicha bir xil tuzilishdagi hisobotlarni quradi:

- Kuzatilgan net = obuna tushumi + qo'lda foyda − model-cost estimate − qo'lda rasxod
- ARPU / ARPPU
- Obuna yangilash va hozirgi paid holati
- Manba → pullik (qaysi manba real pul olib keladi)

Mavjud xizmatlar (PortfolioService, AdminMiniAppService) o'zgartirilmaydi —
bu fayl faqat o'qish (read-only) hisob-kitob qiladi.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select

from app.db.models.ai_usage import AIUsageEvent
from app.db.models.payment import Payment
from app.db.models.portfolio import PortfolioTransaction
from app.db.models.subscription_entry_event import SubscriptionEntryEvent
from app.db.models.user import User
from app.services.subscription_currency_service import (
    DEFAULT_USD_CNY_RATE,
    DEFAULT_VISA_LOCAL_RATES,
)
from app.services.subscription_entry_analytics_service import (
    SubscriptionEntryAnalyticsService,
)


STATS_TZ = ZoneInfo("Asia/Shanghai")

# Portfel (PortfolioService.amount_to_usd) bilan bir xil kurslar — bu modul
# AI/OpenAI zanjirini tortmasligi uchun to'g'ridan-to'g'ri shu yerda hisoblanadi.
_USD_TO_SOMONI = float(DEFAULT_VISA_LOCAL_RATES["tjs"])
_USD_TO_YUAN = float(DEFAULT_USD_CNY_RATE)

_CLIENT_CHANNELS = {
    "miniapp": {
        "label": "Mini App / bot",
        "note": "Telegram Mini App va bot ichidagi canonical checkout",
    },
    "android": {
        "label": "Android",
        "note": "Native Android -> canonical APK checkout",
    },
    "desktop": {
        "label": "Desktop",
        "note": "Native desktop -> canonical checkout adapter",
    },
    "unknown": {
        "label": "Noma'lum",
        "note": "Paymentdan oldin entry source topilmadi",
    },
}
_CLIENT_ORDER = ("miniapp", "android", "desktop", "unknown")


def _amount_to_usd(amount, currency: str | None) -> float | None:
    """To'lov summasini USDga aylantiradi (portfel bilan bir xil mantiq)."""
    key = (currency or "").strip().lower()
    if key in {"somoni", "tjs", "сомони"}:
        return float(amount) / _USD_TO_SOMONI
    if key in {"usd", "$"}:
        return float(amount)
    if key in {"¥", "cny", "yuan", "юань"}:
        return float(amount) / _USD_TO_YUAN
    return None


def _usd(value: float) -> str:
    try:
        return f"${float(value or 0):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def _pct(part: float, total: float) -> float:
    return round(part / total * 100, 1) if total and total > 0 else 0.0


def _dt(value: datetime | None) -> str:
    if not value:
        return "—"
    try:
        return value.astimezone(STATS_TZ).strftime("%d.%m.%Y %H:%M")
    except Exception:
        return str(value)


@dataclass
class _ApprovedPayment:
    user_id: int
    usd: float
    at: datetime
    submitted_at: datetime
    priced: bool
    is_renewal: bool
    source: str


class AdminFinanceStatsService:
    def __init__(self, session):
        self.session = session

    async def build(self) -> dict:
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        approved = await self._load_approved_payments()
        source_events_by_user = await self._source_events_by_user()

        total_users = await self._count_users()
        paid_ever = len({p.user_id for p in approved})
        active_paid_now = await self._active_paid_now(
            now,
            telegram_ids={p.user_id for p in approved},
        )
        renewed_ever = await self._renewed_ever_count()

        periods = []
        for key, title, note, since in (
            ("weekly", "Haftalik", "Oxirgi 7 kun", week_ago),
            ("monthly", "Oylik", "Oxirgi 30 kun", month_ago),
            ("all_time", "To'liq", "Butun davr (boshidan)", None),
        ):
            periods.append(
                await self._period(
                    key=key,
                    title=title,
                    note=note,
                    since=since,
                    now=now,
                    approved=approved,
                    source_events_by_user=source_events_by_user,
                    total_users=total_users,
                    active_paid_now=active_paid_now,
                    paid_ever=paid_ever,
                    renewed_ever=renewed_ever,
                )
            )

        return {
            "ok": True,
            "generated_at": _dt(now),
            "tz": "Asia/Shanghai",
            "periods": periods,
        }

    # ---- ma'lumot yig'ish -------------------------------------------------

    async def _load_approved_payments(self) -> list[_ApprovedPayment]:
        rows = (
            await self.session.execute(
                select(
                    Payment.user_telegram_id,
                    Payment.amount,
                    Payment.currency,
                    Payment.base_amount,
                    Payment.reviewed_at,
                    Payment.submitted_at,
                    Payment.source,
                ).where(Payment.payment_status == "approved")
            )
        ).all()

        items: list[_ApprovedPayment] = []
        for user_id, amount, currency, base_amount, reviewed_at, submitted_at, source in rows:
            usd = _amount_to_usd(amount, currency)
            if usd is None and base_amount:
                usd = _amount_to_usd(base_amount, "TJS")
            priced = usd is not None
            if not priced:
                usd = 0.0
            at = reviewed_at or submitted_at
            if at is None or submitted_at is None:
                continue
            if at.tzinfo is None:
                at = at.replace(tzinfo=timezone.utc)
            if submitted_at.tzinfo is None:
                submitted_at = submitted_at.replace(tzinfo=timezone.utc)
            items.append(
                _ApprovedPayment(
                    user_id=int(user_id),
                    usd=float(usd),
                    at=at,
                    submitted_at=submitted_at,
                    priced=priced,
                    is_renewal=False,
                    source=str(source or "telegram_bot"),
                )
            )

        # Vaqt bo'yicha tartiblab, har bir foydalanuvchining 2-chi+ to'lovini
        # "yangilash" (renewal) deb belgilaymiz.
        items.sort(key=lambda p: p.at)
        seen: set[int] = set()
        for p in items:
            if p.user_id in seen:
                p.is_renewal = True
            seen.add(p.user_id)
        return items

    async def _source_events_by_user(self) -> dict[int, list[tuple[datetime, str]]]:
        """Return each user's subscription entries in chronological order."""
        rows = (
            await self.session.execute(
                select(
                    SubscriptionEntryEvent.telegram_id,
                    SubscriptionEntryEvent.source,
                    SubscriptionEntryEvent.created_at,
                ).order_by(SubscriptionEntryEvent.created_at.asc())
            )
        ).all()
        result: dict[int, list[tuple[datetime, str]]] = {}
        for telegram_id, source, created in rows:
            if not created:
                continue
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            result.setdefault(int(telegram_id), []).append(
                (created, source or "unknown")
            )
        return result

    async def _count_users(self, *conditions) -> int:
        stmt = select(func.count()).select_from(User)
        if conditions:
            stmt = stmt.where(*conditions)
        return (await self.session.execute(stmt)).scalar() or 0

    async def _active_paid_now(self, now: datetime, *, telegram_ids: set[int]) -> int:
        if not telegram_ids:
            return 0
        return await self._count_users(
            User.telegram_id.in_(telegram_ids),
            User.payment_status == "approved",
            User.status == "active",
            User.end_date.is_not(None),
            User.end_date > now,
        )

    async def _renewed_ever_count(self) -> int:
        """≥2 marta tasdiqlangan to'lov qilgan (kamida 1 marta yangilagan) foydalanuvchilar."""
        sub = (
            select(Payment.user_telegram_id)
            .where(Payment.payment_status == "approved")
            .group_by(Payment.user_telegram_id)
            .having(func.count() >= 2)
        ).subquery()
        return (await self.session.execute(select(func.count()).select_from(sub))).scalar() or 0

    async def _ai_cost_usd(self, since: datetime | None) -> float:
        stmt = select(func.coalesce(func.sum(AIUsageEvent.cost_usd), 0.0))
        if since is not None:
            stmt = stmt.where(AIUsageEvent.created_at >= since)
        return float((await self.session.execute(stmt)).scalar() or 0.0)

    async def _ai_usage_breakdown(self, since: datetime | None) -> list[dict]:
        stmt = select(
            AIUsageEvent.model, AIUsageEvent.billing_tier,
            func.count().label("requests"),
            func.sum(AIUsageEvent.total_tokens).label("tokens"),
            func.sum(AIUsageEvent.cost_usd).label("cost"),
        ).group_by(AIUsageEvent.model, AIUsageEvent.billing_tier).order_by(
            AIUsageEvent.model, AIUsageEvent.billing_tier
        )
        if since is not None:
            stmt = stmt.where(AIUsageEvent.created_at >= since)
        labels = {
            "free": "Bepul", "paid_estimate": "Pullik taxmin",
            "legacy_estimate": "Eski taxmin — tarif tasdiqlanmagan",
            "unpriced": "Narxi noma'lum",
        }
        return [
            {"model": row.model, "billing_tier": row.billing_tier,
             "label": labels.get(row.billing_tier, "Tarif noma'lum"),
             "requests": int(row.requests), "tokens": int(row.tokens or 0),
             "cost_usd": float(row.cost or 0), "cost_text": f"${float(row.cost or 0):,.6f}"}
            for row in (await self.session.execute(stmt)).all()
        ]

    async def _expense_usd(self, since: datetime | None) -> float:
        stmt = select(func.coalesce(func.sum(PortfolioTransaction.amount_usd), 0.0)).where(
            PortfolioTransaction.transaction_type == "expense"
        )
        if since is not None:
            stmt = stmt.where(PortfolioTransaction.created_at >= since)
        return float((await self.session.execute(stmt)).scalar() or 0.0)

    async def _manual_profit_usd(self, since: datetime | None) -> float:
        stmt = select(func.coalesce(func.sum(PortfolioTransaction.amount_usd), 0.0)).where(
            PortfolioTransaction.transaction_type == "profit",
            PortfolioTransaction.source == "manual_profit",
        )
        if since is not None:
            stmt = stmt.where(PortfolioTransaction.created_at >= since)
        return float((await self.session.execute(stmt)).scalar() or 0.0)

    # ---- davr hisoboti ----------------------------------------------------

    async def _period(
        self,
        *,
        key: str,
        title: str,
        note: str,
        since: datetime | None,
        now: datetime,
        approved: list[_ApprovedPayment],
        source_events_by_user: dict[int, list[tuple[datetime, str]]],
        total_users: int,
        active_paid_now: int,
        paid_ever: int,
        renewed_ever: int,
    ) -> dict:
        in_period = [p for p in approved if since is None or p.at >= since]

        revenue_usd = sum(p.usd for p in in_period if p.priced)
        unpriced_payments = len([p for p in in_period if not p.priced])
        ai_cost_usd = await self._ai_cost_usd(since)
        ai_usage = await self._ai_usage_breakdown(since)
        expense_usd = await self._expense_usd(since)
        manual_profit_usd = await self._manual_profit_usd(since)
        net_usd = revenue_usd + manual_profit_usd - ai_cost_usd - expense_usd

        approved_count = len(in_period)
        paying_users = len({p.user_id for p in in_period})
        new_paying = len([p for p in in_period if not p.is_renewal])
        renewals = approved_count - new_paying

        new_users = (
            total_users
            if since is None
            else await self._count_users(User.created_at >= since)
        )

        # Birlik iqtisodi
        denom_users = (
            total_users
            if since is None
            else await self._count_users(User.last_active_at >= since)
        )
        arpu = revenue_usd / denom_users if denom_users else 0.0
        arppu = revenue_usd / paying_users if paying_users else 0.0
        avg_check = revenue_usd / approved_count if approved_count else 0.0

        # Renewal payment share and current state of users who actually paid.
        renewal_share = _pct(renewals, approved_count)
        if since is None:
            inactive_paid_share = _pct(max(paid_ever - active_paid_now, 0), paid_ever)
            ever_renewed_share = _pct(renewed_ever, paid_ever)
        else:
            inactive_paid_share = None
            ever_renewed_share = None

        # Manba -> pul
        sources_paid = self._sources_paid(in_period, source_events_by_user)
        client_business = self._client_business(
            since=since,
            approved=in_period,
            source_events_by_user=source_events_by_user,
            revenue_usd=revenue_usd,
            approved_count=approved_count,
            active_paid_now=active_paid_now,
        )

        ai_share = _pct(ai_cost_usd, revenue_usd)
        margin = _pct(net_usd, revenue_usd)

        finance = {
            "revenue_usd": round(revenue_usd, 2),
            "revenue_text": _usd(revenue_usd),
            "ai_usage": ai_usage,
            "ai_cost_usd": round(ai_cost_usd, 2),
            "ai_cost_text": _usd(ai_cost_usd),
            "manual_profit_usd": round(manual_profit_usd, 2),
            "manual_profit_text": _usd(manual_profit_usd),
            "expense_usd": round(expense_usd, 2),
            "expense_text": _usd(expense_usd),
            "net_usd": round(net_usd, 2),
            "net_text": _usd(net_usd),
            "net_positive": net_usd >= 0,
            "ai_share_pct": ai_share,
            "margin_pct": margin,
            "unpriced_payments": unpriced_payments,
            "explain": (
                "Bepul AI yozuvlari $0; eski taxminlar tekshirilmaguncha saqlanadi. "
                "Kuzatilgan net = obuna tushumi + qo'lda foyda − AI model-cost estimate − qo'lda rasxod. "
                f"Obuna tushumi {_usd(revenue_usd)}, qo'lda foyda {_usd(manual_profit_usd)}, "
                f"AI estimate {_usd(ai_cost_usd)}, rasxod {_usd(expense_usd)}, net {_usd(net_usd)}. "
                "USD qiymatlar koddagi reference kurs bilan hisoblangan; historical FX snapshot, soliq, "
                "payment fee va boshqa infra xarajatlari saqlanmagani uchun bu accounting sof foyda emas. "
                f"Narxi aniqlanmagan to'lov: {unpriced_payments}."
            ),
        }

        unit = {
            "total_users": total_users,
            "new_users": new_users,
            "arpu_users": denom_users,
            "paying_users": paying_users,
            "approved_count": approved_count,
            "arpu_usd": round(arpu, 3),
            "arpu_text": _usd(arpu),
            "arppu_usd": round(arppu, 2),
            "arppu_text": _usd(arppu),
            "avg_check_text": _usd(avg_check),
            "explain": (
                f"ARPU = daromad ÷ {'jami' if since is None else 'shu davrda faol'} foydalanuvchi "
                f"({_usd(revenue_usd)} ÷ {denom_users}) = {_usd(arpu)} — o'rtacha har bir foydalanuvchi qancha pul keltiradi. "
                f"ARPPU = daromad ÷ pul to'laganlar ({_usd(revenue_usd)} ÷ {paying_users}) = {_usd(arppu)} — "
                f"o'rtacha har bir pullik foydalanuvchidan tushum. "
                f"O'rtacha chek (har bir to'lov) = {_usd(avg_check)}."
            ),
        }

        retention = {
            "new_paying": new_paying,
            "renewals": renewals,
            "renewal_share_pct": renewal_share,
            "ever_renewed_share_pct": ever_renewed_share,
            "inactive_paid_share_pct": inactive_paid_share,
            # Backward-compatible field; the old value was not cohort churn.
            "churn_rate_pct": None,
            "paid_ever": paid_ever,
            "active_paid_now": active_paid_now,
            "renewed_ever": renewed_ever,
            "explain": self._retention_explain(
                since=since,
                approved_count=approved_count,
                new_paying=new_paying,
                renewals=renewals,
                renewal_share=renewal_share,
                paid_ever=paid_ever,
                active_paid_now=active_paid_now,
                renewed_ever=renewed_ever,
                ever_renewed_share=ever_renewed_share,
                inactive_paid_share=inactive_paid_share,
            ),
        }

        return {
            "key": key,
            "title": title,
            "note": note,
            "range_label": self._range_label(since, now),
            "finance": finance,
            "unit": unit,
            "retention": retention,
            "sources_paid": sources_paid,
            "client_business": client_business,
            "source_attribution_explain": (
                "Yangi paymentlarda aniq Payment.source ishlatiladi (Android / Mini App / Desktop). "
                "Eski yoki telegram_bot yozuvlarida tarixiy aniqlikni saqlash uchun paymentdan oldingi "
                "eng yaqin obuna-kirish manbasi fallback sifatida olinadi."
            ),
            "cards": [
                {"label": "Daromad", "value": _usd(revenue_usd), "note": f"{approved_count} ta to'lov", "tone": "info"},
                {"label": "AI model estimate", "value": _usd(ai_cost_usd), "note": f"daromadning {ai_share}%", "tone": "warn"},
                {"label": "Qo'lda foyda", "value": _usd(manual_profit_usd), "note": "portfel", "tone": "good"},
                {"label": "Portfel rasxod", "value": _usd(expense_usd), "note": "qo'lda kiritilgan", "tone": "warn"},
                {"label": "Kuzatilgan net", "value": _usd(net_usd), "note": f"marja {margin}%", "tone": "good" if net_usd >= 0 else "danger"},
                {"label": "ARPU", "value": _usd(arpu), "note": "har foydalanuvchi", "tone": "info"},
                {"label": "ARPPU", "value": _usd(arppu), "note": "har pullik", "tone": "good"},
                {"label": "Pullik foydalanuvchi", "value": paying_users, "note": f"yangi {new_paying} · yangilash {renewals}", "tone": "good"},
                {
                    "label": "Yangilash" if since is not None else "Hozir inactive payer",
                    "value": f"{renewal_share}%" if since is not None else f"{inactive_paid_share}%",
                    "note": "qayta to'lov ulushi" if since is not None else "ever payer ichida",
                    "tone": "good" if since is not None else "danger",
                },
            ],
        }

    def _sources_paid(
        self,
        in_period: list[_ApprovedPayment],
        source_events_by_user: dict[int, list[tuple[datetime, str]]],
    ) -> list[dict]:
        agg: dict[str, dict] = {}
        for p in in_period:
            source = SubscriptionEntryAnalyticsService.source_group_key(
                self._source_for_payment(
                    p,
                    source_events_by_user.get(p.user_id, []),
                )
            )
            bucket = agg.setdefault(source, {"revenue": 0.0, "users": set(), "payments": 0})
            bucket["revenue"] += p.usd
            bucket["users"].add(p.user_id)
            bucket["payments"] += 1
        rows = [
            {
                "source": source,
                "label": SubscriptionEntryAnalyticsService.source_label(source),
                "paying_users": len(data["users"]),
                "payments": data["payments"],
                "revenue_usd": round(data["revenue"], 2),
                "revenue_text": _usd(data["revenue"]),
            }
            for source, data in agg.items()
        ]
        rows.sort(key=lambda r: r["revenue_usd"], reverse=True)
        return rows[:12]

    def _client_business(
        self,
        *,
        since: datetime | None,
        approved: list[_ApprovedPayment],
        source_events_by_user: dict[int, list[tuple[datetime, str]]],
        revenue_usd: float,
        approved_count: int,
        active_paid_now: int,
    ) -> dict:
        buckets = {
            key: {
                "entries": 0,
                "entry_users": set(),
                "paying_users": set(),
                "payments": 0,
                "revenue": 0.0,
            }
            for key in _CLIENT_CHANNELS
        }

        for telegram_id, events in source_events_by_user.items():
            for created_at, source in events:
                if since is not None and created_at < since:
                    continue
                client = self._client_key_for_source(source)
                bucket = buckets.setdefault(
                    client,
                    {
                        "entries": 0,
                        "entry_users": set(),
                        "paying_users": set(),
                        "payments": 0,
                        "revenue": 0.0,
                    },
                )
                bucket["entries"] += 1
                bucket["entry_users"].add(int(telegram_id))

        for payment in approved:
            source = self._source_for_payment(
                payment,
                source_events_by_user.get(payment.user_id, []),
            )
            client = self._client_key_for_source(source)
            bucket = buckets.setdefault(
                client,
                {
                    "entries": 0,
                    "entry_users": set(),
                    "paying_users": set(),
                    "payments": 0,
                    "revenue": 0.0,
                },
            )
            bucket["payments"] += 1
            bucket["paying_users"].add(payment.user_id)
            if payment.priced:
                bucket["revenue"] += payment.usd

        rows = []
        for key in _CLIENT_ORDER:
            data = buckets.get(key)
            if not data:
                continue
            if key == "unknown" and not any(
                (
                    data["entries"],
                    data["entry_users"],
                    data["paying_users"],
                    data["payments"],
                    data["revenue"],
                )
            ):
                continue
            meta = _CLIENT_CHANNELS.get(key, _CLIENT_CHANNELS["unknown"])
            rows.append(
                {
                    "key": key,
                    "label": meta["label"],
                    "note": meta["note"],
                    "entries": int(data["entries"]),
                    "entry_users": len(data["entry_users"]),
                    "paying_users": len(data["paying_users"]),
                    "payments": int(data["payments"]),
                    "revenue_usd": round(float(data["revenue"]), 2),
                    "revenue_text": _usd(float(data["revenue"])),
                }
            )

        return {
            "cards": [
                {
                    "label": "Umumiy tushum",
                    "value": _usd(revenue_usd),
                    "note": f"{approved_count} ta approved payment",
                    "tone": "info",
                },
                {
                    "label": "Faol obuna",
                    "value": active_paid_now,
                    "note": "User access bitta schema",
                    "tone": "good",
                },
                {
                    "label": "Client kesimi",
                    "value": "Mini App · Android · Desktop",
                    "note": "alohida payment bazasi yo'q",
                    "tone": "info",
                },
            ],
            "rows": rows,
            "explain": (
                "Mini App, Android va Desktop alohida biznes bazaga yozmaydi: "
                "pul approved Payment jadvalidan, obuna holati User access maydonlaridan, "
                "yangi to'lovlarda client attribution Payment.source'dan, eski yozuvlarda esa "
                "paymentdan oldingi eng yaqin SubscriptionEntryEvent manbasidan olinadi."
            ),
        }

    @staticmethod
    def _client_key_for_source(source: str | None) -> str:
        group = SubscriptionEntryAnalyticsService.source_group_key(source)
        if group == "unknown":
            return "unknown"
        if group.startswith("android_") or group == "android_subscription":
            return "android"
        if group.startswith("desktop_") or group == "desktop_subscription":
            return "desktop"
        return "miniapp"

    @staticmethod
    def _source_for_payment(
        payment: _ApprovedPayment,
        source_events: list[tuple[datetime, str]],
    ) -> str:
        exact = str(payment.source or "").strip().lower()
        if exact in {"android", "desktop", "miniapp"}:
            return exact
        source = "unknown"
        for created_at, candidate in source_events:
            if created_at > payment.submitted_at:
                break
            source = candidate or "unknown"
        return source

    @staticmethod
    def _retention_explain(
        *,
        since,
        approved_count,
        new_paying,
        renewals,
        renewal_share,
        paid_ever,
        active_paid_now,
        renewed_ever,
        ever_renewed_share,
        inactive_paid_share,
    ) -> str:
        if since is not None:
            return (
                f"Shu davrda {approved_count} ta to'lov tasdiqlangan: {new_paying} tasi birinchi marta to'lagan, "
                f"{renewals} tasi obunani yangilagan (qayta to'lov ulushi {renewal_share}%). "
                "Yangilash ulushi qancha baland bo'lsa, obuna shuncha barqaror."
            )
        return (
            f"Hozirgacha {paid_ever} foydalanuvchi kamida bir marta to'lagan, ulardan {renewed_ever} tasi "
            f"obunani kamida bir marta yangilagan (ever payer ichida {ever_renewed_share}%). "
            f"Hozir shu payerlardan {active_paid_now} kishi faol; {max(paid_ever - active_paid_now, 0)} kishi "
            f"hozir inactive ({inactive_paid_share}%). Bu snapshot, cohort churn emas."
        )

    @staticmethod
    def _range_label(since: datetime | None, now: datetime) -> str:
        end = now.astimezone(STATS_TZ).strftime("%d.%m.%Y")
        if since is None:
            return f"boshidan — {end}"
        start = since.astimezone(STATS_TZ).strftime("%d.%m.%Y")
        return f"{start} — {end}"
