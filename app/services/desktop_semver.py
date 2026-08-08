from __future__ import annotations

import re
from dataclasses import dataclass
from functools import total_ordering


_SEMVER_CORE_RE = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-([^+]+))?(?:\+(.+))?$"
)
_SEMVER_IDENTIFIER_RE = re.compile(r"^[0-9A-Za-z-]+$")


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
