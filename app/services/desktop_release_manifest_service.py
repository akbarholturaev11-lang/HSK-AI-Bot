from __future__ import annotations

import asyncio
import inspect
import ipaddress
import json
import logging
import math
import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Awaitable, Callable
from urllib.parse import urlsplit

import httpx

from app.services.desktop_semver import parse_desktop_semver


logger = logging.getLogger(__name__)

MANIFEST_SCHEMA_VERSION = 1
DEFAULT_CACHE_TTL_SECONDS = 60
DEFAULT_TIMEOUT_SECONDS = 5.0
DEFAULT_MAX_BYTES = 65_536
_SIGNATURE_RE = re.compile(r"^[A-Za-z0-9+/=_-]+$")
_SHA256_RE = re.compile(r"^[0-9A-Fa-f]{64}$")
_STABLE_SEMVER_RE = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$"
)
_UTC_TIMESTAMP_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)
_TOP_LEVEL_KEYS = {
    "schema_version",
    "version",
    "notes",
    "published_at",
    "macos",
    "windows",
}
_MACOS_KEYS = {
    "download_url",
    "update_url",
    "signature",
    "download_sha256",
    "update_sha256",
}
_WINDOWS_KEYS = {
    "download_url",
    "update_url",
    "signature",
    "sha256",
}


class DesktopReleaseManifestError(ValueError):
    pass


@dataclass(frozen=True)
class DesktopReleasePlatform:
    download_url: str
    update_url: str
    signature: str
    download_sha256: str
    update_sha256: str

    def immutable_fingerprint(self) -> tuple[str, ...]:
        return (
            self.download_url,
            self.update_url,
            self.signature,
            self.download_sha256,
            self.update_sha256,
        )


@dataclass(frozen=True)
class DesktopReleaseManifest:
    version: str
    notes: str
    published_at: str
    macos: DesktopReleasePlatform
    windows: DesktopReleasePlatform

    def platform(self, value: str) -> DesktopReleasePlatform | None:
        if value in {"macos", "darwin"}:
            return self.macos
        if value == "windows":
            return self.windows
        return None

    def immutable_fingerprint(self) -> tuple[Any, ...]:
        return (
            self.version,
            self.macos.immutable_fingerprint(),
            self.windows.immutable_fingerprint(),
        )


@dataclass
class _ManifestCacheEntry:
    manifest: DesktopReleaseManifest | None = None
    checked_at: float = float("-inf")


ManifestFetcher = Callable[[str, float, int], Awaitable[bytes] | bytes]


def _bounded_number(value: Any, *, default: float, minimum: float, maximum: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(parsed) or parsed < minimum or parsed > maximum:
        return default
    return parsed


def _strict_https_url(
    value: Any,
    *,
    suffix: str,
    max_length: int = 2_048,
) -> str:
    url = str(value or "").strip()
    if (
        not url
        or len(url) > max_length
        or "\\" in url
        or any(ord(character) <= 0x20 or ord(character) == 0x7F for character in url)
    ):
        raise DesktopReleaseManifestError("invalid_url")
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise DesktopReleaseManifestError("invalid_url") from exc
    hostname = str(parsed.hostname or "").lower().rstrip(".")
    if (
        parsed.scheme.lower() != "https"
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or port not in {None, 443}
        or parsed.query
        or parsed.fragment
        or not parsed.path.lower().endswith(suffix)
    ):
        raise DesktopReleaseManifestError("invalid_url")
    if (
        hostname == "localhost"
        or hostname.endswith(".localhost")
        or hostname.endswith(".local")
        or hostname.endswith(".internal")
    ):
        raise DesktopReleaseManifestError("invalid_url")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address is None and "." not in hostname:
        raise DesktopReleaseManifestError("invalid_url")
    if address is not None and not address.is_global:
        raise DesktopReleaseManifestError("invalid_url")
    return url


def _strict_text(value: Any, *, max_length: int, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise DesktopReleaseManifestError("invalid_text")
    text = value.strip()
    if (not text and not allow_empty) or len(text) > max_length or "\x00" in text:
        raise DesktopReleaseManifestError("invalid_text")
    return text


def _strict_signature(value: Any) -> str:
    signature = _strict_text(value, max_length=16_384)
    if len(signature) < 32 or not _SIGNATURE_RE.fullmatch(signature):
        raise DesktopReleaseManifestError("invalid_signature")
    return signature


def _strict_sha256(value: Any) -> str:
    digest = _strict_text(value, max_length=64)
    if not _SHA256_RE.fullmatch(digest):
        raise DesktopReleaseManifestError("invalid_sha256")
    return digest.lower()


def _strict_published_at(value: Any) -> str:
    published_at = _strict_text(value, max_length=40)
    if not _UTC_TIMESTAMP_RE.fullmatch(published_at):
        raise DesktopReleaseManifestError("invalid_published_at")
    try:
        parsed = datetime.fromisoformat(published_at[:-1] + "+00:00")
    except ValueError as exc:
        raise DesktopReleaseManifestError("invalid_published_at") from exc
    if parsed.utcoffset() is None:
        raise DesktopReleaseManifestError("invalid_published_at")
    return published_at


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DesktopReleaseManifestError("duplicate_key")
        result[key] = value
    return result


def _reject_json_constant(_value: str) -> None:
    raise DesktopReleaseManifestError("invalid_json_constant")


def parse_desktop_release_manifest(payload: bytes) -> DesktopReleaseManifest:
    try:
        decoded = payload.decode("utf-8")
        document = json.loads(
            decoded,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DesktopReleaseManifestError("invalid_json") from exc

    if not isinstance(document, dict) or set(document) != _TOP_LEVEL_KEYS:
        raise DesktopReleaseManifestError("invalid_schema")
    if (
        type(document["schema_version"]) is not int
        or document["schema_version"] != MANIFEST_SCHEMA_VERSION
    ):
        raise DesktopReleaseManifestError("invalid_schema_version")

    version = _strict_text(document["version"], max_length=128)
    if not _STABLE_SEMVER_RE.fullmatch(version):
        raise DesktopReleaseManifestError("invalid_version")
    parse_desktop_semver(version)
    notes = _strict_text(document["notes"], max_length=4_000, allow_empty=True)
    published_at = _strict_published_at(document["published_at"])

    macos = document["macos"]
    windows = document["windows"]
    if not isinstance(macos, dict) or set(macos) != _MACOS_KEYS:
        raise DesktopReleaseManifestError("invalid_macos_schema")
    if not isinstance(windows, dict) or set(windows) != _WINDOWS_KEYS:
        raise DesktopReleaseManifestError("invalid_windows_schema")

    return DesktopReleaseManifest(
        version=version,
        notes=notes,
        published_at=published_at,
        macos=DesktopReleasePlatform(
            download_url=_strict_https_url(macos["download_url"], suffix=".dmg"),
            update_url=_strict_https_url(
                macos["update_url"],
                suffix=".app.tar.gz",
            ),
            signature=_strict_signature(macos["signature"]),
            download_sha256=_strict_sha256(macos["download_sha256"]),
            update_sha256=_strict_sha256(macos["update_sha256"]),
        ),
        windows=DesktopReleasePlatform(
            download_url=_strict_https_url(
                windows["download_url"],
                suffix=".exe",
            ),
            update_url=_strict_https_url(windows["update_url"], suffix=".exe"),
            signature=_strict_signature(windows["signature"]),
            download_sha256=_strict_sha256(windows["sha256"]),
            update_sha256=_strict_sha256(windows["sha256"]),
        ),
    )


class DesktopReleaseManifestService:
    """Fetch and cache the single stable desktop release manifest.

    A configured but unavailable/invalid manifest never falls through to static
    per-version values. After one valid response, transient failures retain the
    last-known-good release for the lifetime of this process.
    """

    _cache: dict[str, _ManifestCacheEntry] = {}
    _cache_lock = threading.RLock()

    def __init__(
        self,
        settings_obj: Any,
        *,
        fetcher: ManifestFetcher | None = None,
        clock: Callable[[], float] = time.monotonic,
        http_transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.settings = settings_obj
        self.raw_url = str(
            getattr(settings_obj, "DESKTOP_RELEASE_MANIFEST_URL", "") or ""
        ).strip()
        self.configured = bool(self.raw_url)
        try:
            self.url = _strict_https_url(self.raw_url, suffix=".json")
        except DesktopReleaseManifestError:
            self.url = None
        self.cache_ttl_seconds = int(
            _bounded_number(
                getattr(
                    settings_obj,
                    "DESKTOP_RELEASE_MANIFEST_CACHE_TTL_SECONDS",
                    DEFAULT_CACHE_TTL_SECONDS,
                ),
                default=DEFAULT_CACHE_TTL_SECONDS,
                minimum=5,
                maximum=300,
            )
        )
        self.timeout_seconds = _bounded_number(
            getattr(
                settings_obj,
                "DESKTOP_RELEASE_MANIFEST_TIMEOUT_SECONDS",
                DEFAULT_TIMEOUT_SECONDS,
            ),
            default=DEFAULT_TIMEOUT_SECONDS,
            minimum=1,
            maximum=15,
        )
        self.max_bytes = int(
            _bounded_number(
                getattr(
                    settings_obj,
                    "DESKTOP_RELEASE_MANIFEST_MAX_BYTES",
                    DEFAULT_MAX_BYTES,
                ),
                default=DEFAULT_MAX_BYTES,
                minimum=4_096,
                maximum=262_144,
            )
        )
        self.fetcher = fetcher or self._fetch_bytes
        self.clock = clock
        self.http_transport = http_transport

    @classmethod
    def clear_cache(cls) -> None:
        with cls._cache_lock:
            cls._cache.clear()

    def _cached(self) -> _ManifestCacheEntry:
        assert self.url is not None
        with self._cache_lock:
            return self._cache.setdefault(self.url, _ManifestCacheEntry())

    async def _fetch_bytes(self, url: str, timeout: float, max_bytes: int) -> bytes:
        timeout_config = httpx.Timeout(timeout)
        headers = {
            "Accept": "application/json",
            "User-Agent": "Pomp-HSK-AI-release-resolver/1",
        }
        async with asyncio.timeout(timeout):
            async with httpx.AsyncClient(
                timeout=timeout_config,
                follow_redirects=False,
                transport=self.http_transport,
            ) as client:
                async with client.stream("GET", url, headers=headers) as response:
                    if response.status_code != 200:
                        raise DesktopReleaseManifestError("manifest_http_error")
                    media_type = response.headers.get("content-type", "").split(
                        ";",
                        1,
                    )[0]
                    if media_type.strip().lower() != "application/json":
                        raise DesktopReleaseManifestError(
                            "manifest_content_type_invalid"
                        )
                    content_length = response.headers.get(
                        "content-length",
                        "",
                    ).strip()
                    if content_length:
                        try:
                            if int(content_length) > max_bytes:
                                raise DesktopReleaseManifestError(
                                    "manifest_too_large"
                                )
                        except ValueError as exc:
                            raise DesktopReleaseManifestError(
                                "manifest_content_length_invalid"
                            ) from exc
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > max_bytes:
                            raise DesktopReleaseManifestError("manifest_too_large")
                    if not body:
                        raise DesktopReleaseManifestError("manifest_empty")
                    return bytes(body)

    def cached_manifest(self) -> DesktopReleaseManifest | None:
        if not self.url:
            return None
        with self._cache_lock:
            entry = self._cache.get(self.url)
            return entry.manifest if entry else None

    async def resolve(self) -> DesktopReleaseManifest | None:
        if not self.configured or not self.url:
            return None

        now = self.clock()
        entry = self._cached()
        with self._cache_lock:
            if now - entry.checked_at < self.cache_ttl_seconds:
                return entry.manifest

        try:
            fetched = self.fetcher(self.url, self.timeout_seconds, self.max_bytes)
            payload = await fetched if inspect.isawaitable(fetched) else fetched
            if not isinstance(payload, bytes) or len(payload) > self.max_bytes:
                raise DesktopReleaseManifestError("manifest_too_large")
            candidate = parse_desktop_release_manifest(payload)
        except Exception as exc:
            logger.warning(
                "Desktop release manifest refresh failed (%s)",
                type(exc).__name__,
            )
            with self._cache_lock:
                current = self._cache.setdefault(self.url, _ManifestCacheEntry())
                current.checked_at = now
                return current.manifest

        with self._cache_lock:
            current = self._cache.setdefault(self.url, _ManifestCacheEntry())
            previous = current.manifest
            if previous is not None:
                previous_version = parse_desktop_semver(previous.version)
                candidate_version = parse_desktop_semver(candidate.version)
                if candidate_version < previous_version:
                    logger.warning("Desktop release manifest downgrade was rejected")
                    current.checked_at = now
                    return previous
                if (
                    candidate_version == previous_version
                    and candidate.immutable_fingerprint()
                    != previous.immutable_fingerprint()
                ):
                    logger.warning(
                        "Desktop release manifest same-version artifact mutation was rejected"
                    )
                    current.checked_at = now
                    return previous
            current.manifest = candidate
            current.checked_at = now
            return candidate


async def resolve_desktop_latest_versions(settings_obj: Any) -> dict[str, str]:
    service = DesktopReleaseManifestService(settings_obj)
    if service.configured:
        manifest = await service.resolve()
        return (
            {"macos": manifest.version, "windows": manifest.version}
            if manifest
            else {}
        )
    versions = {
        "macos": str(getattr(settings_obj, "DESKTOP_MAC_VERSION", "") or "").strip(),
        "windows": str(
            getattr(settings_obj, "DESKTOP_WINDOWS_VERSION", "") or ""
        ).strip(),
    }
    return {platform: version for platform, version in versions.items() if version}
