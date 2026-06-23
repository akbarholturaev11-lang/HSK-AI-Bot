import json

from sqlalchemy import select

from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.repositories.course_lesson_repo import CourseLessonRepository
from app.repositories.user_repo import UserRepository
from app.services.course_miniapp_access_service import CourseMiniAppAccessService
from app.services.course_miniapp_analytics_service import CourseMiniAppAnalyticsService
from app.services.course_miniapp_lesson_service import CourseMiniAppLessonService
from app.services.course_mistake_service import CourseMistakeService
from app.services.course_gamification_service import CourseGamificationService


PRACTICE_VERSION = 1
PRACTICE_MODES = {"placement", "mock", "training"}
TRAINING_SKILLS = {"listening", "writing", "characters"}


class CourseMiniAppPracticeService:
    def __init__(self, session):
        self.session = session
        self.user_repo = UserRepository(session)
        self.lesson_repo = CourseLessonRepository(session)
        self.lesson_service = CourseMiniAppLessonService(session)
        self.access = CourseMiniAppAccessService(session)
        self.mistakes = CourseMistakeService(session)
        self.gamification = CourseGamificationService(session)

    @staticmethod
    def _level(value: str) -> str:
        level = str(value or "hsk1").strip().lower()
        if level in {"hsk4a", "hsk4b"}:
            return "hsk4"
        if level not in {"hsk1", "hsk2", "hsk3", "hsk4"}:
            raise ValueError("Unknown HSK level")
        return level

    @staticmethod
    def _feature(mode: str) -> str:
        return "placement" if mode == "placement" else "training_test"

    async def _is_completed(self, telegram_id: int, feature: str) -> bool:
        result = await self.session.execute(
            select(CourseMiniAppEvent.id)
            .where(
                CourseMiniAppEvent.telegram_id == telegram_id,
                CourseMiniAppEvent.event_name.in_(("test_completed", "training_completed")),
                CourseMiniAppEvent.dedupe_key == f"practice:{feature}:completed",
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    def _choice_question(question: dict, *, level: str, lesson_order: int, index: int) -> dict | None:
        options = question.get("opts") or question.get("options")
        try:
            answer_index = int(question.get("ans"))
        except (TypeError, ValueError):
            return None
        if not isinstance(options, list) or len(options) < 2 or not 0 <= answer_index < len(options):
            return None
        return {
            "id": f"{level}:{lesson_order}:{index}",
            "level": level,
            "lesson": lesson_order,
            "type": str(question.get("type") or "multiple_choice"),
            "subtype": str(question.get("subtype") or ""),
            "prompt": str(question.get("q") or question.get("prompt") or ""),
            "sentence": str(question.get("sentence") or question.get("source") or ""),
            "audio_text": str(question.get("audioText") or ""),
            "options": [str(option) for option in options],
            "answer_index": answer_index,
            "explanation": str(question.get("expl") or question.get("explanation") or ""),
        }

    @staticmethod
    def _skill_match(question: dict, skill: str) -> bool:
        question_type = str(question.get("type") or "")
        subtype = str(question.get("subtype") or "")
        if skill == "listening":
            return bool(question.get("audio_text")) or question_type in {"listening_choice", "listen_and_fill"}
        if skill == "writing":
            return question_type in {
                "fill_blank",
                "fill_blank_choice",
                "tap_missing_word",
                "grammar_in_context",
                "grammar_example_to_pattern",
                "grammar_pattern_to_example",
            }
        if skill == "characters":
            return subtype in {"meaning_to_hanzi", "pinyin_to_hanzi", "hanzi_to_meaning"}
        return True

    async def _level_questions(self, level: str, lang: str, limit: int, skill: str = "") -> list[dict]:
        lessons = await self.lesson_repo.list_by_level(level)
        pool = []
        for lesson in lessons:
            payload = await self.lesson_service.get_payload(
                lesson_order=int(lesson.lesson_order),
                lang=lang,
                level=level,
            )
            for index, item in enumerate((payload or {}).get("quiz_questions", []), 1):
                normalized = self._choice_question(
                    item,
                    level=level,
                    lesson_order=int(lesson.lesson_order),
                    index=index,
                )
                if normalized:
                    pool.append(normalized)
            if len(pool) >= max(limit * 3, limit):
                break
        filtered = [item for item in pool if not skill or self._skill_match(item, skill)]
        if len(filtered) < limit:
            filtered.extend(item for item in pool if item not in filtered)
        if not filtered:
            return []
        step = max(1, len(filtered) // limit)
        selected = filtered[::step][:limit]
        return selected

    async def _questions(self, mode: str, level: str, lang: str, skill: str) -> list[dict]:
        if mode == "placement":
            questions = []
            for item_level, count in (("hsk1", 3), ("hsk2", 3), ("hsk3", 2), ("hsk4", 2)):
                questions.extend(await self._level_questions(item_level, lang, count))
            return questions
        return await self._level_questions(level, lang, 10, skill if mode == "training" else "")

    async def start(
        self,
        telegram_id: int,
        *,
        mode: str,
        level: str,
        lang: str,
        skill: str = "",
    ) -> dict:
        mode = str(mode or "").strip().lower()
        skill = str(skill or "").strip().lower()
        if mode not in PRACTICE_MODES:
            raise ValueError("Unknown practice mode")
        if mode == "training" and skill not in TRAINING_SKILLS:
            raise ValueError("Unknown training skill")
        level = self._level(level)

        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return {"ok": False, "error": "access_start_first"}
        feature = self._feature(mode)
        if not self.access.is_paid_user(user) and await self._is_completed(telegram_id, feature):
            return {"ok": False, "error": "free_feature_limit_reached"}
        session_scope = skill or level
        usage_ref = f"practice:{feature}:{mode}:{session_scope}:v{PRACTICE_VERSION}"
        access = await self.access.consume_free_use(
            user,
            feature_key=feature,
            usage_ref=usage_ref,
        )
        if not access.get("allowed"):
            return {"ok": False, "error": access.get("error") or "free_feature_limit_reached"}

        questions = await self._questions(mode, level, lang, skill)
        if not questions:
            return {"ok": False, "error": "practice_questions_not_found"}
        session_id = f"practice:{user.id}:{feature}:{mode}:{session_scope}:v{PRACTICE_VERSION}"
        event_name = "training_started" if mode == "training" else "test_started"
        await CourseMiniAppAnalyticsService(self.session).record_server_event(
            event_name=event_name,
            telegram_id=telegram_id,
            user_id=user.id,
            level=level,
            session_id=session_id,
            dedupe_key=f"{session_id}:started",
            payload={"mode": mode, "skill": skill, "question_count": len(questions)},
        )
        await self.session.commit()
        return {
            "ok": True,
            "session": {
                "id": session_id,
                "mode": mode,
                "skill": skill,
                "level": level,
                "questions": questions,
            },
        }

    async def complete(
        self,
        telegram_id: int,
        *,
        session_id: str,
        mode: str,
        level: str,
        lang: str,
        skill: str,
        answers: list,
    ) -> dict:
        mode = str(mode or "").strip().lower()
        skill = str(skill or "").strip().lower()
        if mode not in PRACTICE_MODES:
            raise ValueError("Unknown practice mode")
        if mode == "training" and skill not in TRAINING_SKILLS:
            raise ValueError("Unknown training skill")
        level = self._level(level)
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return {"ok": False, "error": "access_start_first"}
        feature = self._feature(mode)
        session_scope = skill or level
        expected_session = f"practice:{user.id}:{feature}:{mode}:{session_scope}:v{PRACTICE_VERSION}"
        if str(session_id or "") != expected_session:
            return {"ok": False, "error": "invalid_practice_session"}
        access = await self.access.consume_free_use(
            user,
            feature_key=feature,
            usage_ref=f"practice:{feature}:{mode}:{session_scope}:v{PRACTICE_VERSION}",
        )
        if not access.get("allowed"):
            return {"ok": False, "error": access.get("error") or "free_feature_limit_reached"}

        questions = await self._questions(mode, level, lang, skill)
        submitted = {
            str(item.get("question_id") or ""): item
            for item in answers if isinstance(item, dict) and item.get("question_id")
        }
        if set(submitted) != {item["id"] for item in questions}:
            return {"ok": False, "error": "practice_answers_incomplete"}
        score = 0
        wrong = []
        by_level = {}
        for question in questions:
            selected = submitted[question["id"]].get("selected_index")
            try:
                selected = int(selected)
            except (TypeError, ValueError):
                return {"ok": False, "error": "practice_answer_invalid"}
            correct = selected == int(question["answer_index"])
            score += int(correct)
            level_score = by_level.setdefault(question["level"], {"score": 0, "total": 0})
            level_score["score"] += int(correct)
            level_score["total"] += 1
            if not correct:
                wrong.append(
                    {
                        "question_id": question["id"],
                        "question": question["prompt"],
                        "selected_answer": question["options"][selected] if 0 <= selected < len(question["options"]) else "",
                        "correct_answer": question["options"][question["answer_index"]],
                        "explanation": question["explanation"],
                        "level": question["level"],
                        "type": question["type"],
                        "subtype": question["subtype"],
                        "category": (
                            "grammar"
                            if mode == "training" and skill == "writing"
                            else "character"
                            if mode == "training" and skill == "characters"
                            else "word"
                        ),
                    }
                )
        total = len(questions)
        percent = round((score / total) * 100) if total else 0
        recommendation = level.upper()
        if mode == "placement":
            recommendation = "HSK 1"
            for item_level in ("hsk1", "hsk2", "hsk3", "hsk4"):
                item = by_level.get(item_level, {})
                item_percent = round((item.get("score", 0) / item.get("total", 1)) * 100)
                if item_percent >= 60:
                    recommendation = item_level.upper().replace("HSK", "HSK ")

        event_name = "training_completed" if mode == "training" else "test_completed"
        await self.mistakes.record_items(
            user,
            wrong,
            source="training" if mode == "training" else "test",
            level=level,
        )
        analytics = CourseMiniAppAnalyticsService(self.session)
        await analytics.record_server_event(
            event_name=event_name,
            telegram_id=telegram_id,
            user_id=user.id,
            level=level,
            session_id=expected_session,
            dedupe_key=f"practice:{feature}:completed",
            payload={
                "mode": mode,
                "skill": skill,
                "score": score,
                "total": total,
                "percent": percent,
                "recommendation": recommendation,
                "wrong": json.dumps(wrong, ensure_ascii=False)[:4000],
            },
        )
        reward = await self.gamification.award(
            user,
            activity_type="training" if mode == "training" else "test",
            activity_ref=f"{expected_session}:completed",
            base_xp=12 if mode == "training" else 15,
            level=level,
        )
        await self.session.commit()
        return {
            "ok": True,
            "score": score,
            "total": total,
            "percent": percent,
            "recommendation": recommendation,
            "wrong_items": wrong,
            "reward": reward,
        }
