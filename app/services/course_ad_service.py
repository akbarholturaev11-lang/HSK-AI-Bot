import contextlib
import hashlib
import os

from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.course_ad import CourseAdCreative, CourseAdView


COURSE_AD_PLACEMENTS = ("start", "middle", "end")
COURSE_AD_MIN_SECONDS = 5
COURSE_AD_MAX_SECONDS = 120
COURSE_AD_DEFAULT_SECONDS = 7
# Media doimiy diskda saqlanishi kerak. Railway'da runtime disk EPHEMERAL —
# har deploy/restartda `app/static/uploads` tozalanadi va yuklangan reklama
# fayllari yo'qoladi (DB yozuvi qoladi, fayl esa 404 → mini app'da qora ekran).
# `RAILWAY_VOLUME_MOUNT_PATH` (Railway Volume ulanganda avtomatik) yoki `MEDIA_ROOT`
# berilsa — media o'sha doimiy diskka saqlanadi; bo'lmasa lokal/dev fallback.
MEDIA_ROOT_BASE = (
    os.environ.get("MEDIA_ROOT")
    or os.environ.get("RAILWAY_VOLUME_MOUNT_PATH")
    or "app/static/uploads"
)
COURSE_AD_MEDIA_ROOT = os.path.join(MEDIA_ROOT_BASE, "course_ads")
# Reklama tillari. "all" — barcha tillardagi foydalanuvchilarga ko'rsatiladi.
COURSE_AD_LANGUAGES = ("uz", "ru", "tj")
COURSE_AD_ALL_LANGUAGES = "all"
# Reklama turlari: odiy (oddiy), hamkorlik (reklama qabul qilish/hamkorlik),
# bot (o'z botlarini reklama qilish). Odiy — hozirgi xatti-harakat.
COURSE_AD_TYPES = ("odiy", "hamkorlik", "bot")
COURSE_AD_DEFAULT_TYPE = "odiy"


class CourseAdService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._media_backup_changed = False

    @property
    def media_backup_changed(self) -> bool:
        return self._media_backup_changed

    @staticmethod
    def normalize_placement(value: str | None) -> str:
        placement = str(value or "").strip().lower()
        if placement not in COURSE_AD_PLACEMENTS:
            return "start"
        return placement

    @staticmethod
    def normalize_duration(value) -> int:
        try:
            duration = int(value or COURSE_AD_DEFAULT_SECONDS)
        except (TypeError, ValueError):
            duration = COURSE_AD_DEFAULT_SECONDS
        return min(max(duration, COURSE_AD_MIN_SECONDS), COURSE_AD_MAX_SECONDS)

    @staticmethod
    def normalize_language(value) -> str:
        """Reklama tilini normallashtiradi: uz/ru/tj yoki "all" (barchasi)."""
        lang = str(value or "").strip().lower()
        if lang in COURSE_AD_LANGUAGES:
            return lang
        return COURSE_AD_ALL_LANGUAGES

    @staticmethod
    def normalize_link(value) -> str | None:
        link = str(value or "").strip()
        if not link:
            return None
        if link.startswith("@"):
            # @username — Telegram foydalanuvchi/bot havolasiga aylantiramiz.
            link = "https://t.me/" + link[1:]
        if not (link.startswith("http://") or link.startswith("https://")):
            link = "https://" + link
        return link[:512]

    @staticmethod
    def normalize_ad_type(value) -> str:
        ad_type = str(value or "").strip().lower()
        return ad_type if ad_type in COURSE_AD_TYPES else COURSE_AD_DEFAULT_TYPE

    @staticmethod
    def normalize_button_text(value) -> str | None:
        text = str(value or "").strip()
        return text[:64] or None

    @staticmethod
    def media_checksum(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    @classmethod
    def _backup_bytes(cls, ad: CourseAdCreative) -> bytes | None:
        data = getattr(ad, "media_blob", None)
        if isinstance(data, memoryview):
            data = data.tobytes()
        if not data:
            return None
        checksum = getattr(ad, "media_checksum", None)
        if checksum and cls.media_checksum(data) != checksum:
            return None
        return bytes(data)

    @staticmethod
    def _media_full_path(media_path: str | None) -> str | None:
        if not media_path:
            return None
        return os.path.join(COURSE_AD_MEDIA_ROOT, os.path.basename(str(media_path)))

    @staticmethod
    def _file_available(path: str | None) -> bool:
        if not path:
            return False
        try:
            return os.path.exists(path) and os.path.getsize(path) > 0
        except OSError:
            return False

    @classmethod
    def read_media_file(cls, media_path: str) -> bytes:
        full_path = cls._media_full_path(media_path)
        if not cls._file_available(full_path):
            raise OSError("course ad media file is missing")
        with open(str(full_path), "rb") as handle:
            return handle.read()

    @classmethod
    def attach_media_backup(cls, ad: CourseAdCreative, data: bytes | None) -> bool:
        if not data:
            return False
        checksum = cls.media_checksum(data)
        if (
            getattr(ad, "media_blob", None) == data
            and getattr(ad, "media_checksum", None) == checksum
        ):
            return False
        ad.media_blob = data
        ad.media_size = len(data)
        ad.media_checksum = checksum
        return True

    @classmethod
    def ensure_media_available(cls, ad: CourseAdCreative) -> tuple[bool, bool]:
        path = cls._media_full_path(getattr(ad, "media_path", None))
        if cls._file_available(path):
            return True, False
        data = cls._backup_bytes(ad)
        if not data or not path:
            return False, False
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp_path = f"{path}.restore"
        try:
            with open(tmp_path, "wb") as handle:
                handle.write(data)
            os.replace(tmp_path, path)
        except OSError:
            with contextlib.suppress(OSError):
                os.remove(tmp_path)
            return False, False
        return cls._file_available(path), True

    async def ensure_media_backup(self, ad: CourseAdCreative) -> bool:
        if self._backup_bytes(ad):
            return False
        try:
            data = self.read_media_file(getattr(ad, "media_path", ""))
        except OSError:
            return False
        if not self.attach_media_backup(ad, data):
            return False
        self._media_backup_changed = True
        await self.session.flush()
        return True

    @staticmethod
    def media_available(ad: CourseAdCreative) -> bool:
        """Reklama media fayli diskda haqiqatan mavjudmi.

        Railway ephemeral disk restartda tozalanadi — DB'da yozuv qolib, fayl
        yo'qolishi mumkin. Bunday reklamani foydalanuvchiga KO'RSATMAYMIZ, aks holda
        <video> 404 oladi va mini app'da qora ekran ("video yuklanmadi") chiqadi.
        """
        return CourseAdService.ensure_media_available(ad)[0]

    @classmethod
    def payload(cls, ad: CourseAdCreative) -> dict:
        media_available, media_restored = cls.ensure_media_available(ad)
        return {
            "id": int(ad.id),
            "title": ad.title,
            "media_type": ad.media_type,
            "media_url": f"/uploads/course_ads/{ad.media_path}",
            "link_url": getattr(ad, "link_url", None) or None,
            "language": cls.normalize_language(getattr(ad, "language", None)),
            "ad_type": cls.normalize_ad_type(getattr(ad, "ad_type", None)),
            "button_text": getattr(ad, "button_text", None) or None,
            "duration_seconds": cls.normalize_duration(ad.duration_seconds),
            "is_active": bool(ad.is_active),
            "media_available": media_available,
            "media_restored": media_restored,
            "media_backed_up": bool(cls._backup_bytes(ad)),
            "media_size": getattr(ad, "media_size", None) or None,
            "created_at": ad.created_at.isoformat() if ad.created_at else None,
        }

    async def list_for_admin(self) -> list[dict]:
        result = await self.session.execute(
            select(CourseAdCreative).order_by(CourseAdCreative.created_at.desc(), CourseAdCreative.id.desc())
        )
        ads = result.scalars().all()
        for ad in ads:
            await self.ensure_media_backup(ad)
        return [self.payload(ad) for ad in ads]

    async def create_video(
        self,
        *,
        title: str,
        media_path: str,
        duration_seconds: int = COURSE_AD_DEFAULT_SECONDS,
        link_url: str | None = None,
        language: str = COURSE_AD_ALL_LANGUAGES,
        ad_type: str = COURSE_AD_DEFAULT_TYPE,
        button_text: str | None = None,
        media_blob: bytes | None = None,
        created_by_telegram_id: int | None = None,
    ) -> CourseAdCreative:
        ad = CourseAdCreative(
            title=(title or "Course ad").strip()[:120],
            media_path=media_path,
            media_type="video",
            link_url=self.normalize_link(link_url),
            language=self.normalize_language(language),
            ad_type=self.normalize_ad_type(ad_type),
            button_text=self.normalize_button_text(button_text),
            duration_seconds=self.normalize_duration(duration_seconds),
            is_active=True,
            created_by_telegram_id=created_by_telegram_id,
        )
        self.attach_media_backup(ad, media_blob)
        self.session.add(ad)
        await self.session.flush()
        return ad

    async def set_active(self, ad_id: int, is_active: bool) -> CourseAdCreative | None:
        result = await self.session.execute(
            select(CourseAdCreative).where(CourseAdCreative.id == ad_id)
        )
        ad = result.scalar_one_or_none()
        if not ad:
            return None
        ad.is_active = bool(is_active)
        await self.session.flush()
        return ad

    async def delete(self, ad_id: int) -> str | None:
        """Reklamani butunlay o'chiradi. O'chirilgan media fayl nomini qaytaradi
        (mavjud bo'lsa) — chaqiruvchi diskdan ham o'chirishi uchun."""
        result = await self.session.execute(
            select(CourseAdCreative).where(CourseAdCreative.id == ad_id)
        )
        ad = result.scalar_one_or_none()
        if not ad:
            return None
        media_path = ad.media_path
        await self.session.delete(ad)
        await self.session.flush()
        return media_path

    @classmethod
    def _language_filter(cls, language: str | None):
        """Foydalanuvchi tili uchun mos reklamalarni filterlash sharti.
        Til berilsa: shu tildagi YOKI "all" (barcha tillar) reklamalar.
        Til berilmasa: filtersiz (barcha aktivlar)."""
        if not language:
            return None
        target = cls.normalize_language(language)
        return CourseAdCreative.language.in_((target, COURSE_AD_ALL_LANGUAGES))

    async def get_active_ad(self, language: str | None = None) -> CourseAdCreative | None:
        stmt = select(CourseAdCreative).where(CourseAdCreative.is_active.is_(True))
        lang_filter = self._language_filter(language)
        if lang_filter is not None:
            stmt = stmt.where(lang_filter)
        stmt = stmt.order_by(
            CourseAdCreative.created_at.desc(), CourseAdCreative.id.desc()
        )
        result = await self.session.execute(stmt)
        # Faqat media fayli haqiqatan diskda mavjud bo'lgan (eng yangi) reklamani qaytaramiz.
        for ad in result.scalars().all():
            if self.media_available(ad):
                await self.ensure_media_backup(ad)
                return ad
        return None

    async def get_active_payload(self, language: str | None = None) -> dict | None:
        ad = await self.get_active_ad(language=language)
        return self.payload(ad) if ad else None

    async def list_active(self, language: str | None = None) -> list[CourseAdCreative]:
        """Aktiv reklamalar — ketma-ket ko'rsatish uchun (eskisidan yangisiga).
        `language` berilsa, faqat shu til + "all" reklamalari qaytadi."""
        stmt = select(CourseAdCreative).where(CourseAdCreative.is_active.is_(True))
        lang_filter = self._language_filter(language)
        if lang_filter is not None:
            stmt = stmt.where(lang_filter)
        stmt = stmt.order_by(CourseAdCreative.created_at.asc(), CourseAdCreative.id.asc())
        result = await self.session.execute(stmt)
        # Media fayli yo'q (ephemeral diskda o'chib ketgan) reklamalarni tashlab yuboramiz —
        # ular mini app'da qora ekran beradi. Fayli borlari ketma-ket ko'rsatiladi.
        ads = []
        for ad in result.scalars().all():
            if self.media_available(ad):
                await self.ensure_media_backup(ad)
                ads.append(ad)
        return ads

    async def list_active_payloads(self, language: str | None = None) -> list[dict]:
        return [self.payload(ad) for ad in await self.list_active(language=language)]

    async def record_view(
        self,
        *,
        user,
        ad_id: int,
        level: str,
        lesson_order: int,
        placement: str,
        watched_seconds: int,
    ) -> dict:
        placement = self.normalize_placement(placement)
        result = await self.session.execute(
            select(CourseAdCreative).where(CourseAdCreative.id == int(ad_id or 0))
        )
        ad = result.scalar_one_or_none()
        if not ad:
            return {"ok": False, "error": "ad_not_found"}

        required_seconds = self.normalize_duration(ad.duration_seconds)
        try:
            watched = int(watched_seconds or 0)
        except (TypeError, ValueError):
            watched = 0
        completed = watched >= required_seconds

        view = CourseAdView(
            ad_id=ad.id,
            user_id=getattr(user, "id", None),
            user_telegram_id=int(getattr(user, "telegram_id", 0) or 0),
            level=str(level or "hsk1")[:16],
            lesson_order=int(lesson_order or 0),
            placement=placement,
            watched_seconds=max(0, watched),
            completed=completed,
        )
        self.session.add(view)
        await self.session.flush()
        return {
            "ok": completed,
            "required_seconds": required_seconds,
            "watched_seconds": max(0, watched),
            "placement": placement,
        }

    async def has_completed_required_views(
        self,
        *,
        user_telegram_id: int,
        level: str,
        lesson_order: int,
    ) -> bool:
        result = await self.session.execute(
            select(distinct(CourseAdView.placement))
            .where(CourseAdView.user_telegram_id == int(user_telegram_id))
            .where(CourseAdView.level == str(level or "hsk1")[:16])
            .where(CourseAdView.lesson_order == int(lesson_order or 0))
            .where(CourseAdView.completed.is_(True))
            .where(CourseAdView.placement.in_(COURSE_AD_PLACEMENTS))
        )
        placements = {str(item) for item in result.scalars().all()}
        return set(COURSE_AD_PLACEMENTS).issubset(placements)
