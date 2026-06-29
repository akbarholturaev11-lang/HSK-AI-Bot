"""Admin Mini App uchun chuqur moliyaviy va biznes statistikasi.

Bu xizmat yangi admin panel (admin.html) uchun 3 ta davr (7 kun / 30 kun / to'liq)
bo'yicha bir xil tuzilishdagi hisobotlarni quradi:

- Sof foyda = daromad (USD) − real AI xarajat (ai_usage_events) − portfel rasxod
- ARPU / ARPPU
- Obuna yangilash (renewal) va churn foizi
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
    is_renewal: bool


class AdminFinanceStatsService:
    def __init__(self, session):
        self.session = session

    async def build(self) -> dict:
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        approved = await self._load_approved_payments()
        source_by_user = await self._source_by_user()

        total_users = await self._count_users()
        active_paid_now = await self._active_paid_now(now)
        paid_ever = len({p.user_id for p in approved})
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
                    source_by_user=source_by_user,
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
                ).where(Payment.payment_status == "approved")
            )
        ).all()

        items: list[_ApprovedPayment] = []
        for user_id, amount, currency, base_amount, reviewed_at, submitted_at in rows:
            usd = _amount_to_usd(amount, currency)
            if usd is None and base_amount:
                usd = _amount_to_usd(base_amount, "TJS")
            if usd is None:
                usd = 0.0
            at = reviewed_at or submitted_at
            if at is None:
                continue
            if at.tzinfo is None:
                at = at.replace(tzinfo=timezone.utc)
            items.append(_ApprovedPayment(user_id=int(user_id), usd=float(usd), at=at, is_renewal=False))

        # Vaqt bo'yicha tartiblab, har bir foydalanuvchining 2-chi+ to'lovini
        # "yangilash" (renewal) deb belgilaymiz.
        items.sort(key=lambda p: p.at)
        seen: set[int] = set()
        for p in items:
            if p.user_id in seen:
                p.is_renewal = True
            seen.add(p.user_id)
        return items

    async def _source_by_user(self) -> dict[int, str]:
        """Har bir foydalanuvchi uchun eng so'nggi obuna-kirish manbasi."""
        rows = (
            await self.session.execute(
                select(
                    SubscriptionEntryEvent.telegram_id,
                    SubscriptionEntryEvent.source,
                    SubscriptionEntryEvent.created_at,
                ).order_by(SubscriptionEntryEvent.created_at.asc())
            )
        ).all()
        result: dict[int, str] = {}
        for telegram_id, source, _created in rows:
            result[int(telegram_id)] = source or "unknown"
        return result

    async def _count_users(self, *conditions) -> int:
        stmt = select(func.count()).select_from(User)
        if conditions:
            stmt = stmt.where(*conditions)
        return (await self.session.execute(stmt)).scalar() or 0

    async def _active_paid_now(self, now: datetime) -> int:
        return await self._count_users(
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

    async def _expense_usd(self, since: datetime | None) -> float:
        stmt = select(func.coalesce(func.sum(PortfolioTransaction.amount_usd), 0.0)).where(
            PortfolioTransaction.transaction_type == "expense"
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
        source_by_user: dict[int, str],
        total_users: int,
        active_paid_now: int,
        paid_ever: int,
        renewed_ever: int,
    ) -> dict:
        in_period = [p for p in approved if since is None or p.at >= since]

        revenue_usd = sum(p.usd for p in in_period)
        ai_cost_usd = await self._ai_cost_usd(since)
        expense_usd = await self._expense_usd(since)
        net_usd = revenue_usd - ai_cost_usd - expense_usd

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
        denom_users = total_users if since is None else new_users
        arpu = revenue_usd / denom_users if denom_users else 0.0
        arppu = revenue_usd / paying_users if paying_users else 0.0
        avg_check = revenue_usd / approved_count if approved_count else 0.0

        # Renewal / churn
        renewal_share = _pct(renewals, approved_count)
        if since is None:
            churn_rate = _pct(max(paid_ever - active_paid_now, 0), paid_ever)
            renewal_rate = _pct(renewed_ever, paid_ever)
        else:
            churn_rate = None
            renewal_rate = renewal_share

        # Manba -> pul
        sources_paid = self._sources_paid(in_period, source_by_user)

        ai_share = _pct(ai_cost_usd, revenue_usd)
        margin = _pct(net_usd, revenue_usd)

        finance = {
            "revenue_usd": round(revenue_usd, 2),
            "revenue_text": _usd(revenue_usd),
            "ai_cost_usd": round(ai_cost_usd, 2),
            "ai_cost_text": _usd(ai_cost_usd),
            "expense_usd": round(expense_usd, 2),
            "expense_text": _usd(expense_usd),
            "net_usd": round(net_usd, 2),
            "net_text": _usd(net_usd),
            "net_positive": net_usd >= 0,
            "ai_share_pct": ai_share,
            "margin_pct": margin,
            "explain": (
                "Sof foyda = daromad − real AI xarajat − portfel rasxod. "
                f"Daromad {_usd(revenue_usd)} (barcha valyutalar joriy kurs bo'yicha USDga aylandi), "
                f"AI xarajat {_usd(ai_cost_usd)} (ai_usage_events bo'yicha real token narxi), "
                f"qo'lda kiritilgan rasxod {_usd(expense_usd)}. "
                f"Demak sof foyda {_usd(net_usd)}. "
                f"AI xarajat daromadning {ai_share}% ini, sof foyda esa {margin}% ni tashkil etadi."
            ),
        }

        unit = {
            "total_users": total_users,
            "new_users": new_users,
            "paying_users": paying_users,
            "approved_count": approved_count,
            "arpu_usd": round(arpu, 3),
            "arpu_text": _usd(arpu),
            "arppu_usd": round(arppu, 2),
            "arppu_text": _usd(arppu),
            "avg_check_text": _usd(avg_check),
            "explain": (
                f"ARPU = daromad ÷ {'jami' if since is None else 'shu davrdagi yangi'} foydalanuvchi "
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
            "renewal_rate_pct": renewal_rate,
            "churn_rate_pct": churn_rate,
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
                renewal_rate=renewal_rate,
                churn_rate=churn_rate,
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
            "cards": [
                {"label": "Daromad", "value": _usd(revenue_usd), "note": f"{approved_count} ta to'lov", "tone": "info"},
                {"label": "AI xarajat", "value": _usd(ai_cost_usd), "note": f"daromadning {ai_share}%", "tone": "warn"},
                {"label": "Portfel rasxod", "value": _usd(expense_usd), "note": "qo'lda kiritilgan", "tone": "warn"},
                {"label": "Sof foyda", "value": _usd(net_usd), "note": f"marja {margin}%", "tone": "good" if net_usd >= 0 else "danger"},
                {"label": "ARPU", "value": _usd(arpu), "note": "har foydalanuvchi", "tone": "info"},
                {"label": "ARPPU", "value": _usd(arppu), "note": "har pullik", "tone": "good"},
                {"label": "Pullik foydalanuvchi", "value": paying_users, "note": f"yangi {new_paying} · yangilash {renewals}", "tone": "good"},
                {
                    "label": "Yangilash" if since is not None else "Churn",
                    "value": f"{renewal_share}%" if since is not None else f"{churn_rate}%",
                    "note": "qayta to'lov ulushi" if since is not None else "yo'qolgan obunachi",
                    "tone": "good" if since is not None else "danger",
                },
            ],
        }

    def _sources_paid(
        self,
        in_period: list[_ApprovedPayment],
        source_by_user: dict[int, str],
    ) -> list[dict]:
        agg: dict[str, dict] = {}
        for p in in_period:
            source = source_by_user.get(p.user_id, "unknown")
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
        renewal_rate,
        churn_rate,
    ) -> str:
        if since is not None:
            return (
                f"Shu davrda {approved_count} ta to'lov tasdiqlangan: {new_paying} tasi birinchi marta to'lagan, "
                f"{renewals} tasi obunani yangilagan (qayta to'lov ulushi {renewal_share}%). "
                "Yangilash ulushi qancha baland bo'lsa, obuna shuncha barqaror."
            )
        return (
            f"Hozirgacha {paid_ever} foydalanuvchi kamida bir marta to'lagan, ulardan {renewed_ever} tasi "
            f"obunani kamida bir marta yangilagan (yangilash darajasi {renewal_rate}%). "
            f"Hozir faol obunada {active_paid_now} kishi bor; demak {max(paid_ever - active_paid_now, 0)} kishi "
            f"obunadan chiqib ketgan — churn (yo'qotish) darajasi {churn_rate}%. Churn past bo'lsa biznes barqaror."
        )

    @staticmethod
    def _range_label(since: datetime | None, now: datetime) -> str:
        end = now.astimezone(STATS_TZ).strftime("%d.%m.%Y")
        if since is None:
            return f"boshidan — {end}"
        start = since.astimezone(STATS_TZ).strftime("%d.%m.%Y")
        return f"{start} — {end}"
