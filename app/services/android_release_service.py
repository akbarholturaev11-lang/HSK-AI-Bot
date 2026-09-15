"""The Android APK that the bot hands out.

Distribution is Telegram-only for now — there is no Play listing and no file
host. The admin uploads one signed APK to the bot, Telegram keeps the bytes,
and every learner afterwards receives that same `file_id`. Nothing of ours
serves the download, there is no second copy to keep in sync, and the file
arrives inside the chat the learner is already reading.

The published release lives in `bot_settings` under a single JSON value rather
than in its own table: it is exactly one row that only an admin ever writes, so
a migration would buy nothing. Withdrawing a bad build is one write away, which
matters more here than schema purity — a broken APK must stop being handed out
within seconds, not within a deploy.
"""

import json
import logging
import re
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlsplit

from app.repositories.bot_setting_repo import BotSettingRepository


logger = logging.getLogger(__name__)

ANDROID_RELEASE_KEY = "android_apk_release"

# Telegram refuses documents larger than this from a bot, so an APK above it
# could be stored and then never delivered. Rejecting at upload turns a silent
# failure in every learner's chat into one error message in the admin's.
MAX_APK_BYTES = 50 * 1024 * 1024

# Gradle names the artifact `hsk-ai-<versionName>-<versionCode>-<flavour>-<type>.apk`
# (see `archivesBaseName` in android/app/build.gradle.kts), which is the only
# place the version survives the trip through Telegram — the bot never opens
# the APK. When the name does not match, the admin is asked to type the version
# instead of the bot guessing one.
_ARTIFACT_NAME = re.compile(
    r"^hsk-ai-(?P<version_name>.+)-(?P<version_code>\d+)-"
    r"(?P<flavor>direct|play)-(?P<build_type>debug|release)\.apk$",
    re.IGNORECASE,
)

_VERSION_TEXT = re.compile(
    r"^(?P<version_name>\d+(?:\.\d+){0,3}(?:-[0-9A-Za-z.]+)?)"
    r"(?:\s*[( ]\s*(?P<version_code>\d+)\s*\)?)?$"
)


class AndroidReleaseError(ValueError):
    """A refused upload. The message is admin-facing Uzbek, not a code."""


@dataclass(frozen=True)
class AndroidRelease:
    file_id: str
    file_unique_id: str
    file_name: str
    file_size: int
    version_name: str
    version_code: Optional[int]
    published_at: datetime
    published_by: Optional[int]
    # Where an installed app can fetch this same build. It lives on the same
    # row as the Telegram file on purpose: the updater must never be able to
    # offer a different version from the one the bot hands out, and two rows
    # would let exactly that drift in unnoticed.
    update_url: Optional[str] = None

    @property
    def can_self_update(self) -> bool:
        """An installed app can only be offered an update it can identify.

        Without a version code there is nothing to compare against what is
        installed, so the app would either re-offer the build it is already
        running or never offer anything.
        """
        return bool(self.update_url) and self.version_code is not None

    @property
    def size_text(self) -> str:
        return format_size(self.file_size)

    @property
    def version_text(self) -> str:
        if self.version_code is None:
            return self.version_name
        return f"{self.version_name} ({self.version_code})"

    def to_json(self) -> str:
        return json.dumps(
            {
                "file_id": self.file_id,
                "file_unique_id": self.file_unique_id,
                "file_name": self.file_name,
                "file_size": self.file_size,
                "version_name": self.version_name,
                "version_code": self.version_code,
                "published_at": self.published_at.isoformat(),
                "published_by": self.published_by,
                "update_url": self.update_url,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )

    @classmethod
    def from_json(cls, raw: str) -> Optional["AndroidRelease"]:
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            logger.warning("Stored Android release is not valid JSON; ignoring it")
            return None
        if not isinstance(data, dict):
            return None
        file_id = str(data.get("file_id") or "").strip()
        version_name = str(data.get("version_name") or "").strip()
        if not file_id or not version_name:
            # A half-written row must not be handed to a learner as if it were
            # a release: without a file_id there is nothing to send.
            return None
        try:
            published_at = datetime.fromisoformat(str(data.get("published_at")))
        except (TypeError, ValueError):
            published_at = datetime.now(timezone.utc)
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=timezone.utc)
        return cls(
            file_id=file_id,
            file_unique_id=str(data.get("file_unique_id") or ""),
            file_name=str(data.get("file_name") or "hsk-ai.apk"),
            file_size=_as_int(data.get("file_size")) or 0,
            version_name=version_name,
            version_code=_as_int(data.get("version_code")),
            published_at=published_at,
            published_by=_as_int(data.get("published_by")),
            update_url=_https_apk_url(data.get("update_url")),
        )


def _as_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _https_apk_url(value: Any) -> Optional[str]:
    """An update URL the app is allowed to download from, or nothing.

    Validated on the way in and on the way out, because a stored row outlives
    the code that wrote it: anything that is not a plain https `.apk` link is
    treated as absent rather than handed to a client that would then fetch it.
    """

    url = str(value or "").strip()
    if not url or len(url) > 2048:
        return None
    try:
        parsed = urlsplit(url)
    except ValueError:
        return None
    if parsed.scheme != "https" or not parsed.netloc:
        return None
    if parsed.username or parsed.password:
        # A credential in the link would be handed to every installed app.
        return None
    if not parsed.path.lower().endswith(".apk"):
        return None
    return url


def format_size(size_bytes: int) -> str:
    size = max(int(size_bytes or 0), 0)
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.0f} KB"
    return f"{size} B"


@dataclass(frozen=True)
class ArtifactName:
    """What the Gradle artifact name says about the file the admin just sent."""

    version_name: str
    version_code: int
    flavor: str
    build_type: str

    @property
    def is_distributable(self) -> bool:
        """Only a `direct` release may be handed out from the bot.

        The `play` flavour compiles out every external checkout, so a learner
        who installed it could never pay; a `debug` build carries the
        `.debug` application id, so it can never be updated by a real release.
        Either one works well enough on the admin's own phone to look fine and
        then strands whoever installs it.
        """
        return self.flavor.lower() == "direct" and self.build_type.lower() == "release"


def parse_artifact_name(file_name: str) -> Optional[ArtifactName]:
    match = _ARTIFACT_NAME.match(str(file_name or "").strip())
    if not match:
        return None
    return ArtifactName(
        version_name=match.group("version_name"),
        version_code=int(match.group("version_code")),
        flavor=match.group("flavor"),
        build_type=match.group("build_type"),
    )


def parse_version_text(text: str) -> tuple[str, Optional[int]]:
    """Read `1.2.0`, `1.2.0 3` or `1.2.0 (3)` the way an admin would type it."""

    match = _VERSION_TEXT.match(str(text or "").strip())
    if not match:
        raise AndroidReleaseError(
            "Versiyani <code>1.2.0</code> yoki <code>1.2.0 (3)</code> ko'rinishida yozing."
        )
    version_code = match.group("version_code")
    return match.group("version_name"), int(version_code) if version_code else None


class AndroidReleaseService:
    def __init__(self, session):
        self.session = session
        self.settings_repo = BotSettingRepository(session)

    async def current(self) -> Optional[AndroidRelease]:
        raw = await self.settings_repo.get(ANDROID_RELEASE_KEY)
        if not raw:
            return None
        return AndroidRelease.from_json(raw)

    async def publish(
        self,
        *,
        file_id: str,
        file_unique_id: str,
        file_name: str,
        file_size: int,
        version_name: str,
        version_code: Optional[int],
        published_by: Optional[int] = None,
        update_url: Optional[str] = None,
    ) -> AndroidRelease:
        release = AndroidRelease(
            file_id=_require(file_id, "Fayl identifikatori yo'q."),
            file_unique_id=str(file_unique_id or ""),
            file_name=_require(file_name, "Fayl nomi yo'q."),
            file_size=_valid_size(file_size),
            version_name=_require(version_name, "Versiya yo'q."),
            version_code=version_code,
            published_at=datetime.now(timezone.utc),
            published_by=published_by,
            update_url=_https_apk_url(update_url),
        )
        await self.settings_repo.set(ANDROID_RELEASE_KEY, release.to_json())
        await self.session.commit()
        return release

    async def set_update_url(self, url: str) -> AndroidRelease:
        """Point installed apps at this same build.

        Refuses when nothing is published: an update link with no release
        behind it would offer a file the bot cannot even name, and the version
        the app compares against would be missing.
        """

        current = await self.current()
        if current is None:
            raise AndroidReleaseError(
                "Avval APK chiqaring — yangilanish havolasi shunga bog'lanadi."
            )
        validated = _https_apk_url(url)
        if not validated:
            raise AndroidReleaseError(
                "Havola <code>https://</code> bilan boshlanib, <code>.apk</code> "
                "bilan tugashi kerak, va ichida parol bo'lmasligi kerak."
            )
        if current.version_code is None:
            raise AndroidReleaseError(
                "Bu release'da versiya kodi yo'q — ilova nimani solishtirishni "
                "bilmaydi. APK'ni versiya kodi bilan qayta chiqaring."
            )
        updated = replace(current, update_url=validated)
        await self.settings_repo.set(ANDROID_RELEASE_KEY, updated.to_json())
        await self.session.commit()
        return updated

    async def clear_update_url(self) -> AndroidRelease | None:
        """Stop offering in-app updates without withdrawing the file itself."""

        current = await self.current()
        if current is None or current.update_url is None:
            return current
        updated = replace(current, update_url=None)
        await self.settings_repo.set(ANDROID_RELEASE_KEY, updated.to_json())
        await self.session.commit()
        return updated

    async def withdraw(self) -> None:
        """Stop handing out the APK without losing what was published.

        The row is emptied rather than deleted so that `current()` reads
        "nothing to give" while the previous `file_id` stays recoverable from
        the settings history if the withdrawal turns out to be a mistake.
        """
        await self.settings_repo.set(ANDROID_RELEASE_KEY, "")
        await self.session.commit()


def _require(value: Any, message: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise AndroidReleaseError(message)
    return text


def _valid_size(value: Any) -> int:
    size = _as_int(value) or 0
    if size <= 0:
        raise AndroidReleaseError("Fayl bo'sh ko'rinadi.")
    if size > MAX_APK_BYTES:
        raise AndroidReleaseError(
            f"Fayl juda katta ({format_size(size)}). Telegram bot orqali "
            f"{format_size(MAX_APK_BYTES)} gacha yuborish mumkin."
        )
    return size
