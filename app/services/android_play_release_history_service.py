"""Google Play production release history mirror, published on R2 after API verification.

The Play Console API is authoritative for RELEASES; Play Core on the installed
phone separately confirms whether the offered release is available to that
user. No sideload/download_url can enter this format.
"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from typing import Any

from app.services.android_release_manifest_service import (
    AndroidReleaseManifestService, MAX_VERSION_CODE,
)
from app.services.desktop_release_manifest_service import _strict_https_url

logger = logging.getLogger(__name__)
_CACHE_TTL = 120.0
_CACHE: dict[str, tuple[float, tuple[int, ...]]] = {}
_LOCK = threading.RLock()


def parse_play_release_history(payload: bytes) -> tuple[int, ...]:
    if not isinstance(payload, bytes) or len(payload) > 16384:
        raise ValueError("play_history_too_large")
    data = json.loads(payload.decode("utf-8"))
    if not isinstance(data, dict) or set(data) != {
        "schema_version", "package_name", "track", "published_version_codes", "synced_at"
    }:
        raise ValueError("play_history_schema")
    if data["schema_version"] != 1 or data["package_name"] != "com.pomp.hskai" or data["track"] != "production":
        raise ValueError("play_history_source")
    codes = data["published_version_codes"]
    if (not isinstance(codes, list) or not 1 <= len(codes) <= 128
            or any(type(code) is not int or not 1 <= code <= MAX_VERSION_CODE for code in codes)
            or codes != sorted(set(codes))):
        raise ValueError("play_history_codes")
    if not isinstance(data["synced_at"], str) or not 1 <= len(data["synced_at"]) <= 40:
        raise ValueError("play_history_timestamp")
    return tuple(codes)


class AndroidPlayReleaseHistoryService:
    def __init__(self, settings_obj: Any = None, *, fetcher=None):
        if settings_obj is None:
            from app.config import settings
            settings_obj = settings
        raw = str(getattr(settings_obj, "ANDROID_RELEASE_MANIFEST_URL", "") or "").strip()
        # Existing Direct CDN points at R2/android/latest.json. The Play-only
        # ledger lives in the same bucket but is written ONLY after Google Play
        # Developer API verification, not by the Direct release workflow.
        if raw.endswith("/android/latest.json"):
            raw = raw[:-len("latest.json")] + "play-releases.json"
        else:
            raw = ""
        try:
            self.url = _strict_https_url(raw, suffix=".json") if raw else None
        except Exception:
            self.url = None
        self._fetcher = fetcher
        self.settings = settings_obj

    @classmethod
    def clear_cache(cls):
        with _LOCK:
            _CACHE.clear()

    async def resolve(self) -> tuple[int, ...]:
        if not self.url:
            return ()
        now = time.monotonic()
        with _LOCK:
            old = _CACHE.get(self.url)
            if old and now - old[0] < _CACHE_TTL:
                return old[1]
        try:
            if self._fetcher is None:
                resolver = AndroidReleaseManifestService(self.settings)
                payload = await resolver._fetch_bytes(self.url, 5, 16384)
            else:
                maybe = self._fetcher(self.url)
                payload = await maybe if asyncio.iscoroutine(maybe) else maybe
            codes = parse_play_release_history(payload)
            with _LOCK:
                previous = _CACHE.get(self.url)
                if previous:
                    prior = previous[1]
                    overlap = tuple(code for code in prior if code >= codes[0])
                    if overlap != codes[:len(overlap)]:
                        logger.warning("Play release history rewrite was rejected")
                        _CACHE[self.url] = (now, prior)
                        return prior
                _CACHE[self.url] = (now, codes)
            return codes
        except Exception as exc:
            logger.warning("Play release history unavailable (%s)", type(exc).__name__)
            with _LOCK:
                old = _CACHE.get(self.url)
                if old:
                    _CACHE[self.url] = (now, old[1])
                    return old[1]
            return ()
