import base64
import hashlib
import hmac
import json
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import and_, delete, func, or_, select, text

from app.db.models.desktop import DesktopDevice, DesktopLinkRequest, DesktopSession
from app.db.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.course_miniapp_analytics_service import (
    CourseMiniAppAnalyticsService,
)
from app.services.desktop_update_service import parse_desktop_semver
from app.services.user_access_state_service import UserAccessStateService


DISPLAY_CODE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
DESKTOP_PLATFORMS = {"macos", "windows"}
MOBILE_PLATFORMS = {"android"}
# Every native client allowed to open a Telegram device link. The desktop-only
# set stays separate so desktop consumers (downloads, release manifest, admin
# desktop statistics) keep their current meaning and are not silently widened.
NATIVE_PLATFORMS = DESKTOP_PLATFORMS | MOBILE_PLATFORMS
logger = logging.getLogger(__name__)

# A transaction-scoped PostgreSQL advisory lock makes the unauthenticated
# link-start count-and-insert sequence atomic across workers and replicas. The
# number is a fixed application namespace, not derived from user input.
LINK_START_RATE_LIMIT_LOCK_KEY = 1_215_521_089


class DesktopAuthError(RuntimeError):
    def __init__(self, code: str, *, status_code: int):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


@dataclass(frozen=True)
class DesktopAuthContext:
    session: DesktopSession
    device: DesktopDevice
    user: User
    claims: dict[str, Any]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _b64_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _b64_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def analytics_prefix(platform: str | None) -> str:
    """Analytics namespace for a native platform.

    Android must never be counted as a desktop install, so its lifecycle
    events, analytics source and dedupe keys use their own prefix. Desktop
    platforms keep the exact names they already emit in production.
    """

    normalized = str(platform or "").strip().lower()
    return "android" if normalized in MOBILE_PLATFORMS else "desktop"


class DesktopAuthService:
    def __init__(self, session, settings_obj):
        self.session = session
        self.settings = settings_obj

    def _signing_secret(self) -> bytes:
        value = str(
            getattr(self.settings, "DESKTOP_AUTH_SIGNING_SECRET", "") or ""
        ).encode()
        if len(value) < 32:
            raise DesktopAuthError(
                "desktop_auth_unavailable",
                status_code=503,
            )
        return value

    def _hash(self, purpose: str, value: str) -> str:
        return hmac.new(
            self._signing_secret(),
            f"{purpose}:{value}".encode(),
            hashlib.sha256,
        ).hexdigest()

    def _link_ttl(self) -> int:
        return max(
            120,
            min(
                1800,
                int(getattr(self.settings, "DESKTOP_AUTH_LINK_TTL_SECONDS", 600)),
            ),
        )

    def _access_ttl(self) -> int:
        return max(
            300,
            min(
                3600,
                int(getattr(self.settings, "DESKTOP_AUTH_ACCESS_TTL_SECONDS", 900)),
            ),
        )

    def _refresh_ttl(self) -> timedelta:
        days = max(
            1,
            min(
                90,
                int(getattr(self.settings, "DESKTOP_AUTH_REFRESH_TTL_DAYS", 30)),
            ),
        )
        return timedelta(days=days)

    def _record_retention(self) -> timedelta:
        days = max(
            1,
            min(
                365,
                int(
                    getattr(
                        self.settings,
                        "DESKTOP_AUTH_RECORD_RETENTION_DAYS",
                        30,
                    )
                ),
            ),
        )
        return timedelta(days=days)

    async def _acquire_link_start_rate_limit_lock(self) -> None:
        """Serialize public link-start admission on the production database.

        Railway uses PostgreSQL. SQLite is kept as a lightweight local/test
        backend and already serializes its writes; PostgreSQL needs an explicit
        cross-process lock so concurrent replicas cannot all pass the same
        count before inserting.
        """

        bind = self.session.get_bind()
        dialect = str(getattr(getattr(bind, "dialect", None), "name", ""))
        if dialect == "postgresql":
            await self.session.execute(
                text("SELECT pg_advisory_xact_lock(:lock_key)"),
                {"lock_key": LINK_START_RATE_LIMIT_LOCK_KEY},
            )

    async def cleanup_expired_records(
        self,
        *,
        now: datetime | None = None,
    ) -> dict[str, int]:
        """Delete native-auth records only after the configured retention.

        Devices are intentionally retained because they hold installation
        ownership and first-open analytics. Only already-expired link requests
        and expired/revoked sessions are eligible.
        """

        cleanup_now = _as_utc(now) or _utcnow()
        cutoff = cleanup_now - self._record_retention()
        link_result = await self.session.execute(
            delete(DesktopLinkRequest).where(
                DesktopLinkRequest.expires_at <= cutoff,
            )
        )
        session_result = await self.session.execute(
            delete(DesktopSession).where(
                or_(
                    DesktopSession.expires_at <= cutoff,
                    and_(
                        DesktopSession.revoked_at.is_not(None),
                        DesktopSession.revoked_at <= cutoff,
                    ),
                )
            )
        )
        await self.session.commit()
        return {
            "link_requests_deleted": max(0, int(link_result.rowcount or 0)),
            "sessions_deleted": max(0, int(session_result.rowcount or 0)),
        }

    @staticmethod
    def _display_code() -> str:
        return "".join(secrets.choice(DISPLAY_CODE_ALPHABET) for _ in range(8))

    @staticmethod
    def _refresh_token() -> str:
        return "pomp_r1_" + secrets.token_urlsafe(48)

    def _access_token(
        self,
        *,
        desktop_session: DesktopSession,
        device: DesktopDevice,
    ) -> tuple[str, int]:
        now = int(_utcnow().timestamp())
        ttl = self._access_ttl()
        header = {"alg": "HS256", "typ": "POMP"}
        payload = {
            "typ": "access",
            "sid": desktop_session.id,
            "did": device.id,
            "uid": device.user_id,
            "iat": now,
            "exp": now + ttl,
            "jti": uuid4().hex,
        }
        encoded_header = _b64_encode(
            json.dumps(header, separators=(",", ":"), sort_keys=True).encode()
        )
        encoded_payload = _b64_encode(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        )
        signed = f"{encoded_header}.{encoded_payload}"
        signature = hmac.new(
            self._signing_secret(),
            signed.encode(),
            hashlib.sha256,
        ).digest()
        return f"{signed}.{_b64_encode(signature)}", ttl

    def _access_claims(self, token: str) -> dict[str, Any]:
        if not token or len(token) > 4096:
            raise DesktopAuthError("desktop_access_invalid", status_code=401)
        try:
            encoded_header, encoded_payload, encoded_signature = token.split(".")
            signed = f"{encoded_header}.{encoded_payload}"
            expected = hmac.new(
                self._signing_secret(),
                signed.encode(),
                hashlib.sha256,
            ).digest()
            if not hmac.compare_digest(expected, _b64_decode(encoded_signature)):
                raise ValueError("signature")
            header = json.loads(_b64_decode(encoded_header))
            payload = json.loads(_b64_decode(encoded_payload))
            if (
                header != {"alg": "HS256", "typ": "POMP"}
                or payload.get("typ") != "access"
                or int(payload.get("exp") or 0) <= int(_utcnow().timestamp())
                or not all(payload.get(key) for key in ("sid", "did", "uid"))
            ):
                raise ValueError("claims")
            return payload
        except DesktopAuthError:
            raise
        except Exception as exc:
            raise DesktopAuthError(
                "desktop_access_invalid", status_code=401
            ) from exc

    async def start_link(
        self,
        *,
        platform: str,
        app_version: str,
        installation_key: str,
    ) -> dict[str, Any]:
        self._signing_secret()
        if platform not in NATIVE_PLATFORMS:
            raise DesktopAuthError("desktop_platform_invalid", status_code=422)
        if not 32 <= len(installation_key) <= 200:
            raise DesktopAuthError(
                "desktop_installation_key_invalid", status_code=422
            )

        await self._acquire_link_start_rate_limit_lock()
        now = _utcnow()
        installation_hash = self._hash("installation", installation_key)
        global_limit = max(
            1,
            int(
                getattr(
                    self.settings,
                    "DESKTOP_AUTH_LINK_GLOBAL_RATE_LIMIT_COUNT",
                    120,
                )
            ),
        )
        global_window = max(
            10,
            int(
                getattr(
                    self.settings,
                    "DESKTOP_AUTH_LINK_GLOBAL_RATE_LIMIT_WINDOW_SECONDS",
                    60,
                )
            ),
        )
        global_result = await self.session.execute(
            select(func.count())
            .select_from(DesktopLinkRequest)
            .where(
                DesktopLinkRequest.created_at
                >= now - timedelta(seconds=global_window)
            )
        )
        if int(global_result.scalar() or 0) >= global_limit:
            raise DesktopAuthError("desktop_link_rate_limited", status_code=429)
        recent_result = await self.session.execute(
            select(func.count())
            .select_from(DesktopLinkRequest)
            .where(
                DesktopLinkRequest.installation_key_hash == installation_hash,
                DesktopLinkRequest.created_at >= now - timedelta(minutes=5),
            )
        )
        if int(recent_result.scalar() or 0) >= 5:
            raise DesktopAuthError("desktop_link_rate_limited", status_code=429)

        display_code = self._display_code()
        polling_secret = secrets.token_urlsafe(32)
        link_request = DesktopLinkRequest(
            id=str(uuid4()),
            display_code_hash=self._hash("display-code", display_code),
            polling_secret_hash=self._hash("polling", polling_secret),
            installation_key_hash=installation_hash,
            platform=platform,
            app_version=app_version,
            status="pending",
            expires_at=now + timedelta(seconds=self._link_ttl()),
        )
        self.session.add(link_request)
        await self.session.commit()

        username = (
            str(getattr(self.settings, "BOT_USERNAME", "") or "darsi_chini_bot")
            .strip()
            .lstrip("@")
            or "darsi_chini_bot"
        )
        return {
            "ok": True,
            "status": "pending",
            "link_request_id": link_request.id,
            "display_code": display_code,
            "polling_secret": polling_secret,
            # The display code must be typed manually in the private bot chat.
            # Never place it in a Telegram deep-link, browser history or logs.
            "bot_deep_link": f"https://t.me/{username}?start=desktop_link",
            "expires_in": self._link_ttl(),
        }

    async def approve_link(
        self,
        *,
        display_code: str,
        telegram_id: int,
    ) -> dict[str, Any]:
        normalized = str(display_code or "").strip().upper().replace("-", "")
        if len(normalized) != 8:
            raise DesktopAuthError("desktop_link_invalid", status_code=404)
        result = await self.session.execute(
            select(DesktopLinkRequest)
            .where(
                DesktopLinkRequest.display_code_hash
                == self._hash("display-code", normalized)
            )
            .with_for_update()
        )
        link_request = result.scalar_one_or_none()
        now = _utcnow()
        if not link_request:
            raise DesktopAuthError("desktop_link_invalid", status_code=404)
        if (_as_utc(link_request.expires_at) or now) <= now:
            link_request.status = "expired"
            await self.session.commit()
            raise DesktopAuthError("desktop_link_expired", status_code=410)
        if link_request.status == "approved":
            if int(link_request.approved_telegram_id or 0) == int(telegram_id):
                await self.session.commit()
                return {
                    "ok": True,
                    "duplicate": True,
                    "platform": link_request.platform,
                }
            raise DesktopAuthError("desktop_link_already_approved", status_code=409)
        if link_request.status != "pending" or link_request.consumed_at is not None:
            raise DesktopAuthError("desktop_link_consumed", status_code=409)
        if (
            link_request.approved_telegram_id is not None
            and int(link_request.approved_telegram_id) != int(telegram_id)
        ):
            raise DesktopAuthError("desktop_link_invalid", status_code=403)

        user = await UserRepository(self.session).get_by_telegram_id_for_update(
            telegram_id
        )
        if not user:
            raise DesktopAuthError("desktop_user_not_found", status_code=404)
        link_request.status = "approved"
        link_request.approved_user_id = user.id
        link_request.approved_telegram_id = user.telegram_id
        link_request.approved_at = now
        await self.session.commit()
        return {
            "ok": True,
            "duplicate": False,
            "platform": link_request.platform,
        }

    async def link_preview(
        self,
        *,
        display_code: str,
        telegram_id: int | None = None,
    ) -> dict[str, Any]:
        """Return display-safe details before the Telegram user consents."""

        self._signing_secret()
        normalized = str(display_code or "").strip().upper().replace("-", "")
        if len(normalized) != 8:
            raise DesktopAuthError("desktop_link_invalid", status_code=404)
        query = select(DesktopLinkRequest).where(
            DesktopLinkRequest.display_code_hash
            == self._hash("display-code", normalized)
        )
        if telegram_id is not None:
            query = query.with_for_update()
        result = await self.session.execute(query)
        link_request = result.scalar_one_or_none()
        now = _utcnow()
        if (
            not link_request
            or link_request.status != "pending"
            or link_request.consumed_at is not None
        ):
            raise DesktopAuthError("desktop_link_invalid", status_code=404)
        expires_at = _as_utc(link_request.expires_at) or now
        if expires_at <= now:
            raise DesktopAuthError("desktop_link_expired", status_code=410)
        if telegram_id is not None:
            if (
                link_request.approved_telegram_id is not None
                and int(link_request.approved_telegram_id) != int(telegram_id)
            ):
                raise DesktopAuthError("desktop_link_invalid", status_code=403)
            link_request.approved_telegram_id = int(telegram_id)
            await self.session.commit()
        return {
            "ok": True,
            "display_code": normalized,
            "platform": link_request.platform,
            "app_version": link_request.app_version,
            "expires_in": max(0, int((expires_at - now).total_seconds())),
        }

    async def cancel_link(
        self,
        *,
        display_code: str,
        telegram_id: int | None = None,
    ) -> dict[str, Any]:
        """Cancel a pending link from the explicit Telegram confirmation."""

        self._signing_secret()
        normalized = str(display_code or "").strip().upper().replace("-", "")
        if len(normalized) != 8:
            raise DesktopAuthError("desktop_link_invalid", status_code=404)
        result = await self.session.execute(
            select(DesktopLinkRequest)
            .where(
                DesktopLinkRequest.display_code_hash
                == self._hash("display-code", normalized)
            )
            .with_for_update()
        )
        link_request = result.scalar_one_or_none()
        now = _utcnow()
        if not link_request:
            raise DesktopAuthError("desktop_link_invalid", status_code=404)
        if (_as_utc(link_request.expires_at) or now) <= now:
            link_request.status = "expired"
            await self.session.commit()
            raise DesktopAuthError("desktop_link_expired", status_code=410)
        if link_request.status != "pending" or link_request.consumed_at is not None:
            raise DesktopAuthError("desktop_link_consumed", status_code=409)
        if (
            telegram_id is not None
            and link_request.approved_telegram_id is not None
            and int(link_request.approved_telegram_id) != int(telegram_id)
        ):
            raise DesktopAuthError("desktop_link_invalid", status_code=403)
        link_request.status = "cancelled"
        await self.session.commit()
        return {"ok": True}

    async def poll_link(
        self,
        *,
        link_request_id: str,
        polling_secret: str,
    ) -> dict[str, Any]:
        if not 32 <= len(polling_secret) <= 512:
            raise DesktopAuthError("desktop_link_invalid", status_code=401)
        result = await self.session.execute(
            select(DesktopLinkRequest)
            .where(DesktopLinkRequest.id == link_request_id)
            .with_for_update()
        )
        link_request = result.scalar_one_or_none()
        now = _utcnow()
        if not link_request or not hmac.compare_digest(
            str(getattr(link_request, "polling_secret_hash", "") or ""),
            self._hash("polling", polling_secret),
        ):
            raise DesktopAuthError("desktop_link_invalid", status_code=401)
        if (_as_utc(link_request.expires_at) or now) <= now:
            link_request.status = "expired"
            await self.session.commit()
            raise DesktopAuthError("desktop_link_expired", status_code=410)
        if link_request.consumed_at is not None or link_request.status == "consumed":
            raise DesktopAuthError("desktop_link_consumed", status_code=409)
        if link_request.status == "pending":
            return {
                "ok": True,
                "status": "pending",
                "expires_in": max(
                    0,
                    int(((_as_utc(link_request.expires_at) or now) - now).total_seconds()),
                ),
            }
        if (
            link_request.status != "approved"
            or not link_request.approved_user_id
            or not link_request.approved_telegram_id
        ):
            raise DesktopAuthError("desktop_link_invalid", status_code=409)

        device_result = await self.session.execute(
            select(DesktopDevice)
            .where(
                DesktopDevice.installation_key_hash
                == link_request.installation_key_hash
            )
            .with_for_update()
        )
        device = device_result.scalar_one_or_none()
        if device and device.user_id != link_request.approved_user_id:
            if device.revoked_at is None:
                raise DesktopAuthError(
                    "desktop_device_bound_to_other_user", status_code=409
                )
            device.user_id = int(link_request.approved_user_id)
            device.telegram_id = int(link_request.approved_telegram_id)
            device.revoked_at = None
            device.first_open_at = None
        elif not device:
            device = DesktopDevice(
                id=str(uuid4()),
                user_id=int(link_request.approved_user_id),
                telegram_id=int(link_request.approved_telegram_id),
                installation_key_hash=link_request.installation_key_hash,
                platform=link_request.platform,
                app_version=link_request.app_version,
            )
            self.session.add(device)
            await self.session.flush()
        else:
            device.platform = link_request.platform
            device.app_version = link_request.app_version
            device.revoked_at = None

        refresh_token = self._refresh_token()
        desktop_session = DesktopSession(
            id=str(uuid4()),
            device_id=device.id,
            refresh_token_hash=self._hash("refresh", refresh_token),
            expires_at=now + self._refresh_ttl(),
            last_seen_at=now,
        )
        self.session.add(desktop_session)
        await self.session.flush()
        access_token, access_expires_in = self._access_token(
            desktop_session=desktop_session,
            device=device,
        )
        link_request.status = "consumed"
        link_request.consumed_at = now
        # Persist the device/session/token state before optional analytics.
        # Course analytics is best-effort and must never roll back credentials
        # that have already been returned to the native client.
        await self.session.commit()
        prefix = analytics_prefix(device.platform)
        try:
            await CourseMiniAppAnalyticsService(self.session).record_server_event(
                event_name=f"{prefix}_session_linked",
                telegram_id=device.telegram_id,
                user_id=device.user_id,
                source=f"{prefix}_auth",
                session_id=desktop_session.id,
                dedupe_key=f"{prefix}-link:{link_request.id}",
                payload={
                    "platform": device.platform,
                    "app_version": device.app_version,
                    "device_id": device.id,
                },
            )
            await self.session.commit()
        except Exception:
            logger.exception(
                "Desktop session linked but analytics failed for device=%s",
                device.id,
            )
            await self.session.rollback()
        return {
            "ok": True,
            "status": "linked",
            "access_token": access_token,
            "access_expires_in": access_expires_in,
            "refresh_token": refresh_token,
            "refresh_expires_in": int(self._refresh_ttl().total_seconds()),
        }

    async def refresh(self, refresh_token: str) -> dict[str, Any]:
        if not 32 <= len(refresh_token) <= 512:
            raise DesktopAuthError("desktop_refresh_invalid", status_code=401)
        token_hash = self._hash("refresh", refresh_token)
        result = await self.session.execute(
            select(DesktopSession)
            .where(
                or_(
                    DesktopSession.refresh_token_hash == token_hash,
                    DesktopSession.previous_refresh_token_hash == token_hash,
                )
            )
            .with_for_update()
        )
        desktop_session = result.scalar_one_or_none()
        if not desktop_session:
            raise DesktopAuthError("desktop_refresh_invalid", status_code=401)
        if hmac.compare_digest(
            str(desktop_session.previous_refresh_token_hash or ""),
            token_hash,
        ):
            desktop_session.revoked_at = _utcnow()
            await self.session.commit()
            raise DesktopAuthError(
                "desktop_refresh_reuse_detected", status_code=401
            )

        device_result = await self.session.execute(
            select(DesktopDevice)
            .where(DesktopDevice.id == desktop_session.device_id)
            .with_for_update()
        )
        device = device_result.scalar_one_or_none()
        now = _utcnow()
        if (
            not device
            or device.revoked_at is not None
            or desktop_session.revoked_at is not None
            or (_as_utc(desktop_session.expires_at) or now) <= now
        ):
            raise DesktopAuthError("desktop_session_revoked", status_code=401)

        new_refresh = self._refresh_token()
        desktop_session.previous_refresh_token_hash = (
            desktop_session.refresh_token_hash
        )
        desktop_session.refresh_token_hash = self._hash("refresh", new_refresh)
        desktop_session.rotated_at = now
        desktop_session.last_seen_at = now
        device.last_seen_at = now
        access_token, access_expires_in = self._access_token(
            desktop_session=desktop_session,
            device=device,
        )
        await self.session.commit()
        return {
            "ok": True,
            "access_token": access_token,
            "access_expires_in": access_expires_in,
            "refresh_token": new_refresh,
            "refresh_expires_in": max(
                0,
                int(((_as_utc(desktop_session.expires_at) or now) - now).total_seconds()),
            ),
        }

    async def authenticate(self, access_token: str) -> DesktopAuthContext:
        claims = self._access_claims(access_token)
        session_result = await self.session.execute(
            select(DesktopSession).where(DesktopSession.id == claims["sid"])
        )
        desktop_session = session_result.scalar_one_or_none()
        if (
            not desktop_session
            or desktop_session.revoked_at is not None
            or (_as_utc(desktop_session.expires_at) or _utcnow()) <= _utcnow()
        ):
            raise DesktopAuthError("desktop_session_revoked", status_code=401)

        device_result = await self.session.execute(
            select(DesktopDevice).where(DesktopDevice.id == claims["did"])
        )
        device = device_result.scalar_one_or_none()
        if (
            not device
            or device.revoked_at is not None
            or device.id != desktop_session.device_id
            or int(device.user_id) != int(claims["uid"])
        ):
            raise DesktopAuthError("desktop_session_revoked", status_code=401)
        user_result = await self.session.execute(
            select(User).where(User.id == device.user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise DesktopAuthError("desktop_user_not_found", status_code=401)
        return DesktopAuthContext(
            session=desktop_session,
            device=device,
            user=user,
            claims=claims,
        )

    async def revoke(
        self,
        access_token: str,
        *,
        revoke_device: bool,
    ) -> dict[str, Any]:
        context = await self.authenticate(access_token)
        now = _utcnow()
        context.session.revoked_at = now
        if revoke_device:
            context.device.revoked_at = now
            result = await self.session.execute(
                select(DesktopSession)
                .where(DesktopSession.device_id == context.device.id)
                .with_for_update()
            )
            for desktop_session in result.scalars().all():
                desktop_session.revoked_at = now
        await self.session.commit()
        return {"ok": True, "device_revoked": revoke_device}

    async def bootstrap(
        self,
        access_token: str,
        *,
        app_version: str | None = None,
    ) -> dict[str, Any]:
        context = await self.authenticate(access_token)
        now = _utcnow()
        prefix = analytics_prefix(context.device.platform)
        was_opened = context.device.first_open_at is not None
        previous_version = str(context.device.app_version or "").strip()
        reported_version = str(app_version or "").strip()
        version_upgraded = False
        if reported_version and reported_version != previous_version:
            try:
                previous_semver = parse_desktop_semver(previous_version)
                reported_semver = parse_desktop_semver(reported_version)
            except ValueError:
                reported_version = ""
            else:
                version_upgraded = (
                    was_opened and reported_semver > previous_semver
                )
                context.device.app_version = reported_version
                if version_upgraded:
                    await CourseMiniAppAnalyticsService(
                        self.session
                    ).record_server_event(
                        event_name=f"{prefix}_update_installed",
                        telegram_id=context.user.telegram_id,
                        user_id=context.user.id,
                        source=f"{prefix}_app",
                        session_id=context.session.id,
                        dedupe_key=(
                            f"{prefix}-update:{context.device.id}:"
                            f"{reported_version}"
                        ),
                        payload={
                            "platform": context.device.platform,
                            "app_version": reported_version,
                            "from_version": previous_version,
                            "to_version": reported_version,
                            "device_id": context.device.id,
                        },
                    )
        first_open = context.device.first_open_at is None
        if first_open:
            context.device.first_open_at = now
            await CourseMiniAppAnalyticsService(self.session).record_server_event(
                event_name=f"{prefix}_first_open",
                telegram_id=context.user.telegram_id,
                user_id=context.user.id,
                source=f"{prefix}_app",
                session_id=context.session.id,
                dedupe_key=f"{prefix}-first-open:{context.device.id}",
                payload={
                    "platform": context.device.platform,
                    "app_version": context.device.app_version,
                    "device_id": context.device.id,
                },
            )
        context.device.last_seen_at = now
        context.session.last_seen_at = now
        await CourseMiniAppAnalyticsService(self.session).record_server_event(
            event_name=f"{prefix}_app_opened",
            telegram_id=context.user.telegram_id,
            user_id=context.user.id,
            source=f"{prefix}_app",
            session_id=context.session.id,
            dedupe_key=(
                f"{prefix}-open:{context.device.id}:{now.date().isoformat()}"
            ),
            payload={
                "platform": context.device.platform,
                "app_version": context.device.app_version,
                "device_id": context.device.id,
            },
        )
        await self.session.commit()
        display_name = str(
            context.user.full_name or context.user.username or "HSK Student"
        ).strip()[:60]
        language = str(context.user.language or "ru").lower()
        if language not in {"uz", "ru", "tj"}:
            language = "ru"
        level = str(context.user.level or "hsk1").lower()
        if level == "beginner":
            level = "hsk1"
        if level not in {"hsk1", "hsk2", "hsk3", "hsk4"}:
            level = "hsk1"
        return {
            "ok": True,
            "authenticated": True,
            "first_open": first_open,
            "version_upgraded": version_upgraded,
            "device": {
                "id": context.device.id,
                "platform": context.device.platform,
                "app_version": context.device.app_version,
            },
            "user": {
                "name": display_name,
                "language": language,
                "level": level,
                "access_state": UserAccessStateService.classify(context.user),
                "is_paid": UserAccessStateService.is_paid(context.user),
            },
        }
