from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.course_promo_section import CoursePromoSection
from app.services.broadcast_translation_service import (
    BroadcastTranslationService,
    SUPPORTED_BROADCAST_LANGUAGES,
    encode_localized_broadcast_text,
    localized_broadcast_text_for_language,
)

PROMO_SECTION_KINDS = ("cooperation", "bot_promo")
PROMO_TITLE_MAX = 120
PROMO_BODY_MAX = 600
PROMO_MAX_SECTIONS = 5


class CoursePromoSectionService:
    """Reklama oqimidagi (video ostidagi) promo bo'limlarni boshqaradi:
    hamkorlik taklifi va boshqa bot reklamasi. Matnlar 1 tilda kiritilib,
    avtomatik 3 tilga tarjima qilinadi (broadcast bilan bir xil format)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ---- normalize helpers ----
    @staticmethod
    def normalize_kind(value) -> str:
        kind = str(value or "").strip().lower()
        return kind if kind in PROMO_SECTION_KINDS else "bot_promo"

    @staticmethod
    def normalize_language(value) -> str:
        lang = str(value or "").strip().lower()
        return lang if lang in SUPPORTED_BROADCAST_LANGUAGES else "uz"

    @staticmethod
    def normalize_link(value, kind: str) -> Optional[str]:
        link = str(value or "").strip()
        if not link:
            return None
        if link.startswith("http://") or link.startswith("https://"):
            return link[:512]
        if link.startswith("@"):
            handle = link[1:]
            if kind == "cooperation":
                return f"https://instagram.com/{handle}"[:512]
            return f"https://t.me/{handle}"[:512]
        return f"https://{link}"[:512]

    # ---- translation ----
    async def _localize(self, text: str, source_language: str, *, max_length: int) -> str:
        localized = await BroadcastTranslationService().translate_generic(
            text,
            source_language,
            max_length=max_length,
        )
        return encode_localized_broadcast_text(localized.texts)

    # ---- payloads ----
    @staticmethod
    def public_payload(section: CoursePromoSection, lang: str) -> dict:
        return {
            "id": section.id,
            "kind": section.kind,
            "title": localized_broadcast_text_for_language(section.title, lang),
            "body": localized_broadcast_text_for_language(section.body, lang),
            "link_url": section.link_url or "",
        }

    @staticmethod
    def admin_payload(section: CoursePromoSection) -> dict:
        src = section.source_language if section.source_language in SUPPORTED_BROADCAST_LANGUAGES else "uz"
        return {
            "id": section.id,
            "kind": section.kind,
            "title": localized_broadcast_text_for_language(section.title, src),
            "body": localized_broadcast_text_for_language(section.body, src),
            "link_url": section.link_url or "",
            "source_language": src,
            "is_active": bool(section.is_active),
            "sort_order": int(section.sort_order or 0),
        }

    # ---- queries ----
    async def list_active(self, lang: str) -> list[dict]:
        result = await self.session.execute(
            select(CoursePromoSection)
            .where(CoursePromoSection.is_active.is_(True))
            .order_by(CoursePromoSection.sort_order.asc(), CoursePromoSection.id.asc())
        )
        return [self.public_payload(item, lang) for item in result.scalars().all()]

    async def list_for_admin(self) -> list[dict]:
        result = await self.session.execute(
            select(CoursePromoSection).order_by(
                CoursePromoSection.sort_order.asc(), CoursePromoSection.id.asc()
            )
        )
        return [self.admin_payload(item) for item in result.scalars().all()]

    async def get(self, section_id: int) -> Optional[CoursePromoSection]:
        return await self.session.get(CoursePromoSection, section_id)

    async def count(self) -> int:
        result = await self.session.execute(select(func.count(CoursePromoSection.id)))
        return int(result.scalar_one() or 0)

    async def _next_sort_order(self) -> int:
        result = await self.session.execute(select(func.max(CoursePromoSection.sort_order)))
        current = result.scalar_one()
        return int(current or 0) + 1

    async def create(
        self,
        *,
        kind: str,
        title: str,
        body: str,
        link_url: str,
        source_language: str,
        created_by_telegram_id: Optional[int] = None,
    ) -> CoursePromoSection:
        kind = self.normalize_kind(kind)
        source_language = self.normalize_language(source_language)
        title_json = await self._localize(title, source_language, max_length=PROMO_TITLE_MAX)
        body_json = await self._localize(body, source_language, max_length=PROMO_BODY_MAX) if body else None
        section = CoursePromoSection(
            kind=kind,
            title=title_json,
            body=body_json,
            link_url=self.normalize_link(link_url, kind),
            source_language=source_language,
            sort_order=await self._next_sort_order(),
            created_by_telegram_id=created_by_telegram_id,
        )
        self.session.add(section)
        await self.session.flush()
        return section

    async def update(
        self,
        section_id: int,
        *,
        kind: str,
        title: str,
        body: str,
        link_url: str,
        source_language: str,
    ) -> Optional[CoursePromoSection]:
        section = await self.get(section_id)
        if not section:
            return None
        kind = self.normalize_kind(kind)
        source_language = self.normalize_language(source_language)
        section.kind = kind
        section.source_language = source_language
        section.title = await self._localize(title, source_language, max_length=PROMO_TITLE_MAX)
        section.body = (
            await self._localize(body, source_language, max_length=PROMO_BODY_MAX) if body else None
        )
        section.link_url = self.normalize_link(link_url, kind)
        return section

    async def set_active(self, section_id: int, is_active: bool) -> Optional[CoursePromoSection]:
        section = await self.get(section_id)
        if not section:
            return None
        section.is_active = bool(is_active)
        return section

    async def delete(self, section_id: int) -> bool:
        section = await self.get(section_id)
        if not section:
            return False
        await self.session.delete(section)
        return True
