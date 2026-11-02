"""Isolated browser-only PWA session using existing device/session tables.

No native access/refresh bearer is issued to a browser. Existing provider OAuth
verifies identities; a same-browser, state-bound proof is required before any
callback is permitted to approve a PWA sign-in. Feature is disabled by default.
"""

from __future__ import annotations

import hmac
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select

from app.db.models.desktop import DesktopDevice, DesktopLinkRequest, DesktopSession
from app.db.models.user import User
from app.db.models.user_identity import UserIdentity
from app.services.desktop_auth_service import DesktopAuthService
from app.services.native_oauth_service import NativeOAuthService, redirect_base_url
from app.services.user_access_state_service import UserAccessState, UserAccessStateService

PWA_PLATFORM = "pwa"
PWA_SESSION_COOKIE = "__Host-hskai-pwa"
PWA_OAUTH_COOKIE = "__Host-hskai-pwa-oauth"
PWA_SESSION_AGE_SECONDS = 7 * 24 * 3600
PWA_OAUTH_AGE_SECONDS = 600


class PwaAuthError(RuntimeError):
    def __init__(self, code: str, *, status_code: int = 401):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def pwa_origin(settings_obj) -> str:
    return redirect_base_url(settings_obj)


def pwa_enabled(settings_obj) -> bool:
    return bool(getattr(settings_obj, "PWA_AUTH_ENABLED", False)) and bool(pwa_origin(settings_obj))


def require_pwa_enabled(settings_obj) -> None:
    if not pwa_enabled(settings_obj):
        raise PwaAuthError("pwa_auth_unavailable", status_code=503)


def require_same_origin(request, settings_obj) -> None:
    expected = pwa_origin(settings_obj)
    if not expected or request.headers.get("Origin") != expected:
        raise PwaAuthError("pwa_origin_invalid", status_code=403)


class PwaAuthService:
    def __init__(self, session, settings_obj):
        self.session = session
        self.settings = settings_obj
        self.native = NativeOAuthService(session, settings_obj)
        self.desktop = DesktopAuthService(session, settings_obj)

    async def start(self, *, provider: str, language: str | None = None) -> tuple[str, str]:
        require_pwa_enabled(self.settings)
        if provider not in {"google", "apple"}:
            raise PwaAuthError("pwa_provider_invalid", status_code=422)
        proof = secrets.token_urlsafe(32)
        started = await self.native.start(
            provider=provider, mode="browser_redirect", platform=PWA_PLATFORM,
            app_version="1.0.0", installation_key=proof,
            language=language if language in {"uz", "ru", "tj"} else None,
        )
        if not started.authorize_url:
            raise PwaAuthError("pwa_auth_unavailable", status_code=503)
        # The native polling secret never leaves the server in the PWA flow.
        return started.authorize_url, proof

    async def _verified_row(self, *, provider: str, state: str, proof: str, lock: bool = False):
        if not isinstance(proof, str) or not 32 <= len(proof) <= 200:
            raise PwaAuthError("pwa_oauth_proof_invalid")
        request_id = self.native.link_request_id_from_state(state)
        stmt = select(DesktopLinkRequest).where(DesktopLinkRequest.id == request_id)
        if lock:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if (
            row is None or row.platform != PWA_PLATFORM
            or row.flow != provider or row.intent != "signin"
            or not hmac.compare_digest(
                str(row.installation_key_hash or ""),
                self.desktop._hash("installation", proof),
            )
            or (_aware(row.expires_at) or _now()) <= _now()
        ):
            raise PwaAuthError("pwa_oauth_proof_invalid")
        return row

    async def before_callback(self, *, provider: str, state: str, proof: str | None) -> bool:
        """Reject a PWA callback before provider exchange if the browser proof is absent.

        A native callback has no PWA row and remains unchanged.
        """
        request_id = self.native.link_request_id_from_state(state)
        row = (await self.session.execute(
            select(DesktopLinkRequest).where(DesktopLinkRequest.id == request_id)
        )).scalar_one_or_none()
        if row is None:
            return False  # Native flow retains its existing rejection.
        if row.platform != PWA_PLATFORM:
            return False
        require_pwa_enabled(self.settings)
        checked = await self._verified_row(provider=provider, state=state, proof=proof or "")
        if checked.status != "pending" or checked.consumed_at is not None:
            raise PwaAuthError("pwa_oauth_proof_invalid")
        return True

    async def consume_callback(self, *, provider: str, state: str, proof: str | None) -> str:
        require_pwa_enabled(self.settings)
        row = await self._verified_row(provider=provider, state=state, proof=proof or "", lock=True)
        if row.status != "approved" or row.consumed_at is not None or not row.approved_user_id:
            raise PwaAuthError("pwa_oauth_proof_invalid")
        user = (await self.session.execute(
            select(User).where(User.id == row.approved_user_id).with_for_update()
        )).scalar_one_or_none()
        if user is None or UserAccessStateService.classify(user) == UserAccessState.BLOCKED:
            raise PwaAuthError("pwa_user_unavailable", status_code=403)
        owner_identity = (await self.session.execute(
            select(UserIdentity.id).where(
                UserIdentity.id == row.approved_identity_id,
                UserIdentity.user_id == user.id,
                UserIdentity.provider == provider,
            )
        )).scalar_one_or_none()
        if owner_identity is None:
            raise PwaAuthError("pwa_identity_unavailable")

        # Existing DB models are reused; no schema migration and no bearer token.
        # Random per-login proof makes installation-key collisions improbable.
        device = DesktopDevice(
            id=str(uuid4()), user_id=user.id,
            telegram_id=user.telegram_id, installation_key_hash=row.installation_key_hash,
            platform=PWA_PLATFORM, app_version="1.0.0",
        )
        self.session.add(device)
        await self.session.flush()
        session_cookie = secrets.token_urlsafe(32)
        self.session.add(DesktopSession(
            id=str(uuid4()), device_id=device.id,
            refresh_token_hash=self.desktop._hash("pwa-cookie", session_cookie),
            expires_at=_now() + timedelta(seconds=PWA_SESSION_AGE_SECONDS),
            last_seen_at=_now(),
        ))
        row.status = "consumed"
        row.consumed_at = _now()
        await self.session.commit()
        return session_cookie

    async def actor(self, cookie: str | None):
        require_pwa_enabled(self.settings)
        if not cookie or not isinstance(cookie, str) or not 32 <= len(cookie) <= 200:
            raise PwaAuthError("pwa_session_required")
        hashed = self.desktop._hash("pwa-cookie", cookie)
        result = await self.session.execute(
            select(DesktopSession, DesktopDevice, User)
            .join(DesktopDevice, DesktopSession.device_id == DesktopDevice.id)
            .join(User, DesktopDevice.user_id == User.id)
            .where(DesktopSession.refresh_token_hash == hashed, DesktopDevice.platform == PWA_PLATFORM)
        )
        row = result.one_or_none()
        if row is None:
            raise PwaAuthError("pwa_session_required")
        session, device, user = row
        if (
            session.revoked_at is not None or device.revoked_at is not None
            or (_aware(session.expires_at) or _now()) <= _now()
            or UserAccessStateService.classify(user) == UserAccessState.BLOCKED
        ):
            raise PwaAuthError("pwa_session_required")
        return user, session

    def csrf(self, cookie: str) -> str:
        return self.desktop._hash("pwa-csrf", cookie)

    async def logout(self, cookie: str, csrf: str):
        if not isinstance(csrf, str) or not hmac.compare_digest(self.csrf(cookie), csrf):
            raise PwaAuthError("pwa_csrf_invalid", status_code=403)
        _, session = await self.actor(cookie)
        session.revoked_at = _now()
        await self.session.commit()
