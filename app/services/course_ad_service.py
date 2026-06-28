from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.course_ad import CourseAdCreative, CourseAdView


COURSE_AD_PLACEMENTS = ("start", "middle", "end")
COURSE_AD_MIN_SECONDS = 5
COURSE_AD_MAX_SECONDS = 120
COURSE_AD_DEFAULT_SECONDS = 7
COURSE_AD_MEDIA_ROOT = "app/static/uploads/course_ads"


class CourseAdService:
    def __init__(self, session: AsyncSession):
        self.session = session

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
    def normalize_link(value) -> str | None:
        link = str(value or "").strip()
        if not link:
            return None
        if not (link.startswith("http://") or link.startswith("https://")):
            link = "https://" + link
        return link[:512]

    @classmethod
    def payload(cls, ad: CourseAdCreative) -> dict:
        return {
            "id": int(ad.id),
            "title": ad.title,
            "media_type": ad.media_type,
            "media_url": f"/uploads/course_ads/{ad.media_path}",
            "link_url": getattr(ad, "link_url", None) or None,
            "duration_seconds": cls.normalize_duration(ad.duration_seconds),
            "is_active": bool(ad.is_active),
            "created_at": ad.created_at.isoformat() if ad.created_at else None,
        }

    async def list_for_admin(self) -> list[dict]:
        result = await self.session.execute(
            select(CourseAdCreative).order_by(CourseAdCreative.created_at.desc(), CourseAdCreative.id.desc())
        )
        return [self.payload(ad) for ad in result.scalars().all()]

    async def create_video(
        self,
        *,
        title: str,
        media_path: str,
        duration_seconds: int = COURSE_AD_DEFAULT_SECONDS,
        link_url: str | None = None,
        created_by_telegram_id: int | None = None,
    ) -> CourseAdCreative:
        ad = CourseAdCreative(
            title=(title or "Course ad").strip()[:120],
            media_path=media_path,
            media_type="video",
            link_url=self.normalize_link(link_url),
            duration_seconds=self.normalize_duration(duration_seconds),
            is_active=True,
            created_by_telegram_id=created_by_telegram_id,
        )
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

    async def get_active_ad(self) -> CourseAdCreative | None:
        result = await self.session.execute(
            select(CourseAdCreative)
            .where(CourseAdCreative.is_active.is_(True))
            .order_by(CourseAdCreative.created_at.desc(), CourseAdCreative.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_active_payload(self) -> dict | None:
        ad = await self.get_active_ad()
        return self.payload(ad) if ad else None

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
