import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import unquote, urlencode, urlsplit
from uuid import uuid4

from sqlalchemy import func, select

from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.repositories.user_repo import UserRepository
from app.services.course_miniapp_analytics_service import CourseMiniAppAnalyticsService


logger = logging.getLogger(__name__)

PLATFORMS = ("macos", "windows")
SOURCES = ("profile", "home_prompt", "lesson_end_promo", "ad_promo")
REQUEST_TOKEN_RE = re.compile(r"^[0-9a-f]{32}$")
SAFE_FILE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,119}$")
PROMO_COOLDOWN_DAYS = 14
PROMO_COMPLETION_EVENTS = (
    "section_completed",
    "lesson_completed",
    "book_lesson_completed",
)
DEFAULT_FILE_NAMES = {
    "macos": "Pomp-HSK-AI-universal.dmg",
    "windows": "Pomp-HSK-AI-x64-setup.exe",
}
EXPECTED_SUFFIXES = {
    "macos": ".dmg",
    "windows": ".exe",
}


class DesktopDownloadError(RuntimeError):
    def __init__(
        self,
        code: str,
        *,
        status_code: int,
        platform: str | None = None,
        retry_after_seconds: int | None = None,
    ):
        super().__init__(code)
        self.code = code
        self.status_code = status_code
        self.platform = platform
        self.retry_after_seconds = retry_after_seconds


def _https_url(value: Any, *, origin_only: bool = False) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parts = urlsplit(raw)
    except ValueError:
        return None
    if (
        parts.scheme.lower() != "https"
        or not parts.hostname
        or parts.username
        or parts.password
        or parts.fragment
    ):
        return None
    if origin_only:
        return f"https://{parts.netloc}".rstrip("/")
    return raw


def _safe_file_name(platform: str, target_url: str | None) -> str | None:
    if platform not in PLATFORMS or not target_url:
        return None
    try:
        candidate = unquote(PurePosixPath(urlsplit(target_url).path).name)
    except (TypeError, ValueError):
        candidate = ""
    expected_suffix = EXPECTED_SUFFIXES[platform]
    if (
        not candidate
        or not SAFE_FILE_NAME_RE.fullmatch(candidate)
        or not candidate.lower().endswith(expected_suffix)
    ):
        candidate = DEFAULT_FILE_NAMES[platform]
    return candidate


@dataclass(frozen=True)
class DesktopReleaseConfig:
    enabled: bool
    public_base_url: str | None
    macos_url: str | None
    windows_url: str | None
    macos_version: str | None
    windows_version: str | None

    @classmethod
    def from_settings(cls, settings_obj: Any) -> "DesktopReleaseConfig":
        public_base = _https_url(
            getattr(settings_obj, "DESKTOP_DOWNLOAD_BASE_URL", "")
            or getattr(settings_obj, "MINI_APP_BASE_URL", ""),
            origin_only=True,
        )
        macos_url = _https_url(getattr(settings_obj, "DESKTOP_MAC_DOWNLOAD_URL", ""))
        windows_url = _https_url(
            getattr(settings_obj, "DESKTOP_WINDOWS_DOWNLOAD_URL", "")
        )
        if macos_url and not urlsplit(macos_url).path.lower().endswith(".dmg"):
            macos_url = None
        if windows_url and not urlsplit(windows_url).path.lower().endswith(".exe"):
            windows_url = None
        enabled = bool(getattr(settings_obj, "DESKTOP_DOWNLOADS_ENABLED", False)) and bool(
            public_base and (macos_url or windows_url)
        )
        return cls(
            enabled=enabled,
            public_base_url=public_base,
            macos_url=macos_url,
            windows_url=windows_url,
            macos_version=(
                str(getattr(settings_obj, "DESKTOP_MAC_VERSION", "") or "").strip()[:40]
                or None
            ),
            windows_version=(
                str(getattr(settings_obj, "DESKTOP_WINDOWS_VERSION", "") or "").strip()[
                    :40
                ]
                or None
            ),
        )

    def target_for(self, platform: str) -> str | None:
        if not self.enabled:
            return None
        if platform == "macos":
            return self.macos_url
        if platform == "windows":
            return self.windows_url
        return None

    def version_for(self, platform: str) -> str | None:
        if platform == "macos":
            return self.macos_version
        if platform == "windows":
            return self.windows_version
        return None

    def file_name_for(self, platform: str) -> str | None:
        return _safe_file_name(platform, self.target_for(platform))

    def status_payload(self) -> dict[str, Any]:
        return {
            "ok": True,
            "enabled": self.enabled,
            "platforms": {
                "macos": bool(self.enabled and self.macos_url),
                "windows": bool(self.enabled and self.windows_url),
            },
            "versions": {
                "macos": self.macos_version,
                "windows": self.windows_version,
            },
        }

    def landing_url(self, platform: str, request_token: str) -> str:
        if not self.target_for(platform) or not self.public_base_url:
            raise DesktopDownloadError(
                "desktop_release_unavailable",
                status_code=503,
                platform=platform,
            )
        return (
            f"{self.public_base_url}/desktop-download?"
            + urlencode({"platform": platform, "request": request_token})
        )

    def tracked_url(self, platform: str, request_token: str | None = None) -> str:
        if not self.target_for(platform) or not self.public_base_url:
            raise DesktopDownloadError(
                "desktop_release_unavailable",
                status_code=503,
                platform=platform,
            )
        query = urlencode({"request": request_token}) if request_token else ""
        return (
            f"{self.public_base_url}/downloads/{platform}"
            + (f"?{query}" if query else "")
        )

    def public_status_payload(self) -> dict[str, Any]:
        payload = self.status_payload()
        payload["downloads"] = {
            platform: (
                self.tracked_url(platform)
                if self.enabled and self.target_for(platform)
                else None
            )
            for platform in PLATFORMS
        }
        payload["files"] = {
            platform: self.file_name_for(platform)
            if self.enabled and self.target_for(platform)
            else None
            for platform in PLATFORMS
        }
        return payload


class DesktopDownloadService:
    def __init__(self, session, settings_obj):
        self.session = session
        self.settings = settings_obj
        self.releases = DesktopReleaseConfig.from_settings(settings_obj)

    async def _user(self, telegram_id: int, *, for_update: bool = False):
        repo = UserRepository(self.session)
        user = (
            await repo.get_by_telegram_id_for_update(telegram_id)
            if for_update
            else await repo.get_by_telegram_id(telegram_id)
        )
        if not user:
            raise DesktopDownloadError("desktop_user_not_found", status_code=404)
        return user

    async def status(self, telegram_id: int) -> dict[str, Any]:
        await self._user(telegram_id)
        payload = self.releases.status_payload()
        payload["promo"] = await self._promo_status(telegram_id)
        return payload

    async def _promo_status(self, telegram_id: int) -> dict[str, Any]:
        completion_result = await self.session.execute(
            select(CourseMiniAppEvent.id)
            .where(
                CourseMiniAppEvent.telegram_id == telegram_id,
                CourseMiniAppEvent.event_name.in_(PROMO_COMPLETION_EVENTS),
            )
            .limit(1)
        )
        has_learning_progress = completion_result.scalar_one_or_none() is not None

        first_open_result = await self.session.execute(
            select(CourseMiniAppEvent.id)
            .where(
                CourseMiniAppEvent.telegram_id == telegram_id,
                CourseMiniAppEvent.event_name == "desktop_first_open",
            )
            .limit(1)
        )
        has_desktop_first_open = first_open_result.scalar_one_or_none() is not None

        last_seen_result = await self.session.execute(
            select(func.max(CourseMiniAppEvent.created_at)).where(
                CourseMiniAppEvent.telegram_id == telegram_id,
                CourseMiniAppEvent.event_name == "desktop_promo_seen",
            )
        )
        last_seen = last_seen_result.scalar_one_or_none()
        if last_seen is not None and last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)

        last_request_result = await self.session.execute(
            select(func.max(CourseMiniAppEvent.created_at)).where(
                CourseMiniAppEvent.telegram_id == telegram_id,
                CourseMiniAppEvent.event_name == "desktop_download_requested",
            )
        )
        last_request = last_request_result.scalar_one_or_none()
        if last_request is not None and last_request.tzinfo is None:
            last_request = last_request.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        cooldown = timedelta(days=PROMO_COOLDOWN_DAYS)
        promo_cooldown_remaining = (
            max(0, int((last_seen + cooldown - now).total_seconds()))
            if last_seen is not None
            else 0
        )
        request_cooldown_remaining = (
            max(0, int((last_request + cooldown - now).total_seconds()))
            if last_request is not None
            else 0
        )
        cooldown_remaining = max(
            promo_cooldown_remaining,
            request_cooldown_remaining,
        )
        feature_enabled = bool(
            getattr(self.settings, "DESKTOP_DOWNLOADS_ENABLED", False)
        )
        release_ready = self.releases.enabled and bool(
            self.releases.macos_url or self.releases.windows_url
        )

        if not feature_enabled:
            reason = "disabled"
        elif not release_ready or not has_learning_progress:
            reason = "not_ready"
        elif has_desktop_first_open:
            reason = "already_installed"
        elif request_cooldown_remaining > 0:
            reason = "recent_request"
        elif promo_cooldown_remaining > 0:
            reason = "cooldown"
        else:
            reason = "eligible"
        eligible = reason == "eligible"

        return {
            "eligible": eligible,
            "reason": reason,
            "cooldown_days": PROMO_COOLDOWN_DAYS,
            "cooldown_remaining_seconds": cooldown_remaining,
            "placements": {
                "profile": release_ready,
                "home_prompt": eligible,
                "lesson_end_promo": eligible,
                "ad_promo": eligible,
            },
        }

    async def _event_by_dedupe(
        self,
        *,
        telegram_id: int,
        event_name: str,
        dedupe_key: str,
    ) -> CourseMiniAppEvent | None:
        result = await self.session.execute(
            select(CourseMiniAppEvent).where(
                CourseMiniAppEvent.telegram_id == telegram_id,
                CourseMiniAppEvent.event_name == event_name,
                CourseMiniAppEvent.dedupe_key == dedupe_key,
            )
        )
        return result.scalar_one_or_none()

    async def _request_event_by_token(
        self, request_token: str
    ) -> CourseMiniAppEvent | None:
        result = await self.session.execute(
            select(CourseMiniAppEvent)
            .where(
                CourseMiniAppEvent.event_name == "desktop_download_requested",
                CourseMiniAppEvent.session_id == request_token,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _recent_requested_count(self, telegram_id: int) -> tuple[int, int, int]:
        count = max(
            1,
            int(getattr(self.settings, "DESKTOP_DOWNLOAD_RATE_LIMIT_COUNT", 3)),
        )
        window_seconds = max(
            60,
            int(
                getattr(
                    self.settings,
                    "DESKTOP_DOWNLOAD_RATE_LIMIT_WINDOW_SECONDS",
                    900,
                )
            ),
        )
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
        result = await self.session.execute(
            select(func.count())
            .select_from(CourseMiniAppEvent)
            .where(
                CourseMiniAppEvent.telegram_id == telegram_id,
                CourseMiniAppEvent.event_name == "desktop_download_requested",
                CourseMiniAppEvent.created_at >= cutoff,
            )
        )
        return int(result.scalar() or 0), count, window_seconds

    async def _record_event(self, **kwargs) -> dict[str, Any]:
        return await CourseMiniAppAnalyticsService(self.session).record_server_event(
            **kwargs
        )

    @staticmethod
    def _event_payload(event: CourseMiniAppEvent) -> dict[str, Any]:
        try:
            value = json.loads(event.payload_json or "{}")
        except (TypeError, json.JSONDecodeError):
            return {}
        return value if isinstance(value, dict) else {}

    def _request_response(
        self,
        *,
        platform: str,
        request_token: str,
        duplicate: bool,
    ) -> dict[str, Any]:
        file_name = self.releases.file_name_for(platform)
        if not file_name:
            raise DesktopDownloadError(
                "desktop_release_unavailable",
                status_code=503,
                platform=platform,
            )
        return {
            "ok": True,
            "platform": platform,
            # `download_url` stays for old Mini App clients, but now opens the
            # branded installer page instead of exposing release storage.
            "download_url": self.releases.landing_url(platform, request_token),
            "download_page_url": self.releases.landing_url(
                platform,
                request_token,
            ),
            "file_name": file_name,
            "duplicate": duplicate,
        }

    async def request_download(
        self,
        *,
        telegram_id: int,
        platform: str,
        source: str,
        event_id: str,
        language: str | None,
    ) -> dict[str, Any]:
        if platform not in PLATFORMS or not self.releases.target_for(platform):
            raise DesktopDownloadError(
                "desktop_release_unavailable",
                status_code=503,
                platform=platform,
            )

        user = await self._user(telegram_id, for_update=True)
        request_dedupe = f"desktop-request:{platform}:{event_id}"
        request_event = await self._event_by_dedupe(
            telegram_id=telegram_id,
            event_name="desktop_download_requested",
            dedupe_key=request_dedupe,
        )
        if request_event:
            request_token = str(request_event.session_id or "")
            if not REQUEST_TOKEN_RE.fullmatch(request_token):
                raise DesktopDownloadError(
                    "desktop_download_temporarily_unavailable",
                    status_code=503,
                    platform=platform,
                )
            await self.session.commit()
            return self._request_response(
                platform=platform,
                request_token=request_token,
                duplicate=True,
            )

        recent, limit, window_seconds = await self._recent_requested_count(telegram_id)
        if recent >= limit:
            raise DesktopDownloadError(
                "desktop_download_rate_limited",
                status_code=429,
                platform=platform,
                retry_after_seconds=window_seconds,
            )

        resolved_language = language if language in {"uz", "ru", "tj"} else str(
            user.language or "uz"
        )
        if resolved_language not in {"uz", "ru", "tj"}:
            resolved_language = "uz"
        request_token = uuid4().hex
        recorded = await self._record_event(
            event_name="desktop_download_requested",
            telegram_id=telegram_id,
            user_id=user.id,
            source=f"desktop_{source}"[:40],
            session_id=request_token,
            dedupe_key=request_dedupe,
            payload={
                "platform": platform,
                "entry_source": source,
                "language": resolved_language,
                "client_event_id": event_id,
                "version": self.releases.version_for(platform),
            },
        )
        if not recorded.get("ok"):
            raise DesktopDownloadError(
                "desktop_download_temporarily_unavailable",
                status_code=503,
                platform=platform,
            )
        duplicate = bool(recorded.get("duplicate"))
        if duplicate:
            request_event = await self._event_by_dedupe(
                telegram_id=telegram_id,
                event_name="desktop_download_requested",
                dedupe_key=request_dedupe,
            )
            request_token = str(
                getattr(request_event, "session_id", "") if request_event else ""
            )
            if not REQUEST_TOKEN_RE.fullmatch(request_token):
                raise DesktopDownloadError(
                    "desktop_download_temporarily_unavailable",
                    status_code=503,
                    platform=platform,
                )
        try:
            await self.session.commit()
        except Exception as exc:
            logger.exception(
                "Desktop download request could not be persisted for telegram_id=%s",
                telegram_id,
            )
            raise DesktopDownloadError(
                "desktop_download_temporarily_unavailable",
                status_code=503,
                platform=platform,
            ) from exc
        return self._request_response(
            platform=platform,
            request_token=request_token,
            duplicate=duplicate,
        )

    async def mark_started(
        self,
        *,
        telegram_id: int,
        platform: str,
        source: str,
        event_id: str,
        transport: str,
    ) -> dict[str, Any]:
        await self._user(telegram_id)
        request_event = await self._event_by_dedupe(
            telegram_id=telegram_id,
            event_name="desktop_download_requested",
            dedupe_key=f"desktop-request:{platform}:{event_id}",
        )
        if not request_event:
            raise DesktopDownloadError(
                "desktop_download_not_found",
                status_code=404,
                platform=platform,
            )
        request_token = str(request_event.session_id or "")
        payload = self._event_payload(request_event)
        if (
            not REQUEST_TOKEN_RE.fullmatch(request_token)
            or payload.get("platform") != platform
            or payload.get("entry_source") != source
        ):
            raise DesktopDownloadError(
                "desktop_download_not_found",
                status_code=404,
                platform=platform,
            )
        recorded = await self._record_event(
            event_name="desktop_download_started",
            telegram_id=request_event.telegram_id,
            user_id=request_event.user_id,
            source=request_event.source,
            session_id=request_token,
            dedupe_key=f"desktop-started:{request_token}",
            payload={
                "platform": platform,
                "entry_source": source,
                "client_event_id": event_id,
                "transport": transport,
            },
        )
        if not recorded.get("ok"):
            raise DesktopDownloadError(
                "desktop_download_temporarily_unavailable",
                status_code=503,
                platform=platform,
            )
        await self.session.commit()
        return {
            "ok": True,
            "platform": platform,
            "recorded": bool(recorded.get("recorded")),
            "duplicate": bool(recorded.get("duplicate")),
        }

    async def resolve_redirect(
        self,
        *,
        platform: str,
        request_token: str | None,
    ) -> tuple[str, str]:
        target = self.releases.target_for(platform)
        file_name = self.releases.file_name_for(platform)
        if not target or not file_name:
            raise DesktopDownloadError(
                "desktop_release_unavailable",
                status_code=503,
                platform=platform,
            )
        if request_token is None or request_token == "":
            # Installers are public and free. Authenticated Mini App requests
            # still carry a token so their funnel can be attributed.
            return target, file_name
        if not REQUEST_TOKEN_RE.fullmatch(request_token):
            raise DesktopDownloadError("desktop_download_not_found", status_code=404)

        request_event = await self._request_event_by_token(request_token)
        if not request_event:
            raise DesktopDownloadError("desktop_download_not_found", status_code=404)
        payload = self._event_payload(request_event)
        if payload.get("platform") != platform:
            raise DesktopDownloadError("desktop_download_not_found", status_code=404)

        recorded = await self._record_event(
            event_name="desktop_download_link_clicked",
            telegram_id=request_event.telegram_id,
            user_id=request_event.user_id,
            source=request_event.source,
            session_id=request_token,
            dedupe_key=f"desktop-click:{request_token}",
            payload={
                "platform": platform,
                "entry_source": payload.get("entry_source"),
            },
        )
        if recorded.get("ok"):
            await self.session.commit()
        else:
            logger.warning("Desktop click analytics failed for request=%s", request_token)
        return target, file_name
