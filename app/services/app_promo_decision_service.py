from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.models.user_client_presence import AppPromoState
from app.repositories.user_repo import UserRepository
from app.services.user_device_inventory_service import (
    NATIVE_PLATFORMS,
    UserDeviceInventoryService,
    normalize_client_platform,
)


PROMO_COOLDOWN_DAYS = 14


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class AppPromoDecisionService:
    """Platform-aware automatic app promo authority.

    Profile/manual download entry is intentionally outside this service: the
    user may always open the apps page. This class only decides unsolicited
    automatic promotion.
    """

    def __init__(self, session):
        self.session = session
        self.inventory = UserDeviceInventoryService(session)

    async def _state(
        self,
        *,
        telegram_id: int,
        target_platform: str,
        create: bool,
    ) -> AppPromoState | None:
        user = await UserRepository(self.session).get_by_telegram_id(int(telegram_id))
        if not user:
            return None
        result = await self.session.execute(
            select(AppPromoState).where(
                AppPromoState.user_id == user.id,
                AppPromoState.target_platform == target_platform,
            )
        )
        state = result.scalar_one_or_none()
        if state is not None or not create:
            return state
        state = AppPromoState(
            user_id=user.id,
            telegram_id=user.telegram_id,
            target_platform=target_platform,
        )
        try:
            async with self.session.begin_nested():
                self.session.add(state)
                await self.session.flush()
            return state
        except IntegrityError:
            result = await self.session.execute(
                select(AppPromoState).where(
                    AppPromoState.user_id == user.id,
                    AppPromoState.target_platform == target_platform,
                )
            )
            return result.scalar_one_or_none()

    @staticmethod
    def _latest_state_at(state: AppPromoState | None) -> datetime | None:
        if state is None:
            return None
        values = [
            _as_utc(state.last_seen_at),
            _as_utc(state.last_dismissed_at),
            _as_utc(state.last_download_requested_at),
        ]
        values = [value for value in values if value is not None]
        return max(values) if values else None

    async def decide(
        self,
        *,
        telegram_id: int,
        current_platform: str,
        available_targets: dict[str, bool],
    ) -> dict[str, Any]:
        platform = normalize_client_platform(current_platform)
        if platform not in NATIVE_PLATFORMS:
            return {
                "eligible": False,
                "reason": "no_matching_native_app",
                "target_platform": None,
                "cooldown_remaining_seconds": 0,
            }
        if not bool(available_targets.get(platform)):
            return {
                "eligible": False,
                "reason": "not_ready",
                "target_platform": platform,
                "cooldown_remaining_seconds": 0,
            }

        installed = await self.inventory.installed_native_platforms(telegram_id)
        if platform in installed:
            return {
                "eligible": False,
                "reason": "already_installed",
                "target_platform": platform,
                "cooldown_remaining_seconds": 0,
            }

        state = await self._state(
            telegram_id=telegram_id,
            target_platform=platform,
            create=False,
        )
        last_at = self._latest_state_at(state)
        remaining = 0
        if last_at is not None:
            next_at = last_at + timedelta(days=PROMO_COOLDOWN_DAYS)
            remaining = max(0, int((next_at - _utcnow()).total_seconds()))
        if remaining > 0:
            return {
                "eligible": False,
                "reason": "cooldown",
                "target_platform": platform,
                "cooldown_remaining_seconds": remaining,
            }
        return {
            "eligible": True,
            "reason": "eligible",
            "target_platform": platform,
            "cooldown_remaining_seconds": 0,
        }

    async def mark(
        self,
        *,
        telegram_id: int,
        target_platform: str,
        action: str,
    ) -> bool:
        platform = normalize_client_platform(target_platform)
        if platform not in NATIVE_PLATFORMS:
            return False
        state = await self._state(
            telegram_id=telegram_id,
            target_platform=platform,
            create=True,
        )
        if state is None:
            return False
        now = _utcnow()
        if action == "seen":
            state.last_seen_at = now
        elif action == "dismissed":
            state.last_dismissed_at = now
        elif action == "download_requested":
            state.last_download_requested_at = now
        else:
            return False
        state.updated_at = now
        await self.session.flush()
        return True
