"""The one stable file that says which Android build is current.

This is the Android half of what `desktop/latest.json` does for macOS and
Windows: the release workflow writes it, the server reads it, and nobody
pastes a link anywhere. It reuses the desktop resolver's URL and text rules
rather than restating them, because the threat is identical — this server
fetches whatever that setting points at.

The rules that matter are the same three the desktop manifest enforces, and
they are the reason this is not just `json.loads`:

* A configured manifest that cannot be read never falls back to something
  older. After one good read the last-known-good release survives every
  later failure, so a storage hiccup cannot un-publish a release.
* A manifest that goes backwards is refused. Otherwise a stale or restored
  copy of the file would tell every installed app to "update" to the build
  it already replaced.
* The same version pointing at a different artifact is refused. A release
  that has been published is finished; changing what is behind it is how
  people end up running something nobody tested.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

import httpx

from app.services.desktop_release_manifest_service import (
    _bounded_number,
    _strict_https_url,
    _strict_text,
)


logger = logging.getLogger(__name__)

ANDROID_MANIFEST_SCHEMA_VERSION = 1
DEFAULT_CACHE_TTL_SECONDS = 60
DEFAULT_TIMEOUT_SECONDS = 5.0
DEFAULT_MAX_BYTES = 16_384
MAX_VERSION_CODE = 2_000_000_000
MAX_APK_BYTES = 512 * 1024 * 1024

_TOP_LEVEL_KEYS = {
    "schema_version",
    "version_name",
    "version_code",
    "download_url",
    "size",
    "sha256",
    "published_at",
    "notes",
}


class AndroidReleaseManifestError(ValueError):
    pass


@dataclass(frozen=True)
class AndroidReleaseManifest:
    version_name: str
    version_code: int
    download_url: str
    size: int
    sha256: str
    published_at: str
    notes: str

    def immutable_fingerprint(self) -> tuple[Any, ...]:
        """What may never change once a version is published."""
        return (self.version_name, self.download_url, self.size, self.sha256)


@dataclass
class _CacheEntry:
    manifest: AndroidReleaseManifest | None = None
    checked_at: float = float("-inf")


ManifestFetcher = Callable[[str, float, int], Awaitable[bytes] | bytes]


def _strict_int(value: Any, *, minimum: int, maximum: int) -> int:
    # `True` is an int in Python, and a JSON `true` reaching a version code
    # would silently become 1.
    if isinstance(value, bool) or not isinstance(value, int):
        raise AndroidReleaseManifestError("invalid_number")
    if value < minimum or value > maximum:
        raise AndroidReleaseManifestError("invalid_number")
    return value


def parse_android_release_manifest(payload: bytes) -> AndroidReleaseManifest:
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise AndroidReleaseManifestError("manifest_invalid_json") from exc
    if not isinstance(data, dict):
        raise AndroidReleaseManifestError("manifest_invalid_json")
    unknown = set(data) - _TOP_LEVEL_KEYS
    if unknown:
        # An unknown key means this file was written by something that does not
        # agree with us about what it contains.
        raise AndroidReleaseManifestError("manifest_unknown_keys")
    if data.get("schema_version") != ANDROID_MANIFEST_SCHEMA_VERSION:
        raise AndroidReleaseManifestError("manifest_schema_version")

    try:
        download_url = _strict_https_url(data.get("download_url"), suffix=".apk")
    except Exception as exc:
        raise AndroidReleaseManifestError("manifest_invalid_url") from exc

    sha256 = _strict_text(data.get("sha256"), max_length=64)
    if len(sha256) != 64 or any(c not in "0123456789abcdefABCDEF" for c in sha256):
        raise AndroidReleaseManifestError("manifest_invalid_sha256")

    return AndroidReleaseManifest(
        version_name=_strict_text(data.get("version_name"), max_length=40),
        version_code=_strict_int(
            data.get("version_code"), minimum=1, maximum=MAX_VERSION_CODE
        ),
        download_url=download_url,
        size=_strict_int(data.get("size"), minimum=1, maximum=MAX_APK_BYTES),
        sha256=sha256.lower(),
        published_at=_strict_text(data.get("published_at"), max_length=40),
        notes=_strict_text(data.get("notes", ""), max_length=2_000, allow_empty=True),
    )


class AndroidReleaseManifestService:
    """Fetch and cache the single stable Android release manifest."""

    _cache: dict[str, _CacheEntry] = {}
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
            getattr(settings_obj, "ANDROID_RELEASE_MANIFEST_URL", "") or ""
        ).strip()
        self.configured = bool(self.raw_url)
        try:
            self.url = _strict_https_url(self.raw_url, suffix=".json")
        except Exception:
            self.url = None
        self.cache_ttl_seconds = int(
            _bounded_number(
                getattr(
                    settings_obj,
                    "ANDROID_RELEASE_MANIFEST_CACHE_TTL_SECONDS",
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
                "ANDROID_RELEASE_MANIFEST_TIMEOUT_SECONDS",
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
                    "ANDROID_RELEASE_MANIFEST_MAX_BYTES",
                    DEFAULT_MAX_BYTES,
                ),
                default=DEFAULT_MAX_BYTES,
                minimum=2_048,
                maximum=131_072,
            )
        )
        self.fetcher = fetcher or self._fetch_bytes
        self.clock = clock
        self.http_transport = http_transport

    @classmethod
    def clear_cache(cls) -> None:
        with cls._cache_lock:
            cls._cache.clear()

    def _cached(self) -> _CacheEntry:
        assert self.url is not None
        with self._cache_lock:
            return self._cache.setdefault(self.url, _CacheEntry())

    async def _fetch_bytes(self, url: str, timeout: float, max_bytes: int) -> bytes:
        headers = {
            "Accept": "application/json",
            "User-Agent": "Pomp-HSK-AI-release-resolver/1",
        }
        async with asyncio.timeout(timeout):
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(timeout),
                follow_redirects=False,
                transport=self.http_transport,
            ) as client:
                async with client.stream("GET", url, headers=headers) as response:
                    if response.status_code != 200:
                        raise AndroidReleaseManifestError("manifest_http_error")
                    media_type = response.headers.get("content-type", "").split(";", 1)[0]
                    if media_type.strip().lower() != "application/json":
                        raise AndroidReleaseManifestError("manifest_content_type_invalid")
                    declared = response.headers.get("content-length", "").strip()
                    if declared:
                        try:
                            if int(declared) > max_bytes:
                                raise AndroidReleaseManifestError("manifest_too_large")
                        except ValueError as exc:
                            raise AndroidReleaseManifestError(
                                "manifest_content_length_invalid"
                            ) from exc
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > max_bytes:
                            raise AndroidReleaseManifestError("manifest_too_large")
                    if not body:
                        raise AndroidReleaseManifestError("manifest_empty")
                    return bytes(body)

    def cached_manifest(self) -> AndroidReleaseManifest | None:
        if not self.url:
            return None
        with self._cache_lock:
            entry = self._cache.get(self.url)
            return entry.manifest if entry else None

    async def resolve(self) -> AndroidReleaseManifest | None:
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
                raise AndroidReleaseManifestError("manifest_too_large")
            candidate = parse_android_release_manifest(payload)
        except Exception as exc:
            # Keep the last-known-good release. A storage hiccup must not
            # un-publish a build that is already in people's hands.
            logger.warning(
                "Android release manifest refresh failed (%s)", type(exc).__name__
            )
            with self._cache_lock:
                current = self._cache.setdefault(self.url, _CacheEntry())
                current.checked_at = now
                return current.manifest

        with self._cache_lock:
            current = self._cache.setdefault(self.url, _CacheEntry())
            previous = current.manifest
            if previous is not None:
                if candidate.version_code < previous.version_code:
                    logger.warning("Android release manifest downgrade was rejected")
                    current.checked_at = now
                    return previous
                if (
                    candidate.version_code == previous.version_code
                    and candidate.immutable_fingerprint()
                    != previous.immutable_fingerprint()
                ):
                    logger.warning(
                        "Android release manifest same-version artifact mutation was rejected"
                    )
                    current.checked_at = now
                    return previous
            current.manifest = candidate
            current.checked_at = now
            return candidate
