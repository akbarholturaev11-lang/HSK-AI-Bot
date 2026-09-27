"""`course_mistake_targets` jadvali bilan ishlash (yozish, backfill, o'qish).

Takror mantig'i (`CourseMistakeService`) shu yerdan faqat nishon qatorlarini
oladi va yangilaydi; savol yasash `mistake_drill_factory` da.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import func, select, update

from app.db.models.course_mistake import CourseMistake
from app.db.models.course_mistake_target import CourseMistakeTarget


UNRESOLVABLE_TARGET_KEY = "-"
MAX_WRONG_VARIANTS = 3
SYNC_BATCH = 300


def aware(value: datetime | None) -> datetime | None:
    """sqlite naive, Postgres aware qaytaradi — solishtirishdan oldin tenglashtiramiz."""
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _loads(value) -> dict:
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(value or "{}")
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _dumps(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def split_csv(value) -> list[str]:
    return [part for part in str(value or "").split(",") if part]


def merge_payload(old: dict, new: dict) -> dict:
    """Yangi xato eski nishonga ma'lumot qo'shadi, lekin borini buzmaydi."""
    merged = dict(old)
    for key, value in new.items():
        if key == "wrong":
            variants = list(old.get("wrong") or [])
            for item in value or []:
                if item and item not in variants:
                    variants.append(item)
            merged["wrong"] = variants[-MAX_WRONG_VARIANTS:]
        elif key in {"translation", "meaning"} and isinstance(value, dict):
            merged[key] = {**value, **(old.get(key) or {})}
        elif not old.get(key) and value:
            merged[key] = value
    return merged


def drill_target(row: CourseMistakeTarget) -> dict:
    """DB qatori -> `mistake_drill_factory` kutadigan nishon."""
    return {
        "id": int(row.id),
        "category": row.category,
        "kind": row.kind,
        "zh": row.zh,
        "level": row.level,
        "payload": _loads(row.payload_json),
    }


class CourseMistakeTargetStore:
    def __init__(self, session):
        self.session = session

    async def get(self, user_id: int, category: str, key: str) -> CourseMistakeTarget | None:
        result = await self.session.execute(
            select(CourseMistakeTarget).where(
                CourseMistakeTarget.user_id == user_id,
                CourseMistakeTarget.category == category,
                CourseMistakeTarget.target_key == key,
            )
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        user_id: int,
        *,
        category: str,
        target: dict,
        source: str,
        now: datetime,
        weight: int = 1,
        seen_at: datetime | None = None,
        new_mistake: bool = True,
    ) -> CourseMistakeTarget:
        """Nishonni yozadi. Yangi xato progressni nolga tushiradi va yopilganini qayta ochadi."""
        seen_at = aware(seen_at or now)
        row = await self.get(user_id, category, target["key"])
        payload = target.get("payload") or {}
        if row is None:
            row = CourseMistakeTarget(
                user_id=user_id,
                category=category,
                kind=target["kind"],
                target_key=target["key"],
                zh=str(target.get("zh") or "")[:1000],
                level=target.get("level"),
                payload_json=_dumps(payload),
                sources=source[:32],
                status="active",
                passed_formats="",
                wrong_count=max(1, int(weight or 1)),
                review_count=0,
                cleared_count=0,
                first_seen_at=seen_at,
                last_seen_at=seen_at,
            )
            self.session.add(row)
            await self.session.flush()
            return row
        row.payload_json = _dumps(merge_payload(_loads(row.payload_json), payload))
        sources = split_csv(row.sources)
        if source and source not in sources:
            sources.append(source[:32])
        row.sources = ",".join(sources)[:200]
        row.wrong_count = int(row.wrong_count or 0) + max(1, int(weight or 1))
        if seen_at > aware(row.last_seen_at):
            row.last_seen_at = seen_at
        if new_mistake:
            row.status = "active"
            row.passed_formats = ""
        return row

    async def unsynced_rows(self, user_id: int, limit: int = SYNC_BATCH) -> list[CourseMistake]:
        result = await self.session.execute(
            select(CourseMistake)
            .where(
                CourseMistake.user_id == user_id,
                CourseMistake.wrong_count > CourseMistake.resolved_count,
                CourseMistake.target_key.is_(None),
            )
            .order_by(CourseMistake.last_seen_at.asc(), CourseMistake.id.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def active(
        self,
        user_id: int,
        *,
        category: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CourseMistakeTarget]:
        query = (
            select(CourseMistakeTarget)
            .where(CourseMistakeTarget.user_id == user_id, CourseMistakeTarget.status == "active")
            .order_by(
                CourseMistakeTarget.wrong_count.desc(),
                CourseMistakeTarget.last_seen_at.desc(),
                CourseMistakeTarget.id.desc(),
            )
        )
        if category:
            query = query.where(CourseMistakeTarget.category == category)
        result = await self.session.execute(query.offset(max(0, offset)).limit(max(1, limit)))
        return list(result.scalars().all())

    async def counts(self, user_id: int) -> dict[str, int]:
        result = await self.session.execute(
            select(CourseMistakeTarget.category, func.count(CourseMistakeTarget.id))
            .where(CourseMistakeTarget.user_id == user_id, CourseMistakeTarget.status == "active")
            .group_by(CourseMistakeTarget.category)
        )
        return {str(category): int(count or 0) for category, count in result.all()}

    async def by_ids(self, user_id: int, ids: list[int], *, lock: bool = False) -> dict[int, CourseMistakeTarget]:
        if not ids:
            return {}
        query = select(CourseMistakeTarget).where(
            CourseMistakeTarget.user_id == user_id,
            CourseMistakeTarget.id.in_(ids),
        )
        if lock:
            query = query.with_for_update()
        result = await self.session.execute(query)
        return {int(row.id): row for row in result.scalars().all()}

    async def resolve_rows(self, row: CourseMistakeTarget, now: datetime) -> None:
        """Yopilgan nishonga bog'langan xato qatorlarini `resolved` qiladi."""
        await self.session.execute(
            update(CourseMistake)
            .where(
                CourseMistake.user_id == row.user_id,
                CourseMistake.category == row.category,
                CourseMistake.target_key == row.target_key,
                CourseMistake.wrong_count > CourseMistake.resolved_count,
            )
            .values(
                resolved_count=CourseMistake.wrong_count,
                review_count=CourseMistake.review_count + 1,
                last_reviewed_at=now,
            )
            .execution_options(synchronize_session="fetch")
        )
