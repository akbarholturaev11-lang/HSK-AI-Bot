"""Server-owned PWA exit intent: offer on X, claim once, discount only when accepted.

The single user row is locked before evaluating/creating the offer so opening
multiple browser tabs cannot reset the deadline or mint duplicate offers.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.db.models.pwa_exit_offer import PwaExitOffer
from app.db.models.user import User
from app.services.lava.config import LavaConfigService, effective_mode

EXIT_PERCENT = 20
EXIT_TTL = timedelta(hours=24)


def _utc(value):
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class PwaExitOfferService:
    def __init__(self, session, settings_obj):
        self.session = session
        self.settings = settings_obj

    async def _capable(self, user):
        config = await LavaConfigService(self.session).load()
        if effective_mode(config, self.settings, client_supports_lava=True) == "manual_only":
            return False
        if not config.promo_code("exit_offer", EXIT_PERCENT):
            return False
        if not config.sellable_terms():
            return False
        if getattr(user, "status", "") == "blocked":
            return False
        end = _utc(getattr(user, "end_date", None))
        if end is not None and end > datetime.now(timezone.utc):
            return False
        return True

    async def active(self, user, *, now=None):
        now = now or datetime.now(timezone.utc)
        row = await self.session.get(PwaExitOffer, user.id)
        return bool(
            row and row.accepted_at is not None and row.consumed_at is None
            and _utc(row.expires_at) > now
        )

    async def action(self, user, *, action: str):
        if action not in {"view", "claim"}:
            return {"ok": False, "error": "invalid_action"}
        # Account-row lock is also used by Lava invoice start and webhook grant.
        # No changes to a paid or blocked account.
        locked = await self.session.get(User, user.id, with_for_update=True)
        if locked is None or not await self._capable(locked):
            return {"ok": True, "available": False}

        now = datetime.now(timezone.utc)
        row = await self.session.get(PwaExitOffer, user.id, with_for_update=True)
        if row is None:
            if action != "view":
                return {"ok": True, "available": False}
            row = PwaExitOffer(
                user_id=user.id, offered_at=now,
                expires_at=now+EXIT_TTL, accepted_at=None, consumed_at=None
            )
            self.session.add(row)
            await self.session.flush()
        if row.consumed_at is not None or _utc(row.expires_at) <= now:
            return {"ok": True, "available": False}
        if action == "claim" and row.accepted_at is None:
            row.accepted_at = now
        return {
            "ok": True, "available": True, "percent": EXIT_PERCENT,
            "accepted": row.accepted_at is not None,
            "expires_at": _utc(row.expires_at).isoformat()
        }
