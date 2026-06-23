import hashlib
import json
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select

from app.db.models.course_mistake import COURSE_MISTAKE_CATEGORIES, CourseMistake
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.course_miniapp_access_service import CourseMiniAppAccessService
from app.services.course_miniapp_analytics_service import CourseMiniAppAnalyticsService
from app.services.course_gamification_service import CourseGamificationService


MISTAKE_REVIEW_VERSION = 1


class CourseMistakeService:
    def __init__(self, session):
        self.session = session
        self.user_repo = UserRepository(session)
        self.access = CourseMiniAppAccessService(session)
        self.gamification = CourseGamificationService(session)

    @staticmethod
    def _text(value, limit: int = 2000) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]

    @classmethod
    def _category(cls, item: dict, source: str) -> str:
        explicit = cls._text(item.get("category"), 24).lower()
        if explicit in COURSE_MISTAKE_CATEGORIES:
            return explicit
        if source == "voice":
            return "pronunciation"
        item_type = cls._text(f"{item.get('type') or ''} {item.get('subtype') or ''}", 160).lower()
        if "character" in item_type or "hanzi" in item_type or "pinyin" in item_type:
            return "character"
        if any(token in item_type for token in ("grammar", "order", "sentence", "writing")):
            return "grammar"
        return "word"

    @classmethod
    def _key(cls, category: str, prompt: str, correct_answer: str) -> str:
        normalized = "|".join((category, prompt.casefold(), correct_answer.casefold()))
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def _weakness(item: CourseMistake) -> int:
        return max(0, int(item.wrong_count or 0) - int(item.resolved_count or 0))

    async def record_items(
        self,
        user,
        items: list,
        *,
        source: str,
        level: str | None = None,
        lesson_id: int | None = None,
        lesson_order: int | None = None,
    ) -> int:
        normalized_source = self._text(source, 32).lower() or "lesson"
        normalized = []
        for raw in items if isinstance(items, list) else []:
            if not isinstance(raw, dict):
                continue
            prompt = self._text(raw.get("question") or raw.get("prompt") or raw.get("correction"))
            correct_answer = self._text(raw.get("correct_answer") or raw.get("correct") or raw.get("correction"))
            if not prompt or not correct_answer:
                continue
            category = self._category(raw, normalized_source)
            normalized.append(
                {
                    "mistake_key": self._key(category, prompt, correct_answer),
                    "category": category,
                    "prompt": prompt,
                    "user_answer": self._text(raw.get("selected_answer") or raw.get("user_answer")) or None,
                    "correct_answer": correct_answer,
                    "explanation": self._text(raw.get("explanation")) or None,
                }
            )
        if not normalized:
            return 0

        await self.session.execute(select(User.id).where(User.id == user.id).with_for_update())
        now = datetime.now(timezone.utc)
        recorded = 0
        for data in normalized:
            result = await self.session.execute(
                select(CourseMistake).where(
                    CourseMistake.user_id == user.id,
                    CourseMistake.mistake_key == data["mistake_key"],
                )
            )
            mistake = result.scalar_one_or_none()
            if mistake:
                mistake.wrong_count = int(mistake.wrong_count or 0) + 1
                mistake.user_answer = data["user_answer"]
                mistake.explanation = data["explanation"] or mistake.explanation
                mistake.source = normalized_source
                mistake.level = self._text(level, 32) or mistake.level
                mistake.lesson_id = lesson_id or mistake.lesson_id
                mistake.lesson_order = lesson_order or mistake.lesson_order
                mistake.last_seen_at = now
            else:
                self.session.add(
                    CourseMistake(
                        user_id=user.id,
                        lesson_id=lesson_id,
                        mistake_key=data["mistake_key"],
                        category=data["category"],
                        source=normalized_source,
                        level=self._text(level, 32) or None,
                        lesson_order=lesson_order,
                        prompt=data["prompt"],
                        user_answer=data["user_answer"],
                        correct_answer=data["correct_answer"],
                        explanation=data["explanation"],
                        first_seen_at=now,
                        last_seen_at=now,
                    )
                )
            recorded += 1
        await self.session.flush()
        return recorded

    async def _items(self, user_id: int, limit: int = 50) -> list[CourseMistake]:
        weakness = CourseMistake.wrong_count - CourseMistake.resolved_count
        result = await self.session.execute(
            select(CourseMistake)
            .where(CourseMistake.user_id == user_id, weakness > 0)
            .order_by(weakness.desc(), CourseMistake.last_seen_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def overview(self, telegram_id: int) -> dict:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return {"ok": False, "error": "access_start_first"}
        items = await self._items(user.id)
        counts_result = await self.session.execute(
            select(CourseMistake.category, func.sum(CourseMistake.wrong_count - CourseMistake.resolved_count))
            .where(
                CourseMistake.user_id == user.id,
                CourseMistake.wrong_count > CourseMistake.resolved_count,
            )
            .group_by(CourseMistake.category)
        )
        category_counts = {str(category): int(count or 0) for category, count in counts_result.all()}
        return {
            "ok": True,
            "summary": {
                "total": sum(category_counts.values()),
                "categories": category_counts,
            },
            "items": [
                {
                    "id": item.id,
                    "category": item.category,
                    "source": item.source,
                    "level": item.level,
                    "lesson": item.lesson_order,
                    "question": item.prompt,
                    "correct_answer": item.correct_answer,
                    "explanation": item.explanation,
                    "count": self._weakness(item),
                }
                for item in items
            ],
        }

    @staticmethod
    def _review_question(item: CourseMistake, distractors: list[str]) -> dict:
        options = [item.correct_answer]
        if item.user_answer and item.user_answer != item.correct_answer:
            options.append(item.user_answer)
        options.extend(value for value in distractors if value not in options)
        options = options[:4]
        if len(options) < 2:
            options.append("—")
        if item.id % 2 and len(options) > 1:
            options[0], options[1] = options[1], options[0]
        return {
            "id": f"mistake:{item.id}",
            "category": item.category,
            "prompt": item.prompt,
            "options": options,
            "answer_index": options.index(item.correct_answer),
            "explanation": item.explanation or item.correct_answer,
        }

    async def start_review(self, telegram_id: int) -> dict:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return {"ok": False, "error": "access_start_first"}
        items = await self._items(user.id, limit=10)
        if not items:
            return {"ok": False, "error": "mistake_review_empty"}
        usage_ref = f"mistake-review:v{MISTAKE_REVIEW_VERSION}"
        access = await self.access.consume_free_use(
            user,
            feature_key="training_test",
            usage_ref=usage_ref,
        )
        if not access.get("allowed"):
            return {"ok": False, "error": access.get("error") or "free_feature_limit_reached"}
        distractors = [item.correct_answer for item in items]
        session_id = f"mistake-review:{user.id}:v{MISTAKE_REVIEW_VERSION}:{uuid.uuid4().hex[:12]}"
        questions = [self._review_question(item, distractors) for item in items]
        await CourseMiniAppAnalyticsService(self.session).record_server_event(
            event_name="mistake_review_started",
            telegram_id=telegram_id,
            user_id=user.id,
            session_id=session_id,
            dedupe_key=f"{session_id}:started",
            payload={"question_count": len(questions), "mistake_ids": [item.id for item in items]},
        )
        await self.session.commit()
        return {"ok": True, "session": {"id": session_id, "questions": questions}}

    async def complete_review(self, telegram_id: int, *, session_id: str, answers: list) -> dict:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return {"ok": False, "error": "access_start_first"}
        expected_prefix = f"mistake-review:{user.id}:v{MISTAKE_REVIEW_VERSION}:"
        if not session_id.startswith(expected_prefix) or len(session_id) > 80:
            return {"ok": False, "error": "invalid_mistake_review_session"}
        await self.session.execute(select(User.id).where(User.id == user.id).with_for_update())
        started_result = await self.session.execute(
            select(CourseMiniAppEvent).where(
                CourseMiniAppEvent.user_id == user.id,
                CourseMiniAppEvent.event_name == "mistake_review_started",
                CourseMiniAppEvent.session_id == session_id,
            )
        )
        started = started_result.scalar_one_or_none()
        if not started:
            return {"ok": False, "error": "invalid_mistake_review_session"}
        completed_result = await self.session.execute(
            select(CourseMiniAppEvent.id).where(
                CourseMiniAppEvent.user_id == user.id,
                CourseMiniAppEvent.event_name == "mistake_review_completed",
                CourseMiniAppEvent.session_id == session_id,
            )
        )
        if completed_result.scalar_one_or_none():
            return {"ok": False, "error": "mistake_review_already_completed"}
        try:
            mistake_ids = [int(value) for value in json.loads(started.payload_json or "{}").get("mistake_ids", [])]
        except (TypeError, ValueError, json.JSONDecodeError):
            mistake_ids = []
        if not mistake_ids:
            return {"ok": False, "error": "invalid_mistake_review_session"}
        items_result = await self.session.execute(
            select(CourseMistake)
            .where(CourseMistake.user_id == user.id, CourseMistake.id.in_(mistake_ids))
            .with_for_update()
        )
        by_id = {item.id: item for item in items_result.scalars().all()}
        items = [by_id[item_id] for item_id in mistake_ids if item_id in by_id]
        if len(items) != len(mistake_ids):
            return {"ok": False, "error": "invalid_mistake_review_session"}
        distractors = [item.correct_answer for item in items]
        questions = {question["id"]: question for question in (self._review_question(item, distractors) for item in items)}
        submitted = {
            str(item.get("question_id") or ""): item
            for item in answers if isinstance(item, dict) and item.get("question_id")
        }
        if not questions or set(submitted) != set(questions):
            return {"ok": False, "error": "mistake_review_answers_incomplete"}

        now = datetime.now(timezone.utc)
        score = 0
        for item in items:
            question = questions[f"mistake:{item.id}"]
            try:
                selected = int(submitted[question["id"]].get("selected_index"))
            except (TypeError, ValueError):
                return {"ok": False, "error": "mistake_review_answer_invalid"}
            correct = selected == int(question["answer_index"])
            score += int(correct)
            item.review_count = int(item.review_count or 0) + 1
            if correct:
                item.resolved_count = min(int(item.wrong_count or 0), int(item.resolved_count or 0) + 1)
            item.last_reviewed_at = now

        total = len(items)
        percent = round((score / total) * 100) if total else 0
        remaining = sum(self._weakness(item) for item in items)
        reward = await self.gamification.award(
            user,
            activity_type="mistake_review",
            activity_ref=f"{session_id}:xp",
            base_xp=5,
            level=getattr(user, "level", None),
        )
        await CourseMiniAppAnalyticsService(self.session).record_server_event(
            event_name="mistake_review_completed",
            telegram_id=telegram_id,
            user_id=user.id,
            session_id=session_id,
            dedupe_key=f"{session_id}:completed",
            payload={
                "score": score,
                "total": total,
                "percent": percent,
                "remaining": remaining,
            },
        )
        await self.session.commit()
        return {
            "ok": True,
            "score": score,
            "total": total,
            "percent": percent,
            "remaining": remaining,
            "reward": reward,
        }
