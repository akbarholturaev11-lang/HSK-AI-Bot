"""Reklama joylari — aynan ikkita, har biri alohida boshqariladi.

Ilgari reklama uch joyda tarqoq edi: mashq sessiyasining boshi/o'rtasi/oxiri,
dars yakuni, va Mini App ochilishi. Ustiga uning "kuniga necha marta" chegarasi
`localStorage` da edi — ya'ni chegara emas, taklif.

Endi ikkita joy bor:

* `lesson_end`    — dars tugagach;
* `screen_center` — ekran markazida, qaysi bo'limda bo'lishidan qat'i nazar.

Va chegara SERVERDA, TELEGRAM AKKAUNTI bo'yicha sanaladi. Ya'ni telefonda
ikkitasini ko'rgan odam desktopda uchinchisini olmaydi. Aynan shu "bitta
boshqaruv, bir nechta qurilma" degani.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import func, select

from app.db.models.course_ad import CourseAdView
from app.repositories.bot_setting_repo import BotSettingRepository
from app.services import course_daily_window
from app.services.course_ad_service import CourseAdService


logger = logging.getLogger(__name__)


AD_PLACEMENTS_KEY = "ad_placements_v1"

PLACEMENT_LESSON_END = "lesson_end"
PLACEMENT_SCREEN_CENTER = "screen_center"
AD_PLACEMENTS = (PLACEMENT_LESSON_END, PLACEMENT_SCREEN_CENTER)

AUDIENCE_FREE_ONLY = "free_only"
AUDIENCE_EVERYONE = "everyone"
AUDIENCES = frozenset({AUDIENCE_FREE_ONLY, AUDIENCE_EVERYONE})

MAX_DAILY_CAP = 50
MAX_SKIP_SECONDS = 60

#: Kelishilgan qiymatlar: markazdagi reklama faqat bepul foydalanuvchilarga,
#: kuniga ko'pi bilan 2 marta.
DEFAULT_SETTINGS = {
    PLACEMENT_LESSON_END: {
        "enabled": True,
        "audience": AUDIENCE_FREE_ONLY,
        "daily_cap": 0,  # 0 = cheklovsiz
        "skip_after_seconds": 0,
        "clients": ["miniapp", "android", "desktop"],
    },
    PLACEMENT_SCREEN_CENTER: {
        "enabled": True,
        "audience": AUDIENCE_FREE_ONLY,
        "daily_cap": 2,
        "skip_after_seconds": 5,
        "clients": ["miniapp", "android", "desktop"],
    },
}


def normalize_placement(value) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in AD_PLACEMENTS else PLACEMENT_SCREEN_CENTER


def normalize_placements(value) -> str:
    """Vergul bilan ajratilgan to'plamni tozalaydi.

    Bo'sh yoki tanib bo'lmaydigan qiymat `screen_center` ga tushadi — ya'ni
    reklama yo'qolib qolmaydi, lekin dars yakunidagi maxsus joyga ham
    tasodifan tushmaydi.
    """
    raw = str(value or "")
    found = [item.strip().lower() for item in raw.split(",")]
    kept = [item for item in AD_PLACEMENTS if item in found]
    return ",".join(kept) if kept else PLACEMENT_SCREEN_CENTER


def placements_of(ad) -> list[str]:
    return normalize_placements(getattr(ad, "placements", None)).split(",")


@dataclass(frozen=True)
class PlacementRule:
    enabled: bool
    audience: str
    daily_cap: int
    skip_after_seconds: int
    clients: tuple[str, ...]

    def allows_client(self, client: str) -> bool:
        return not self.clients or str(client or "").strip().lower() in self.clients

    def as_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "audience": self.audience,
            "daily_cap": self.daily_cap,
            "skip_after_seconds": self.skip_after_seconds,
            "clients": list(self.clients),
        }


@dataclass(frozen=True)
class AdPlacementSettings:
    rules: dict = field(default_factory=dict)
    saved_at: datetime | None = None
    updated_by_telegram_id: int | None = None

    def rule(self, placement: str) -> PlacementRule:
        return self.rules.get(normalize_placement(placement)) or _default_rule(
            normalize_placement(placement)
        )

    def public_payload(self) -> dict:
        return {
            "version": 1,
            "placements": {
                placement: self.rule(placement).as_dict() for placement in AD_PLACEMENTS
            },
            "saved_at": self.saved_at.isoformat() if self.saved_at else None,
            "updated_by_telegram_id": self.updated_by_telegram_id,
        }


def _clean_rule(raw, placement: str) -> PlacementRule:
    default = DEFAULT_SETTINGS[placement]
    if not isinstance(raw, dict):
        raw = {}

    audience = str(raw.get("audience") or default["audience"]).strip().lower()
    if audience not in AUDIENCES:
        audience = default["audience"]

    try:
        cap = int(raw.get("daily_cap", default["daily_cap"]))
    except (TypeError, ValueError):
        cap = default["daily_cap"]
    cap = max(0, min(cap, MAX_DAILY_CAP))

    try:
        skip = int(raw.get("skip_after_seconds", default["skip_after_seconds"]))
    except (TypeError, ValueError):
        skip = default["skip_after_seconds"]
    skip = max(0, min(skip, MAX_SKIP_SECONDS))

    clients = raw.get("clients")
    if isinstance(clients, (list, tuple)) and clients:
        cleaned = tuple(str(item).strip().lower() for item in clients if str(item).strip())
    else:
        cleaned = tuple(default["clients"])

    return PlacementRule(
        enabled=bool(raw.get("enabled", default["enabled"])),
        audience=audience,
        daily_cap=cap,
        skip_after_seconds=skip,
        clients=cleaned,
    )


def _default_rule(placement: str) -> PlacementRule:
    return _clean_rule(None, placement)


def default_settings() -> AdPlacementSettings:
    return AdPlacementSettings(
        rules={placement: _default_rule(placement) for placement in AD_PLACEMENTS}
    )


def settings_from_payload(payload) -> AdPlacementSettings:
    if not isinstance(payload, dict):
        return default_settings()
    raw = payload.get("placements")
    raw = raw if isinstance(raw, dict) else {}
    try:
        updated_by = int(payload.get("updated_by_telegram_id") or 0) or None
    except (TypeError, ValueError):
        updated_by = None
    saved_at = payload.get("saved_at")
    parsed = None
    if saved_at:
        try:
            parsed = datetime.fromisoformat(str(saved_at).replace("Z", "+00:00"))
        except ValueError:
            parsed = None
    return AdPlacementSettings(
        rules={
            placement: _clean_rule(raw.get(placement), placement)
            for placement in AD_PLACEMENTS
        },
        saved_at=parsed,
        updated_by_telegram_id=updated_by,
    )


class AdPlacementService:
    def __init__(self, session):
        self.session = session
        self.ads = CourseAdService(session)

    # --- sozlama ----------------------------------------------------------

    async def get_settings(self) -> AdPlacementSettings:
        raw = await BotSettingRepository(self.session).get(AD_PLACEMENTS_KEY)
        if not raw:
            return default_settings()
        try:
            payload = json.loads(raw)
        except (TypeError, ValueError):
            logger.warning("Buzilgan reklama joylari sozlamasi — defaultga qaytamiz")
            return default_settings()
        return settings_from_payload(payload)

    async def save_settings(
        self, payload: dict, *, updated_by_telegram_id: int | None = None
    ) -> AdPlacementSettings:
        if not isinstance(payload, dict):
            raise ValueError("invalid_ad_placements")
        raw = payload.get("placements")
        if not isinstance(raw, dict) or not raw:
            raise ValueError("invalid_ad_placements")
        for placement in raw:
            if placement not in AD_PLACEMENTS:
                raise ValueError("invalid_ad_placements")

        settings = AdPlacementSettings(
            rules={
                placement: _clean_rule(raw.get(placement), placement)
                for placement in AD_PLACEMENTS
            },
            saved_at=datetime.now(timezone.utc),
            updated_by_telegram_id=int(updated_by_telegram_id or 0) or None,
        )
        await BotSettingRepository(self.session).set(
            AD_PLACEMENTS_KEY,
            json.dumps(
                settings.public_payload(), ensure_ascii=False, separators=(",", ":")
            ),
        )
        return settings

    # --- kunlik hisob -----------------------------------------------------

    async def _offset_minutes(self, user) -> int:
        """O'quvchining vaqt mintaqasi — kun chegarasi shunga qarab olinadi."""
        from app.db.models.course_miniapp_profile import CourseMiniAppProfile

        user_id = getattr(user, "id", None)
        if user_id is None:
            return 0
        result = await self.session.execute(
            select(CourseMiniAppProfile.timezone_offset_minutes).where(
                CourseMiniAppProfile.user_id == int(user_id)
            )
        )
        return course_daily_window.normalize_offset_minutes(
            result.scalar_one_or_none() or 0
        )

    async def used_today(self, user, *, placement: str) -> int:
        """Bugun shu joyda nechta reklama ko'rilgan — QURILMADAN qat'i nazar."""
        placement = normalize_placement(placement)
        offset = await self._offset_minutes(user)
        since = course_daily_window.day_start(offset)
        result = await self.session.execute(
            select(func.count(CourseAdView.id)).where(
                CourseAdView.user_telegram_id == int(user.telegram_id),
                CourseAdView.placement == placement,
                CourseAdView.created_at >= since,
            )
        )
        return int(result.scalar_one() or 0)

    async def status(self, user, *, placement: str, client: str = "") -> dict:
        placement = normalize_placement(placement)
        rule = (await self.get_settings()).rule(placement)
        offset = await self._offset_minutes(user)

        if not rule.enabled or not rule.allows_client(client):
            return {
                "enabled": False,
                "limit": rule.daily_cap or None,
                "used": 0,
                "remaining": 0,
                "reset_at": None,
            }

        used = await self.used_today(user, placement=placement)
        limit = rule.daily_cap or None
        return {
            "enabled": True,
            "limit": limit,
            "used": used,
            "remaining": None if limit is None else max(0, limit - used),
            "reset_at": course_daily_window.next_day_reset(offset).isoformat(),
        }

    # --- tanlash ----------------------------------------------------------

    async def list_for_placement(
        self, placement: str, *, language: str | None = None
    ) -> list:
        """Shu joyda chiqishi mumkin bo'lgan faol reklamalar.

        `CourseAdService.list_active` ATAYLAB ishlatilmaydi: u eski slot
        filtrini qo'llaydi (tur → joy), bu esa aynan biz ajratayotgan bog'lanish.
        Media tekshiruvi esa saqlanadi — fayli yo'q reklama WebView'da qora
        ekran beradi.
        """
        from app.db.models.course_ad import CourseAdCreative

        placement = normalize_placement(placement)
        stmt = (
            self.ads._select_without_blob()
            .where(CourseAdCreative.is_active.is_(True))
            .order_by(CourseAdCreative.created_at.asc(), CourseAdCreative.id.asc())
        )
        lang_filter = self.ads._language_filter(
            CourseAdService.normalize_language(language)
        )
        if lang_filter is not None:
            stmt = stmt.where(lang_filter)

        result = await self.session.execute(stmt)
        ads = []
        for ad in result.scalars().all():
            if placement not in placements_of(ad):
                continue
            if (await self.ads.ensure_media_available(ad))[0]:
                ads.append(ad)
        return ads

    async def next_ad(
        self,
        user,
        *,
        placement: str,
        client: str = "",
        language: str | None = None,
        lesson_order: int | None = None,
    ) -> dict | None:
        """Shu joyda ko'rsatiladigan reklama, yoki `None`.

        `None` qaytishi — kutilgan holat, xato emas: chegara tugagan, joy
        o'chirilgan, foydalanuvchi obunachi yoki katalog bo'sh.
        """
        placement = normalize_placement(placement)
        rule = (await self.get_settings()).rule(placement)
        if not rule.enabled or not rule.allows_client(client):
            return None

        if rule.audience == AUDIENCE_FREE_ONLY and _has_full_access(user):
            return None

        if rule.daily_cap:
            used = await self.used_today(user, placement=placement)
            if used >= rule.daily_cap:
                return None

        candidates = await self.list_for_placement(
            placement, language=language or getattr(user, "language", None)
        )
        if not candidates:
            return None

        # Dars yakunida ketma-ket bir xil reklama chiqmasin: dars raqami
        # bo'yicha aylanma tanlov (tasodifiy emas — takrorlanadigan bo'lsin).
        index = int(lesson_order or 0) % len(candidates)
        payload = self.ads.payload(candidates[index])
        payload["placement"] = placement
        payload["skip_after_seconds"] = rule.skip_after_seconds
        return payload

    async def record_view(
        self,
        user,
        *,
        placement: str,
        ad_id: int,
        watched_seconds: int,
        level: str | None = None,
        lesson_order: int | None = None,
    ) -> dict:
        """Ko'rsatishni yozadi. Kunlik chegara aynan shu qatorlardan sanaladi.

        `CourseAdService.record_view` ATAYLAB ishlatilmaydi: u placement ni
        eski `start/middle/end` ro'yxati bo'yicha normalizatsiya qiladi va
        `screen_center` ni jimgina `start` ga aylantirib yuborardi — ya'ni
        chegara hech qachon to'lmasdi.
        """
        from app.db.models.course_ad import CourseAdCreative

        placement = normalize_placement(placement)
        result = await self.session.execute(
            self.ads._select_without_blob().where(
                CourseAdCreative.id == int(ad_id or 0)
            )
        )
        ad = result.scalar_one_or_none()
        if not ad:
            return {"ok": False, "error": "ad_not_found"}

        required = CourseAdService.normalize_duration(ad.duration_seconds)
        try:
            watched = int(watched_seconds or 0)
        except (TypeError, ValueError):
            watched = 0

        self.session.add(
            CourseAdView(
                ad_id=ad.id,
                user_id=getattr(user, "id", None),
                user_telegram_id=int(getattr(user, "telegram_id", 0) or 0),
                level=str(level or "hsk1")[:16],
                lesson_order=int(lesson_order or 0),
                placement=placement,
                watched_seconds=watched,
                completed=watched >= required,
                created_at=datetime.now(timezone.utc),
            )
        )
        await self.session.flush()
        return {
            "ok": True,
            "placement": placement,
            "required_seconds": required,
            "watched_seconds": watched,
        }


def _has_full_access(user) -> bool:
    # Kech import: `state` moduli `user_access_state_service` ni tortadi va
    # bu yerda aylanma import bo'lib qolmasligi kerak.
    from app.services.entitlements.state import has_full_access, resolve_state

    return has_full_access(resolve_state(user))
