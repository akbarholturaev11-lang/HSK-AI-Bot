from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.bot.utils.course_miniapp import normalize_miniapp_lang
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.user import User
from app.repositories.course_lesson_repo import CourseLessonRepository
from app.repositories.course_progress_repo import CourseProgressRepository
from app.services.course_gamification_service import CourseGamificationService
from app.services.course_lesson_mistake_material_service import (
    CourseLessonMistakeMaterialError,
    CourseLessonMistakeMaterialService,
)
from app.services.course_miniapp_access_service import (
    FREE_COURSE_LESSONS_PER_LEVEL,
    CourseMiniAppAccessService,
)
from app.services.course_miniapp_analytics_service import (
    CourseMiniAppAnalyticsService,
)
from app.services.course_miniapp_profile_service import CourseMiniAppProfileService
from app.services.course_mistake_service import CourseMistakeService
from app.services.course_v3_parts import total_parts
from app.services.desktop_auth_service import DesktopAuthService
from app.services.support_contact_service import get_admin_contact_url


COURSE_V3_LEVELS = frozenset({"hsk1", "hsk2", "hsk3", "hsk4"})
COURSE_V3_LANGUAGES = frozenset({"uz", "ru", "tj"})
COURSE_V3_NEXT_BAND = {"hsk1": "hsk2", "hsk2": "hsk3", "hsk3": "hsk4"}
COURSE_V3_DATA_ROOT = Path(__file__).resolve().parents[1] / "static" / "course_v3_data"
DESKTOP_PREVIEW_COMPLETION_ERROR = "free_feature_limit_reached"


class DesktopCourseError(RuntimeError):
    def __init__(self, code: str, *, status_code: int):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


def normalize_course_v3_level(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in COURSE_V3_LEVELS else "hsk1"


def course_v3_lesson_card_count(lesson: dict[str, Any]) -> int:
    """Count the cards the desktop renderer can step through."""

    total = 0
    sections = lesson.get("sections")
    if not isinstance(sections, list):
        return 0
    for section in sections:
        if not isinstance(section, dict):
            continue
        cards = section.get("cards")
        if isinstance(cards, list):
            total += sum(isinstance(card, dict) for card in cards)
    return total


def apply_course_v3_access_policy(
    data: dict[str, Any],
    *,
    level: str,
    completed: int,
    is_paid: bool,
) -> None:
    """Apply the same server-owned progress and premium rules as Course v3."""

    for unit in data.get("units", []):
        if not isinstance(unit, dict):
            continue
        unit_unlocked = False
        for lesson in unit.get("lessons", []):
            if not isinstance(lesson, dict):
                continue
            try:
                lesson_order = int(lesson.get("n") or 0)
            except (TypeError, ValueError):
                lesson_order = 0

            if lesson_order <= completed:
                lesson["status"] = "done"
                lesson.setdefault("stars", 2)
            elif lesson_order == completed + 1:
                lesson["status"] = "current"
                lesson.pop("stars", None)
            else:
                lesson["status"] = "locked"
                lesson.pop("stars", None)

            requires_premium = CourseMiniAppAccessService.lesson_requires_premium(
                level,
                lesson_order,
            )
            if not is_paid and requires_premium and lesson_order > completed:
                if (
                    lesson_order == completed + 1
                    and lesson_order == FREE_COURSE_LESSONS_PER_LEVEL + 1
                ):
                    lesson["status"] = "current"
                    lesson["preview_half"] = True
                    lesson["completion_allowed"] = False
                    lesson["completion_error"] = DESKTOP_PREVIEW_COMPLETION_ERROR
                    lesson.pop("locked_premium", None)
                else:
                    lesson["status"] = "locked"
                    lesson["locked_premium"] = True
                    lesson["completion_allowed"] = False
                    lesson["completion_error"] = DESKTOP_PREVIEW_COMPLETION_ERROR
                    lesson.pop("preview_half", None)
            else:
                lesson.pop("locked_premium", None)
                lesson.pop("preview_half", None)
                if lesson.get("status") in {"done", "current"}:
                    lesson["completion_allowed"] = True
                    lesson.pop("completion_error", None)
                else:
                    lesson["completion_allowed"] = False
                    lesson["completion_error"] = "course_lesson_not_unlocked"

            if (
                lesson.get("status") in {"done", "current"}
                and not lesson.get("locked_premium")
            ):
                unit_unlocked = True

        if unit_unlocked:
            unit.pop("status", None)
        else:
            unit["status"] = "locked"


class DesktopCourseService:
    """Bearer-authenticated Course v3 adapter for the native desktop client."""

    # Analytics and dedupe namespace for this native client. Android subclasses
    # it (see AndroidCourseService) so an Android completion never shares a
    # dedupe key with a desktop one and never lands in the desktop funnel.
    # Every other rule — access policy, XP, mistakes, idempotency — is shared.
    CLIENT_NAMESPACE = "desktop"

    def __init__(self, session, settings_obj):
        self.session = session
        self.settings = settings_obj

    async def _context(self, access_token: str):
        # `authenticate` validates token/session/device/user without bootstrap's
        # first-open or app-open analytics side effects.
        return await DesktopAuthService(
            self.session,
            self.settings,
        ).authenticate(access_token)

    async def _locked_context_user(self, context):
        result = await self.session.execute(
            select(User).where(User.id == context.user.id).with_for_update()
        )
        user = result.scalar_one_or_none()
        if not user:
            raise DesktopCourseError(
                "desktop_course_user_not_found",
                status_code=401,
            )
        return user

    @staticmethod
    def _level(user) -> str:
        return normalize_course_v3_level(getattr(user, "level", None))

    @staticmethod
    def _language(user) -> str:
        return normalize_miniapp_lang(getattr(user, "language", None))

    @staticmethod
    def _display_name(user) -> str:
        return str(
            getattr(user, "full_name", None)
            or getattr(user, "username", None)
            or "HSK Student"
        ).strip()[:60]

    @staticmethod
    def _initials(display_name: str) -> str:
        return (
            "".join(part[:1].upper() for part in display_name.split()[:2]) or "阿"
        )[:2]

    @staticmethod
    def _read_json(path: Path, *, error_code: str) -> dict[str, Any]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError) as exc:
            raise DesktopCourseError(error_code, status_code=500) from exc
        if not isinstance(payload, dict):
            raise DesktopCourseError(error_code, status_code=500)
        return payload

    async def _progress(self, user, *, for_update: bool):
        level = self._level(user)
        repository = CourseProgressRepository(self.session)
        progress = await repository.get_by_user_id(
            user.id,
            for_update=for_update,
        )
        if not progress:
            progress = await repository.create(
                user_id=user.id,
                level=level,
                current_lesson_id=None,
                current_step="intro",
                waiting_for="none",
            )
        elif normalize_course_v3_level(progress.level) != level:
            progress.level = level
            progress.completed_lessons_count = 0
            progress.current_lesson_id = None
            progress.current_step = "intro"
            progress.waiting_for = "none"
            progress.homework_status = "none"
        elif progress.level != level:
            progress.level = level
        return progress

    @staticmethod
    def _completion_payload(
        *,
        lesson_order: int,
        next_lesson: int | None,
        completed_lessons_count: int,
        gamification: dict[str, Any],
        duplicate: bool = False,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "ok": True,
            "completed_lesson": lesson_order,
            "next_lesson": next_lesson,
            "completed_lessons_count": completed_lessons_count,
            "gamification": gamification,
        }
        if duplicate:
            payload["duplicate"] = True
        return payload

    async def course_map(
        self,
        access_token: str,
        *,
        timezone_offset_minutes: int | None = None,
    ) -> dict[str, Any]:
        context = await self._context(access_token)
        user = context.user
        level = self._level(user)
        language = self._language(user)
        progress = await self._progress(user, for_update=True)
        profile = await CourseMiniAppProfileService(self.session).get_or_create(
            user.id
        )
        if timezone_offset_minutes is not None:
            profile.timezone_offset_minutes = max(
                -720,
                min(840, int(timezone_offset_minutes)),
            )
            progress.reminder_tz_offset = round(
                profile.timezone_offset_minutes / 60
            )

        gamification = await CourseGamificationService(self.session).snapshot(
            user,
            profile=profile,
        )
        is_paid = CourseMiniAppAccessService.is_paid_user(user)
        data = self._read_json(
            COURSE_V3_DATA_ROOT / f"{level}.json",
            error_code="course_map_load_failed",
        )
        completed = int(progress.completed_lessons_count or 0)
        display_name = self._display_name(user)

        data["ok"] = True
        data["authenticated"] = True
        data["bot_username"] = (
            str(getattr(self.settings, "BOT_USERNAME", "") or "darsi_chini_bot")
            .strip()
            .lstrip("@")
            or "darsi_chini_bot"
        )
        data["level"] = level
        data["progress"] = {
            "xp": gamification["xp"],
            "streak": gamification["streak"],
            "longest_streak": gamification.get("longest_streak", 0),
            "weekly_xp": gamification["weekly_xp"],
            "league": gamification["league"],
            "completed": completed,
            "daily_xp": gamification.get("daily_xp", 0),
            "last_activity_date": gamification.get("last_activity_date"),
            "local_date": gamification.get("local_date"),
            "week_start": gamification.get("week_start"),
            "week_activity_dates": gamification.get("week_activity_dates", []),
            "reward_chest": gamification.get("reward_chest"),
        }
        data["user"] = {
            "name": display_name,
            "avatar": self._initials(display_name),
            "language": language,
            "is_paid": is_paid,
            "referral_code": getattr(user, "referral_code", None) or "",
        }
        data["notify"] = {
            "enabled": bool(getattr(profile, "notifications_enabled", True))
        }
        data["admin_contact"] = await get_admin_contact_url(self.session)
        apply_course_v3_access_policy(
            data,
            level=level,
            completed=completed,
            is_paid=is_paid,
        )
        await self.session.commit()
        return data

    async def lesson(
        self,
        access_token: str,
        *,
        lesson_order: int,
    ) -> dict[str, Any]:
        context = await self._context(access_token)
        user = context.user
        level = self._level(user)
        lesson_order = int(lesson_order)
        total = total_parts(level)
        if lesson_order <= 0:
            raise DesktopCourseError(
                "invalid_lesson_order",
                status_code=422,
            )
        if not total or lesson_order > total:
            raise DesktopCourseError(
                "course_no_lesson_found",
                status_code=404,
            )

        progress = await self._progress(user, for_update=True)
        completed = int(progress.completed_lessons_count or 0)
        if lesson_order > completed + 1:
            raise DesktopCourseError(
                "course_lesson_not_unlocked",
                status_code=403,
            )
        is_paid = CourseMiniAppAccessService.is_paid_user(user)
        requires_premium = CourseMiniAppAccessService.lesson_requires_premium(
            level,
            lesson_order,
        )
        preview_half = (
            not is_paid
            and requires_premium
            and lesson_order == completed + 1
            and lesson_order == FREE_COURSE_LESSONS_PER_LEVEL + 1
        )
        if lesson_order > completed and not is_paid and requires_premium and not preview_half:
            raise DesktopCourseError(
                "free_feature_limit_reached",
                status_code=403,
            )

        lesson = self._read_json(
            COURSE_V3_DATA_ROOT
            / level
            / f"lesson_{lesson_order:02d}.json",
            error_code="course_lesson_load_failed",
        )
        if (
            normalize_course_v3_level(lesson.get("level")) != level
            or int(lesson.get("lesson_id") or 0) != lesson_order
        ):
            raise DesktopCourseError(
                "course_lesson_load_failed",
                status_code=500,
            )
        total_cards = course_v3_lesson_card_count(lesson)
        if total_cards <= 0:
            raise DesktopCourseError(
                "course_lesson_load_failed",
                status_code=500,
            )
        preview_card_limit = (
            max(1, total_cards // 2) if preview_half else total_cards
        )
        await self.session.commit()
        return {
            "ok": True,
            "level": level,
            "lesson_order": lesson_order,
            "preview_half": preview_half,
            "preview_card_limit": preview_card_limit,
            "total_cards": total_cards,
            "completion_allowed": not preview_half,
            "completion_error": (
                DESKTOP_PREVIEW_COMPLETION_ERROR if preview_half else None
            ),
            "lesson": lesson,
        }

    async def complete(
        self,
        access_token: str,
        *,
        lesson_order: int,
        event_id: str,
        mistakes: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        context = await self._context(access_token)
        user = await self._locked_context_user(context)
        lesson_order = int(lesson_order)
        event_id = str(event_id or "").strip()
        event_dedupe_key = f"{self.CLIENT_NAMESPACE}-course-complete:{event_id}"
        level = self._level(user)

        existing_result = await self.session.execute(
            select(CourseMiniAppEvent).where(
                CourseMiniAppEvent.telegram_id == int(user.telegram_id),
                CourseMiniAppEvent.event_name == "lesson_completed",
                CourseMiniAppEvent.dedupe_key == event_dedupe_key,
            )
        )
        existing_event = existing_result.scalar_one_or_none()
        if existing_event:
            if (
                int(existing_event.lesson_order or 0) != lesson_order
                or str(existing_event.level or "").strip().lower() != level
            ):
                raise DesktopCourseError(
                    "desktop_course_event_conflict",
                    status_code=409,
                )
            try:
                stored = json.loads(existing_event.payload_json or "{}")
            except (TypeError, ValueError):
                stored = {}
            stored_result = stored.get("result") if isinstance(stored, dict) else None
            if isinstance(stored_result, dict) and stored_result.get("ok") is True:
                return {**stored_result, "duplicate": True}
            raise DesktopCourseError(
                "desktop_course_event_conflict",
                status_code=409,
            )

        total = total_parts(level)
        if lesson_order <= 0:
            raise DesktopCourseError(
                "invalid_lesson_order",
                status_code=422,
            )
        if not total or lesson_order > total:
            raise DesktopCourseError(
                "course_no_lesson_found",
                status_code=404,
            )

        lesson_repository = CourseLessonRepository(self.session)
        legacy_lesson = await lesson_repository.get_by_level_and_order(
            level,
            lesson_order,
        )
        access = CourseMiniAppAccessService(self.session)
        is_paid = access.is_paid_user(user)

        progress_repository = CourseProgressRepository(self.session)
        progress = await self._progress(user, for_update=True)
        completed = int(progress.completed_lessons_count or 0)
        gamification_service = CourseGamificationService(self.session)
        if lesson_order <= completed:
            snapshot = await gamification_service.snapshot(user)
            await self.session.commit()
            return self._completion_payload(
                lesson_order=lesson_order,
                next_lesson=lesson_order + 1 if lesson_order < total else None,
                completed_lessons_count=completed,
                gamification=snapshot,
                duplicate=True,
            )
        if not is_paid and access.lesson_requires_premium(level, lesson_order):
            raise DesktopCourseError(
                DESKTOP_PREVIEW_COMPLETION_ERROR,
                status_code=403,
            )
        if lesson_order != completed + 1:
            raise DesktopCourseError(
                "course_lesson_not_unlocked",
                status_code=403,
            )

        legacy_lesson_id = getattr(legacy_lesson, "id", None)
        await progress_repository.set_current_lesson_and_step(
            progress=progress,
            lesson_id=legacy_lesson_id,
            step="intro",
            waiting_for="none",
        )
        await progress_repository.mark_lesson_completed(progress)
        snapshot = await gamification_service.award(
            user,
            activity_type="lesson",
            activity_ref=f"v3-part:{level}:{lesson_order}:complete",
            base_xp=20,
            level=level,
        )

        has_next = lesson_order < total
        next_lesson = lesson_order + 1 if has_next else None
        if not has_next:
            next_band = COURSE_V3_NEXT_BAND.get(level)
            if next_band:
                user.level = next_band

        next_requires_premium = access.lesson_requires_premium(
            level,
            next_lesson,
        )
        if has_next and (is_paid or not next_requires_premium):
            await progress_repository.set_current_lesson_and_step(
                progress=progress,
                lesson_id=legacy_lesson_id,
                step="intro",
                waiting_for="none",
            )
            await progress_repository.set_homework_status(progress, "none")
        else:
            await progress_repository.set_current_lesson_and_step(
                progress=progress,
                lesson_id=legacy_lesson_id,
                step="completed",
                waiting_for="none",
            )

        completion_result = self._completion_payload(
            lesson_order=lesson_order,
            next_lesson=next_lesson,
            completed_lessons_count=int(progress.completed_lessons_count or 0),
            gamification=snapshot,
        )
        analytics_result = await CourseMiniAppAnalyticsService(
            self.session
        ).record_server_event(
            event_name="lesson_completed",
            telegram_id=user.telegram_id,
            user_id=user.id,
            source=f"{self.CLIENT_NAMESPACE}_course",
            level=level,
            lesson_id=legacy_lesson_id,
            lesson_order=lesson_order,
            session_id=event_id,
            dedupe_key=event_dedupe_key,
            payload={
                "lesson_order": lesson_order,
                "is_paid": is_paid,
                "next_lesson": next_lesson,
                "device_id": context.device.id,
                "result": completion_result,
            },
        )
        if not analytics_result.get("ok"):
            raise DesktopCourseError(
                "desktop_course_save_failed",
                status_code=503,
            )

        canonical_mistakes = mistakes or []
        if canonical_mistakes:
            try:
                canonical_mistakes = (
                    CourseLessonMistakeMaterialService.canonicalize_items(
                        level=level,
                        lesson_order=lesson_order,
                        lang=self._language(user),
                        items=canonical_mistakes,
                    )
                )
            except CourseLessonMistakeMaterialError:
                canonical_mistakes = []
        if canonical_mistakes:
            await CourseMistakeService(self.session).record_items(
                user,
                canonical_mistakes,
                source="lesson",
                level=level,
                lesson_id=legacy_lesson_id,
                lesson_order=lesson_order,
            )

        await self.session.commit()

        persisted_progress = await CourseProgressRepository(
            self.session
        ).get_by_user_id(user.id)
        persisted_event = (
            await self.session.execute(
                select(CourseMiniAppEvent.id).where(
                    CourseMiniAppEvent.telegram_id == int(user.telegram_id),
                    CourseMiniAppEvent.event_name == "lesson_completed",
                    CourseMiniAppEvent.dedupe_key == event_dedupe_key,
                )
            )
        ).scalar_one_or_none()
        if (
            not analytics_result.get("ok")
            or not persisted_event
            or not persisted_progress
            or int(persisted_progress.completed_lessons_count or 0)
            < lesson_order
        ):
            raise DesktopCourseError(
                "desktop_course_save_failed",
                status_code=503,
            )
        return completion_result

    async def set_language(
        self,
        access_token: str,
        *,
        language: str,
    ) -> dict[str, Any]:
        context = await self._context(access_token)
        user = await self._locked_context_user(context)
        language = str(language or "").strip().lower()
        if language not in COURSE_V3_LANGUAGES:
            raise DesktopCourseError(
                "invalid_language",
                status_code=422,
            )
        user.language = language
        await self.session.commit()
        return {"ok": True, "language": language}

    async def record_native_event(
        self,
        access_token: str,
        *,
        event_name: str,
        event_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        context = await self._context(access_token)
        user = context.user
        allowed = {
            "desktop_ai_pack_started",
            "desktop_ai_pack_completed",
            "desktop_offline_ai_used",
        }
        if event_name not in allowed:
            raise DesktopCourseError(
                "desktop_course_event_invalid",
                status_code=422,
            )
        event_id = str(event_id or "").strip()
        if not 16 <= len(event_id) <= 80:
            raise DesktopCourseError(
                "desktop_course_event_invalid",
                status_code=422,
            )
        result = await CourseMiniAppAnalyticsService(
            self.session
        ).record_server_event(
            event_name=event_name,
            telegram_id=user.telegram_id,
            user_id=user.id,
            source="desktop_native",
            level=self._level(user),
            session_id=event_id,
            dedupe_key=f"desktop-native:{event_id}",
            payload={
                "device_id": context.device.id,
                **dict(payload or {}),
            },
        )
        if not result.get("ok"):
            raise DesktopCourseError(
                "desktop_course_save_failed",
                status_code=503,
            )
        await self.session.commit()
        return {
            "ok": True,
            "recorded": bool(result.get("recorded")),
            "duplicate": bool(result.get("duplicate")),
        }
