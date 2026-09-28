"""Pro trial anti-abuse risk engine.

The engine uses only privacy-safe signals already available to HSK AI. The
score is an internal 0..100 risk score, not a fraud probability. Raw IP
addresses and raw native installation keys are never stored.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import case, func, or_, select

from app.db.models.trial_risk_event import TrialRiskEvent


logger = logging.getLogger(__name__)

MODE_ENFORCED = "enforced"

# Fixed server-side policy. There is intentionally no admin control: changing
# these values requires code review + tests + deploy.
RISK_SCORE_THRESHOLD = 80
RISK_SCORE_DEVICE_REUSE = 80
RISK_SCORE_IP_24H_3 = 15
RISK_SCORE_IP_24H_5 = 30
RISK_SCORE_IP_24H_10 = 50
RISK_SCORE_IP_7D_10 = 10
RISK_SCORE_ACCOUNT_UNDER_1H = 5
RISK_SCORE_ACCOUNT_UNDER_24H = 2


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class TrialRiskSnapshot:
    client: str
    source: str
    installation_key_hash: str | None
    ip_hash: str | None
    account_age_minutes: int | None
    prior_device_trial_users: int = 0
    prior_ip_trial_users_24h: int = 0
    prior_ip_trial_users_7d: int = 0
    signals: tuple[str, ...] = ()
    mode: str = MODE_ENFORCED


@dataclass(frozen=True)
class TrialRiskDecision:
    score: int
    denied: bool
    reasons: tuple[str, ...] = ()
    threshold: int = RISK_SCORE_THRESHOLD


class TrialRiskService:
    def __init__(self, session, settings_obj=None):
        self.session = session
        self.settings_obj = settings_obj

    def _hash_ip(self, remote_ip: str | None) -> str | None:
        raw = str(remote_ip or "").strip()
        if not raw:
            return None
        try:
            canonical = ipaddress.ip_address(raw).compressed
        except ValueError:
            return None

        secret = str(
            getattr(self.settings_obj, "DESKTOP_AUTH_SIGNING_SECRET", "") or ""
        )
        if len(secret) < 32:
            return None
        return hmac.new(
            secret.encode(),
            f"trial-risk-ip:{canonical}".encode(),
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def _clean_installation_hash(value: str | None) -> str | None:
        cleaned = str(value or "").strip().lower()
        if len(cleaned) != 64:
            return None
        if any(ch not in "0123456789abcdef" for ch in cleaned):
            return None
        return cleaned

    @staticmethod
    def _account_age_minutes(user, now: datetime) -> int | None:
        created = _as_utc(getattr(user, "created_at", None))
        if created is None:
            return None
        return max(0, int((now - created).total_seconds() // 60))

    async def analyze(
        self,
        user,
        *,
        client: str,
        source: str,
        installation_key_hash: str | None = None,
        remote_ip: str | None = None,
        now: datetime | None = None,
    ) -> TrialRiskSnapshot:
        """Build a fail-open risk snapshot without changing entitlement state."""
        now = now or datetime.now(timezone.utc)
        installation_hash = self._clean_installation_hash(installation_key_hash)
        ip_hash = self._hash_ip(remote_ip)
        fallback = TrialRiskSnapshot(
            client=str(client or "")[:16],
            source=str(source or "")[:32],
            installation_key_hash=installation_hash,
            ip_hash=ip_hash,
            account_age_minutes=self._account_age_minutes(user, now),
        )

        try:
            async with self.session.begin_nested():
                return await self._analyze(
                    user,
                    fallback=fallback,
                    now=now,
                )
        except Exception:  # noqa: BLE001 - telemetry must never break trial
            logger.exception(
                "trial_risk_analyze_failed telegram_id=%s client=%s",
                getattr(user, "telegram_id", None),
                client,
            )
            return fallback

    async def _analyze(
        self,
        user,
        *,
        fallback: TrialRiskSnapshot,
        now: datetime,
    ) -> TrialRiskSnapshot:
        telegram_id = int(getattr(user, "telegram_id", 0) or 0)
        prior_device = 0
        prior_ip_24h = 0
        prior_ip_7d = 0

        if fallback.installation_key_hash and telegram_id:
            result = await self.session.execute(
                select(func.count(func.distinct(TrialRiskEvent.telegram_id))).where(
                    TrialRiskEvent.installation_key_hash
                    == fallback.installation_key_hash,
                    TrialRiskEvent.telegram_id != telegram_id,
                )
            )
            prior_device = int(result.scalar() or 0)

        if fallback.ip_hash and telegram_id:
            seven_days_ago = now - timedelta(days=7)
            one_day_ago = now - timedelta(hours=24)
            result = await self.session.execute(
                select(
                    func.count(
                        func.distinct(TrialRiskEvent.telegram_id)
                    ).filter(TrialRiskEvent.created_at >= one_day_ago),
                    func.count(func.distinct(TrialRiskEvent.telegram_id)),
                ).where(
                    TrialRiskEvent.ip_hash == fallback.ip_hash,
                    TrialRiskEvent.telegram_id != telegram_id,
                    TrialRiskEvent.created_at >= seven_days_ago,
                )
            )
            prior_ip_24h, prior_ip_7d = result.one()
            prior_ip_24h = int(prior_ip_24h or 0)
            prior_ip_7d = int(prior_ip_7d or 0)

        signals: list[str] = []
        if prior_device:
            signals.append("device_used_for_other_trial")
        if prior_ip_24h:
            signals.append("shared_ip_24h")
        elif prior_ip_7d:
            signals.append("shared_ip_7d")

        age = fallback.account_age_minutes
        if age is not None and age < 60:
            signals.append("account_under_1h")
        elif age is not None and age < 24 * 60:
            signals.append("account_under_24h")

        return TrialRiskSnapshot(
            client=fallback.client,
            source=fallback.source,
            installation_key_hash=fallback.installation_key_hash,
            ip_hash=fallback.ip_hash,
            account_age_minutes=age,
            prior_device_trial_users=prior_device,
            prior_ip_trial_users_24h=prior_ip_24h,
            prior_ip_trial_users_7d=prior_ip_7d,
            signals=tuple(signals),
        )

    @staticmethod
    def evaluate(snapshot: TrialRiskSnapshot) -> TrialRiskDecision:
        """Deterministically score one snapshot.

        Account age is deliberately weak: a legitimate new learner may start
        a trial immediately. Device reuse is the only single signal strong
        enough to cross the threshold; IP needs corroborating evidence.
        """
        score = 0
        reasons: list[str] = []

        if snapshot.prior_device_trial_users > 0:
            score += RISK_SCORE_DEVICE_REUSE
            reasons.append("device_reuse")

        ip24 = int(snapshot.prior_ip_trial_users_24h or 0)
        if ip24 >= 10:
            score += RISK_SCORE_IP_24H_10
            reasons.append("ip_24h_10_plus")
        elif ip24 >= 5:
            score += RISK_SCORE_IP_24H_5
            reasons.append("ip_24h_5_plus")
        elif ip24 >= 3:
            score += RISK_SCORE_IP_24H_3
            reasons.append("ip_24h_3_plus")

        if int(snapshot.prior_ip_trial_users_7d or 0) >= 10:
            score += RISK_SCORE_IP_7D_10
            reasons.append("ip_7d_10_plus")

        age = snapshot.account_age_minutes
        if age is not None and age < 60:
            score += RISK_SCORE_ACCOUNT_UNDER_1H
            reasons.append("account_under_1h")
        elif age is not None and age < 24 * 60:
            score += RISK_SCORE_ACCOUNT_UNDER_24H
            reasons.append("account_under_24h")

        score = min(100, max(0, int(score)))
        return TrialRiskDecision(
            score=score,
            denied=score >= RISK_SCORE_THRESHOLD,
            reasons=tuple(reasons),
        )

    async def report(self, *, days: int = 7, limit: int = 20) -> dict:
        """Admin uchun hashlarni oshkor qilmaydigan anti-abuse hisoboti."""
        days = max(1, min(int(days), 90))
        limit = max(1, min(int(limit), 50))
        since = datetime.now(timezone.utc) - timedelta(days=days)

        summary_result = await self.session.execute(
            select(
                func.count(TrialRiskEvent.id),
                func.sum(
                    case((TrialRiskEvent.prior_device_trial_users > 0, 1), else_=0)
                ),
                func.sum(
                    case(
                        (
                            or_(
                                TrialRiskEvent.prior_ip_trial_users_24h > 0,
                                TrialRiskEvent.prior_ip_trial_users_7d > 0,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                func.sum(
                    case((TrialRiskEvent.account_age_minutes < 60, 1), else_=0)
                ),
                func.sum(
                    case((TrialRiskEvent.account_age_minutes < 24 * 60, 1), else_=0)
                ),
            ).where(TrialRiskEvent.created_at >= since)
        )
        total, device_reuse, shared_ip, under_1h, under_24h = summary_result.one()

        client_rows = (
            await self.session.execute(
                select(TrialRiskEvent.client, func.count(TrialRiskEvent.id))
                .where(TrialRiskEvent.created_at >= since)
                .group_by(TrialRiskEvent.client)
                .order_by(TrialRiskEvent.client)
            )
        ).all()

        suspicious = (
            await self.session.execute(
                select(TrialRiskEvent)
                .where(
                    TrialRiskEvent.created_at >= since,
                    or_(
                        TrialRiskEvent.prior_device_trial_users > 0,
                        TrialRiskEvent.prior_ip_trial_users_24h > 0,
                        TrialRiskEvent.prior_ip_trial_users_7d > 0,
                        TrialRiskEvent.account_age_minutes < 24 * 60,
                    ),
                )
                .order_by(TrialRiskEvent.created_at.desc())
                .limit(limit)
            )
        ).scalars().all()

        examples = []
        for row in suspicious:
            try:
                signals = json.loads(row.signals_json or "[]")
            except (TypeError, ValueError):
                signals = []
            row_snapshot = TrialRiskSnapshot(
                client=row.client,
                source=row.source,
                installation_key_hash=row.installation_key_hash,
                ip_hash=row.ip_hash,
                account_age_minutes=row.account_age_minutes,
                prior_device_trial_users=int(row.prior_device_trial_users or 0),
                prior_ip_trial_users_24h=int(row.prior_ip_trial_users_24h or 0),
                prior_ip_trial_users_7d=int(row.prior_ip_trial_users_7d or 0),
                signals=tuple(signals if isinstance(signals, list) else []),
                mode=row.mode or MODE_ENFORCED,
            )
            decision = self.evaluate(row_snapshot)
            examples.append(
                {
                    "telegram_id": int(row.telegram_id),
                    "client": row.client,
                    "source": row.source,
                    "account_age_minutes": row.account_age_minutes,
                    "prior_device_trial_users": int(
                        row.prior_device_trial_users or 0
                    ),
                    "prior_ip_trial_users_24h": int(
                        row.prior_ip_trial_users_24h or 0
                    ),
                    "prior_ip_trial_users_7d": int(
                        row.prior_ip_trial_users_7d or 0
                    ),
                    "signals": signals if isinstance(signals, list) else [],
                    "risk_score": decision.score,
                    "would_deny": decision.denied,
                    "created_at": (
                        row.created_at.isoformat() if row.created_at else None
                    ),
                }
            )

        return {
            "mode": MODE_ENFORCED,
            "threshold": RISK_SCORE_THRESHOLD,
            "days": days,
            "summary": {
                "trial_starts": int(total or 0),
                "device_reuse": int(device_reuse or 0),
                "shared_ip": int(shared_ip or 0),
                "account_under_1h": int(under_1h or 0),
                "account_under_24h": int(under_24h or 0),
            },
            "clients": {str(client): int(count or 0) for client, count in client_rows},
            "examples": examples,
        }

    async def record_started(self, user, snapshot: TrialRiskSnapshot) -> bool:
        """Persist the snapshot inside a savepoint; failure is fail-open."""
        try:
            async with self.session.begin_nested():
                self.session.add(
                    TrialRiskEvent(
                        user_id=int(user.id),
                        telegram_id=int(user.telegram_id),
                        client=snapshot.client,
                        source=snapshot.source,
                        installation_key_hash=snapshot.installation_key_hash,
                        ip_hash=snapshot.ip_hash,
                        account_age_minutes=snapshot.account_age_minutes,
                        prior_device_trial_users=snapshot.prior_device_trial_users,
                        prior_ip_trial_users_24h=snapshot.prior_ip_trial_users_24h,
                        prior_ip_trial_users_7d=snapshot.prior_ip_trial_users_7d,
                        signals_json=json.dumps(
                            list(snapshot.signals),
                            ensure_ascii=False,
                            separators=(",", ":"),
                        ),
                        mode=snapshot.mode,
                        created_at=datetime.now(timezone.utc),
                    )
                )
                await self.session.flush()
            return True
        except Exception:  # noqa: BLE001 - telemetry must never break trial
            logger.exception(
                "trial_risk_record_failed telegram_id=%s client=%s",
                getattr(user, "telegram_id", None),
                snapshot.client,
            )
            return False
