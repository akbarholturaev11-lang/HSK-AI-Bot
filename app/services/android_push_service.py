"""Shared Firebase Cloud Messaging transport for authenticated Android devices.

FCM is a transport, never the source of truth. Payloads are small data-only
hints; Android re-checks account/release/course state before showing anything
that can affect the user.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from typing import Mapping, Sequence

import google.auth
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import service_account
import httpx
from sqlalchemy import select

from app.config import settings
from app.db.models.android_push import AndroidPushToken
from app.db.models.desktop import DesktopDevice


logger = logging.getLogger(__name__)
FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
FCM_CONCURRENCY = 20


@dataclass(frozen=True)
class AndroidPushResult:
    accepted: bool
    stale_token: bool = False


@dataclass(frozen=True)
class AndroidPushTarget:
    token: str
    device_id: str
    data: Mapping[str, object]


class AndroidPushService:
    """Owns Android FCM token lifecycle and generic data-only delivery."""

    def __init__(self, session, settings_obj=settings):
        self.session = session
        self.settings = settings_obj
        self._authorization: str | None = None

    @property
    def configured(self) -> bool:
        return bool(str(getattr(self.settings, "ANDROID_FCM_PROJECT_ID", "") or "").strip())

    async def register(self, *, device: DesktopDevice, token: str) -> None:
        if device.platform != "android" or device.revoked_at is not None:
            raise ValueError("android_device_required")
        existing = (
            await self.session.execute(
                select(AndroidPushToken).where(AndroidPushToken.token == token)
            )
        ).scalar_one_or_none()
        if existing and existing.device_id != device.id:
            await self.session.delete(existing)
            await self.session.flush()

        now = datetime.now(timezone.utc)
        by_device = await self.session.get(AndroidPushToken, device.id)
        if by_device:
            by_device.token = token
            by_device.updated_at = now
        else:
            self.session.add(
                AndroidPushToken(
                    device_id=device.id,
                    token=token,
                    registered_at=now,
                    updated_at=now,
                )
            )
        await self.session.commit()

    async def unregister(self, *, device: DesktopDevice) -> None:
        row = await self.session.get(AndroidPushToken, device.id)
        if row:
            await self.session.delete(row)
            await self.session.commit()

    async def update_preferences(
        self,
        *,
        device: DesktopDevice,
        study_reminders_enabled: bool,
        timezone_name: str,
        notifications_allowed: bool | None = None,
    ) -> None:
        row = await self.session.get(AndroidPushToken, device.id)
        if row is None:
            return
        row.study_reminders_enabled = bool(study_reminders_enabled)
        row.timezone_name = timezone_name
        # Older builds do not send it; their account notices stay on Telegram.
        if notifications_allowed is not None:
            row.notifications_allowed = bool(notifications_allowed)
        row.updated_at = datetime.now(timezone.utc)
        await self.session.commit()

    def _credentials(self):
        raw = str(getattr(self.settings, "ANDROID_FCM_SERVICE_ACCOUNT_JSON", "") or "").strip()
        if raw:
            credentials = service_account.Credentials.from_service_account_info(
                json.loads(raw), scopes=[FCM_SCOPE]
            )
        else:
            credentials, _ = google.auth.default(scopes=[FCM_SCOPE])
        return credentials

    async def _authorization_header(self) -> str:
        if self._authorization:
            return self._authorization
        credentials = await asyncio.to_thread(self._credentials)
        await asyncio.to_thread(credentials.refresh, GoogleAuthRequest())
        self._authorization = f"Bearer {credentials.token}"
        return self._authorization

    @staticmethod
    def _payload_data(data: Mapping[str, object]) -> dict[str, str]:
        result: dict[str, str] = {}
        for key, value in data.items():
            name = str(key).strip()
            if not name or value is None:
                continue
            result[name] = str(value)
        if "kind" not in result:
            raise ValueError("android_push_kind_required")
        return result

    @staticmethod
    def _is_stale_token(response: httpx.Response) -> bool:
        if response.status_code == 404:
            return True
        try:
            body = response.json()
        except Exception:
            return False
        error = body.get("error") if isinstance(body, dict) else None
        details = error.get("details", []) if isinstance(error, dict) else []
        for detail in details if isinstance(details, list) else []:
            if isinstance(detail, dict) and detail.get("errorCode") == "UNREGISTERED":
                return True
        return False

    async def _post_target(
        self,
        *,
        client: httpx.AsyncClient,
        authorization: str,
        target: AndroidPushTarget,
        ttl_seconds: int,
    ) -> AndroidPushResult:
        project_id = str(self.settings.ANDROID_FCM_PROJECT_ID).strip()
        data = self._payload_data(target.data)
        payload = {
            "message": {
                "token": target.token,
                "data": data,
                "android": {
                    "priority": "HIGH",
                    "ttl": f"{max(0, int(ttl_seconds))}s",
                },
            }
        }
        response = await client.post(
            f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send",
            headers={"Authorization": authorization},
            json=payload,
        )
        if response.is_success:
            return AndroidPushResult(True)
        stale = self._is_stale_token(response)
        logger.warning(
            "Android FCM refused kind=%s device=%s status=%s stale=%s",
            data.get("kind"),
            target.device_id,
            response.status_code,
            stale,
        )
        return AndroidPushResult(False, stale_token=stale)

    async def send_batch(
        self,
        targets: Sequence[AndroidPushTarget],
        *,
        ttl_seconds: int = 86400,
    ) -> list[AndroidPushResult]:
        if not targets:
            return []
        if not self.configured:
            return [AndroidPushResult(False) for _ in targets]

        authorization = await self._authorization_header()
        semaphore = asyncio.Semaphore(FCM_CONCURRENCY)

        async with httpx.AsyncClient(timeout=6.0) as client:
            async def send_one(target: AndroidPushTarget) -> AndroidPushResult:
                async with semaphore:
                    try:
                        return await self._post_target(
                            client=client,
                            authorization=authorization,
                            target=target,
                            ttl_seconds=ttl_seconds,
                        )
                    except Exception:
                        logger.exception(
                            "Android push failed kind=%s device=%s",
                            target.data.get("kind"),
                            target.device_id,
                        )
                        return AndroidPushResult(False)

            results = list(await asyncio.gather(*(send_one(target) for target in targets)))

        stale_dirty = False
        for target, result in zip(targets, results):
            if not result.stale_token:
                continue
            row = await self.session.get(AndroidPushToken, target.device_id)
            if row is not None and row.token == target.token:
                await self.session.delete(row)
                stale_dirty = True
        if stale_dirty:
            await self.session.commit()

        return results

    async def send_token(
        self,
        *,
        token: str,
        device_id: str,
        data: Mapping[str, object],
        ttl_seconds: int = 86400,
    ) -> AndroidPushResult:
        results = await self.send_batch(
            [AndroidPushTarget(token=token, device_id=device_id, data=data)],
            ttl_seconds=ttl_seconds,
        )
        return results[0]

    async def send_to_user(
        self,
        *,
        telegram_id: int,
        data: Mapping[str, object],
        ttl_seconds: int = 86400,
    ) -> int:
        if not self.configured:
            return 0
        rows = (
            await self.session.execute(
                select(AndroidPushToken.token, AndroidPushToken.device_id)
                .join(DesktopDevice, AndroidPushToken.device_id == DesktopDevice.id)
                .where(
                    DesktopDevice.telegram_id == telegram_id,
                    DesktopDevice.platform == "android",
                    DesktopDevice.revoked_at.is_(None),
                )
            )
        ).all()
        results = await self.send_batch(
            [
                AndroidPushTarget(token=token, device_id=device_id, data=data)
                for token, device_id in rows
            ],
            ttl_seconds=ttl_seconds,
        )
        return sum(1 for result in results if result.accepted)
