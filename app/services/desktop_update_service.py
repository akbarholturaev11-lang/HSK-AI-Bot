from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from app.services.desktop_release_manifest_service import (
    DesktopReleaseManifestService,
)
from app.services.desktop_semver import parse_desktop_semver


DESKTOP_UPDATE_TARGET_ARCHES = {
    "darwin": frozenset({"aarch64", "x86_64"}),
    # Release CI currently produces one Windows x64 NSIS/updater artifact.
    "windows": frozenset({"x86_64"}),
}
DESKTOP_UPDATE_SUFFIXES = {
    "darwin": ".app.tar.gz",
    "windows": ".exe",
}
_SIGNATURE_RE = re.compile(r"^[A-Za-z0-9+/=_-]+$")


class DesktopUpdateError(ValueError):
    def __init__(self, code: str, *, status_code: int):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


@dataclass(frozen=True)
class DesktopUpdateRelease:
    version: str
    url: str
    signature: str
    notes: str

    def payload(self) -> dict[str, str]:
        return {
            "version": self.version,
            "url": self.url,
            "signature": self.signature,
            "notes": self.notes,
        }


class DesktopUpdateService:
    """Build a public Tauri manifest from fail-closed release settings."""

    def __init__(
        self,
        settings_obj: Any,
        *,
        release_manifest_service: DesktopReleaseManifestService | None = None,
    ):
        self.settings = settings_obj
        self.release_manifest_service = (
            release_manifest_service
            or DesktopReleaseManifestService(settings_obj)
        )

    @staticmethod
    def _text(value: Any, *, max_length: int) -> str:
        text = str(value or "").strip()
        if not text or len(text) > max_length or "\x00" in text:
            return ""
        return text

    @classmethod
    def _artifact_url(cls, value: Any, *, target: str) -> str:
        url = cls._text(value, max_length=2_048)
        if not url:
            return ""
        try:
            parsed = urlsplit(url)
        except ValueError:
            return ""
        expected_suffix = DESKTOP_UPDATE_SUFFIXES[target]
        if (
            parsed.scheme.lower() != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or not parsed.path.lower().endswith(expected_suffix)
        ):
            return ""
        return url

    @classmethod
    def _signature(cls, value: Any) -> str:
        signature = cls._text(value, max_length=16_384)
        if (
            len(signature) < 32
            or not _SIGNATURE_RE.fullmatch(signature)
        ):
            return ""
        return signature

    def _configured_release(self, target: str) -> DesktopUpdateRelease | None:
        if target == "darwin":
            version_value = getattr(self.settings, "DESKTOP_MAC_VERSION", "")
            url_value = getattr(self.settings, "DESKTOP_MAC_UPDATER_URL", "")
            signature_value = getattr(
                self.settings,
                "DESKTOP_MAC_UPDATER_SIGNATURE",
                "",
            )
            notes_value = getattr(self.settings, "DESKTOP_MAC_UPDATER_NOTES", "")
        else:
            version_value = getattr(self.settings, "DESKTOP_WINDOWS_VERSION", "")
            url_value = getattr(
                self.settings,
                "DESKTOP_WINDOWS_UPDATER_URL",
                "",
            )
            signature_value = getattr(
                self.settings,
                "DESKTOP_WINDOWS_UPDATER_SIGNATURE",
                "",
            )
            notes_value = getattr(
                self.settings,
                "DESKTOP_WINDOWS_UPDATER_NOTES",
                "",
            )

        version = self._text(version_value, max_length=128)
        try:
            parse_desktop_semver(version)
        except ValueError:
            return None
        url = self._artifact_url(url_value, target=target)
        signature = self._signature(signature_value)
        if not url or not signature:
            return None
        notes = self._text(notes_value, max_length=4_000)
        return DesktopUpdateRelease(
            version=version,
            url=url,
            signature=signature,
            notes=notes,
        )

    async def _release(self, target: str) -> DesktopUpdateRelease | None:
        if self.release_manifest_service.configured:
            manifest = await self.release_manifest_service.resolve()
            platform = manifest.platform(target) if manifest else None
            if not manifest or not platform:
                return None
            return DesktopUpdateRelease(
                version=manifest.version,
                url=platform.update_url,
                signature=platform.signature,
                notes=manifest.notes,
            )
        return self._configured_release(target)

    async def manifest(
        self,
        *,
        target: str,
        arch: str,
        current_version: str,
    ) -> dict[str, str] | None:
        target = str(target or "").strip()
        arch = str(arch or "").strip()
        if target not in DESKTOP_UPDATE_TARGET_ARCHES:
            raise DesktopUpdateError(
                "desktop_update_target_unsupported",
                status_code=404,
            )
        if arch not in DESKTOP_UPDATE_TARGET_ARCHES[target]:
            raise DesktopUpdateError(
                "desktop_update_arch_unsupported",
                status_code=404,
            )
        try:
            current = parse_desktop_semver(current_version)
        except ValueError as exc:
            raise DesktopUpdateError(
                "desktop_update_version_invalid",
                status_code=422,
            ) from exc

        if not bool(getattr(self.settings, "DESKTOP_UPDATES_ENABLED", False)):
            return None
        release = await self._release(target)
        if not release:
            return None
        latest = parse_desktop_semver(release.version)
        if current >= latest:
            return None
        return release.payload()
