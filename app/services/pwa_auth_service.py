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

from sqlalchemy import select, update, or_

from app.db.models.desktop import DesktopDevice, DesktopLinkRequest, DesktopSession
from app.db.models.user import User
from app.db.models.user_identity import UserIdentity
from app.public_site.render import public_origin
from app.services.desktop_auth_service import DesktopAuthService
from app.services.native_oauth_service import NativeOAuthService, redirect_base_url
from app.services.user_access_state_service import UserAccessState, UserAccessStateService

PWA_PLATFORM = "pwa"
PWA_SESSION_COOKIE = "__Host-hskai-pwa"
PWA_OAUTH_COOKIE = "__Host-hskai-pwa-oauth"
PWA_TELEGRAM_COOKIE = "__Host-hskai-pwa-telegram"
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
    # The page's same-origin/CSRF boundary is the canonical public website.
    # OAuth providers may use a different registered callback host; keep that
    # redirect configuration isolated in NativeOAuthService.
    public_site_url = str(getattr(settings_obj, "PUBLIC_SITE_URL", "") or "").strip()
    if public_site_url:
        try:
            return public_origin(settings_obj)
        except ValueError:
            return ""
    return redirect_base_url(settings_obj)


def pwa_enabled(settings_obj) -> bool:
    return bool(getattr(settings_obj, "PWA_AUTH_ENABLED", False)) and bool(pwa_origin(settings_obj))


def require_pwa_enabled(settings_obj) -> None:
    if not pwa_enabled(settings_obj):
        raise PwaAuthError("pwa_auth_unavailable", status_code=503)


def require_same_origin(request, settings_obj) -> None:
    allowed = {origin for origin in (
        pwa_origin(settings_obj),
        redirect_base_url(settings_obj),
    ) if origin}
    if not allowed or request.headers.get("Origin") not in allowed:
        raise PwaAuthError("pwa_origin_invalid", status_code=403)


class PwaAuthService:
    def __init__(self, session, settings_obj):
        self.session = session
        self.settings = settings_obj
        self.native = NativeOAuthService(session, settings_obj)
        self.desktop = DesktopAuthService(session, settings_obj)

    async def start(
        self, *, provider: str, language: str | None = None,
        replace_cookie: str | None = None,
    ) -> tuple[str, str]:
        require_pwa_enabled(self.settings)
        if provider not in {"google", "apple"}:
            raise PwaAuthError("pwa_provider_invalid", status_code=422)
        # Apple returns via a cross-site POST. Safari omits SameSite=Lax
        # session cookies there, so record the already-verified prior session
        # server-side at OAuth *start*. The ID alone grants no authority: the
        # callback still needs the one-use state and same-browser OAuth proof.
        previous_session_id = None
        if replace_cookie:
            try:
                _, previous = await self.actor(replace_cookie)
                previous_session_id = previous.id
            except PwaAuthError:
                pass  # Stale/invalid session cannot bind a prior owner.
        proof = secrets.token_urlsafe(32)
        started = await self.native.start(
            provider=provider, mode="browser_redirect", platform=PWA_PLATFORM,
            app_version="1.0.0", installation_key=proof,
            language=language if language in {"uz", "ru", "tj"} else None,
            bind_session_id=previous_session_id,
        )
        if not started.authorize_url:
            raise PwaAuthError("pwa_auth_unavailable", status_code=503)
        # The native polling secret never leaves the server in the PWA flow.
        return started.authorize_url, proof

    async def start_telegram(self, *, language: str | None = None) -> tuple[str, str, str]:
        """Browser proof is HttpOnly; bot sees only a one-use UUID deep link."""
        require_pwa_enabled(self.settings)
        proof = secrets.token_urlsafe(32)
        started = await self.desktop.start_link(
            platform=PWA_PLATFORM, app_version="1.0.0",
            installation_key=proof, flow="telegram", intent="signin",
            language=language if language in {"uz", "ru", "tj"} else None,
        )
        url = str(started.get("bot_deep_link") or "")
        if not url.startswith("https://t.me/"):
            raise PwaAuthError("pwa_telegram_unavailable", status_code=503)
        return str(started["link_request_id"]), url, proof

    async def claim_telegram(
        self, *, request_id: str, proof: str | None,
        replace_cookie: str | None = None,
    ) -> tuple[str, str | None]:
        """Status polling never issues native tokens and accepts no URL-only proof.

        A DB row lock, browser-only cookie and confirmed Telegram owner are all
        required before a one-time PWA cookie is created.
        """
        require_pwa_enabled(self.settings)
        from uuid import UUID
        try:
            request_id = str(UUID(request_id))
        except (ValueError, TypeError, AttributeError):
            raise PwaAuthError("pwa_telegram_invalid", status_code=422)
        if not isinstance(proof, str) or not 32 <= len(proof) <= 200:
            raise PwaAuthError("pwa_telegram_proof_invalid")
        row = (await self.session.execute(
            select(DesktopLinkRequest).where(
                DesktopLinkRequest.id == request_id
            ).with_for_update().execution_options(populate_existing=True)
        )).scalar_one_or_none()
        if (
            row is None or row.platform != PWA_PLATFORM
            or row.intent != "signin" or row.flow != "telegram"
            or not hmac.compare_digest(
                str(row.installation_key_hash or ""),
                self.desktop._hash("installation", proof),
            )
        ):
            raise PwaAuthError("pwa_telegram_proof_invalid")
        if (_aware(row.expires_at) or _now()) <= _now():
            raise PwaAuthError("pwa_telegram_expired", status_code=410)
        if row.status == "pending" and row.consumed_at is None:
            return "pending", None
        if (
            row.status != "approved" or row.consumed_at is not None
            or not row.approved_user_id or not row.approved_telegram_id
        ):
            raise PwaAuthError("pwa_telegram_not_approved")
        user = (await self.session.execute(
            select(User).where(User.id == row.approved_user_id).with_for_update()
        )).scalar_one_or_none()
        if (
            user is None or UserAccessStateService.classify(user) == UserAccessState.BLOCKED
            or int(user.telegram_id or 0) != int(row.approved_telegram_id)
        ):
            raise PwaAuthError("pwa_telegram_owner_invalid", status_code=403)
        return "complete", await self._mint_session(user, row, replace_cookie=replace_cookie)

    async def _mint_session(
        self, user: User, row: DesktopLinkRequest, *, replace_cookie: str | None = None,
    ) -> str:
        device = DesktopDevice(
            id=str(uuid4()), user_id=user.id,
            telegram_id=user.telegram_id,
            installation_key_hash=row.installation_key_hash,
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
        # Replace only this browser's previous PWA session. Never revoke other
        # installed/browser sessions, Telegram, Android, or Desktop sessions.
        # Do it in the same transaction as the newly minted session.
        previous_sessions = []
        if row.bind_session_id:
            previous_sessions.append(DesktopSession.id == row.bind_session_id)
        if isinstance(replace_cookie, str) and 32 <= len(replace_cookie) <= 200:
            previous_sessions.append(
                DesktopSession.refresh_token_hash
                == self.desktop._hash("pwa-cookie", replace_cookie)
            )
        if previous_sessions:
            previous_device_ids = (await self.session.scalars(
                select(DesktopSession.device_id)
                .join(DesktopDevice, DesktopSession.device_id == DesktopDevice.id)
                .where(or_(*previous_sessions), DesktopDevice.platform == PWA_PLATFORM)
                .distinct()
            )).all()
            if previous_device_ids:
                from app.services.learner_pwa_push import revoke_device_subscriptions
                for previous_device_id in previous_device_ids:
                    await revoke_device_subscriptions(self.session, previous_device_id)
            await self.session.execute(
                update(DesktopSession)
                .where(
                    or_(*previous_sessions),
                    DesktopSession.device_id.in_(
                        select(DesktopDevice.id).where(
                            DesktopDevice.platform == PWA_PLATFORM
                        )
                    ),
                    DesktopSession.revoked_at.is_(None),
                )
                .values(revoked_at=_now())
            )
        row.status = "consumed"
        row.consumed_at = _now()
        await self.session.commit()
        return session_cookie

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

    async def consume_callback(
        self, *, provider: str, state: str, proof: str | None,
        replace_cookie: str | None = None,
    ) -> str:
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

        return await self._mint_session(user, row, replace_cookie=replace_cookie)

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

    async def mutation_actor(self, cookie: str | None, csrf: str | None):
        """Validate browser authority before any state-changing PWA route.

        Callers must additionally enforce the configured same-origin check.
        Telegram-signed and native bearer transports do not use this method.
        """
        user, session = await self.actor(cookie)
        if not isinstance(csrf, str) or not csrf.isascii() or not hmac.compare_digest(
            self.csrf(cookie), csrf
        ):
            raise PwaAuthError("pwa_csrf_invalid", status_code=403)
        return user, session

    async def logout(self, cookie: str, csrf: str):
        _, session = await self.mutation_actor(cookie, csrf)
        from app.services.learner_pwa_push import revoke_device_subscriptions
        await revoke_device_subscriptions(self.session, session.device_id)
        session.revoked_at = _now()
        await self.session.commit()
