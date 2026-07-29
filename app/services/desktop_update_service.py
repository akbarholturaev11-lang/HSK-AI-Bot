from __future__ import annotations

import re
from dataclasses import dataclass
from functools import total_ordering
from typing import Any
from urllib.parse import urlsplit


DESKTOP_UPDATE_TARGET_ARCHES = {
    "darwin": frozenset({"aarch64", "x86_64"}),
    "windows": frozenset({"aarch64", "i686", "x86_64"}),
}
DESKTOP_UPDATE_SUFFIXES = {
    "darwin": ".app.tar.gz",
    "windows": ".exe",
}
_SEMVER_CORE_RE = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-([^+]+))?(?:\+(.+))?$"
)
_SEMVER_IDENTIFIER_RE = re.compile(r"^[0-9A-Za-z-]+$")
_SIGNATURE_RE = re.compile(r"^[A-Za-z0-9+/=_-]+$")


class DesktopUpdateError(ValueError):
    def __init__(self, code: str, *, status_code: int):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


@total_ordering
@dataclass(frozen=True)
class DesktopSemVer:
    major: int
    minor: int
    patch: int
    prerelease: tuple[str, ...] = ()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DesktopSemVer):
            return NotImplemented
        return (
            self.major,
            self.minor,
            self.patch,
            self.prerelease,
        ) == (
            other.major,
            other.minor,
            other.patch,
            other.prerelease,
        )

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, DesktopSemVer):
            return NotImplemented
        own_core = (self.major, self.minor, self.patch)
        other_core = (other.major, other.minor, other.patch)
        if own_core != other_core:
            return own_core < other_core
        if not self.prerelease:
            return False
        if not other.prerelease:
            return True
        for own_identifier, other_identifier in zip(
            self.prerelease,
            other.prerelease,
        ):
            if own_identifier == other_identifier:
                continue
            own_numeric = own_identifier.isdigit()
            other_numeric = other_identifier.isdigit()
            if own_numeric and other_numeric:
                return int(own_identifier) < int(other_identifier)
            if own_numeric != other_numeric:
                return own_numeric
            return own_identifier < other_identifier
        return len(self.prerelease) < len(other.prerelease)


def parse_desktop_semver(value: str) -> DesktopSemVer:
    normalized = str(value or "").strip()
    if not normalized or len(normalized) > 128:
        raise ValueError("invalid_semver")
    match = _SEMVER_CORE_RE.fullmatch(normalized)
    if not match:
        raise ValueError("invalid_semver")

    prerelease_raw = match.group(4)
    build_raw = match.group(5)
    prerelease = tuple(prerelease_raw.split(".")) if prerelease_raw else ()
    build = tuple(build_raw.split(".")) if build_raw else ()
    for identifier in (*prerelease, *build):
        if not identifier or not _SEMVER_IDENTIFIER_RE.fullmatch(identifier):
            raise ValueError("invalid_semver")
    if any(
        identifier.isdigit()
        and len(identifier) > 1
        and identifier.startswith("0")
        for identifier in prerelease
    ):
        raise ValueError("invalid_semver")

    return DesktopSemVer(
        major=int(match.group(1)),
        minor=int(match.group(2)),
        patch=int(match.group(3)),
        prerelease=prerelease,
    )


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

    def __init__(self, settings_obj: Any):
        self.settings = settings_obj

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

    def manifest(
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
        release = self._configured_release(target)
        if not release:
            return None
        latest = parse_desktop_semver(release.version)
        if current >= latest:
            return None
        return release.payload()
