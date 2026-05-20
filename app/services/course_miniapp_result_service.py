import json
from html import escape
from typing import Any

from app.bot.utils.course_miniapp import (
    course_miniapp_lesson_id,
    is_course_miniapp_supported,
    normalize_result_items,
)
from app.repositories.course_attempt_repo import CourseAttemptRepository
from app.repositories.course_lesson_repo import CourseLessonRepository
from app.repositories.course_progress_repo import CourseProgressRepository
from app.repositories.user_repo import UserRepository
from app.services.ai_usage_budget_service import AIUsageBudgetService
from app.services.course_tutor_service import CourseTutorService


class CourseMiniAppResultService:
    def __init__(self, session):
        self.session = session
        self.user_repo = UserRepository(session)
        self.lesson_repo = CourseLessonRepository(session)
        self.progress_repo = CourseProgressRepository(session)
        self.attempt_repo = CourseAttemptRepository(session)

    @staticmethod
    def _to_int(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _normalize_homework_answers(value: Any) -> dict:
        if isinstance(value, dict):
            return value

        if not isinstance(value, list):
            return {}

        normalized = {}
        for index, item in enumerate(value, start=1):
            if isinstance(item, dict):
                key = str(item.get("type") or item.get("id") or f"answer_{index}").strip()
                normalized[key or f"answer_{index}"] = item
                continue
            if item is not None:
                normalized[f"answer_{index}"] = str(item)

        return normalized

    async def _resolve_context(self, telegram_id: int, mini_lesson_id: int):
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return None, None, None, "access_start_first"

        progress = await self.progress_repo.get_by_user_id(user.id)
        if not progress or not progress.current_lesson_id:
            return user, progress, None, "course_no_lesson_found"

        lesson = await self.lesson_repo.get_by_id(progress.current_lesson_id)
        if not lesson:
            return user, progress, None, "course_no_lesson_found"

        if not is_course_miniapp_supported(lesson):
            return user, progress, lesson, "course_miniapp_unsupported_lesson"

        if mini_lesson_id and course_miniapp_lesson_id(lesson) != mini_lesson_id:
            return user, progress, lesson, "course_miniapp_lesson_mismatch"

        return user, progress, lesson, ""

    async def save_quiz_result(self, telegram_id: int, payload: dict) -> dict:
        mini_lesson_id = self._to_int(payload.get("lesson_id"))
        user, progress, lesson, error_key = await self._resolve_context(telegram_id, mini_lesson_id)
        if error_key:
            return {"error_key": error_key}

        score = self._to_int(payload.get("score"))
        total = self._to_int(payload.get("total"))
        percent = self._to_int(payload.get("percent"), round((score / total) * 100) if total else 0)
        wrong_items = normalize_result_items(payload.get("wrong_items"))
        passed = percent >= 60

        await self.attempt_repo.create(
            user_id=user.id,
            lesson_id=lesson.id,
            attempt_type="quiz",
            step_name="miniapp_quiz",
            score=percent,
            passed=passed,
            answers_json=json.dumps(
                {
                    "telegram_id": telegram_id,
                    "lesson_id": course_miniapp_lesson_id(lesson),
                    "score": score,
                    "total": total,
                    "percent": percent,
                    "wrong_items": wrong_items,
                    "source": "miniapp",
                },
                ensure_ascii=False,
            ),
            ai_feedback=None,
        )

        await self.progress_repo.set_current_lesson_and_step(
            progress=progress,
            lesson_id=lesson.id,
            step="satisfaction_check",
            waiting_for="satisfaction_answer",
        )
        await self.session.commit()

        return {
            "error_key": None,
            "user": user,
            "lesson": lesson,
            "lesson_id": course_miniapp_lesson_id(lesson),
            "score": score,
            "total": total,
            "percent": percent,
            "wrong_items": wrong_items,
        }

    async def save_homework_result(self, telegram_id: int, payload: dict) -> dict:
        mini_lesson_id = self._to_int(payload.get("lesson_id"))
        user, progress, lesson, error_key = await self._resolve_context(telegram_id, mini_lesson_id)
        if error_key:
            return {"error_key": error_key}

        answers = self._normalize_homework_answers(payload.get("answers"))
        raw_score = payload.get("homework_score", payload.get("score"))
        homework_score = self._to_int(raw_score) if raw_score is not None else None
        feedback = normalize_result_items(payload.get("feedback"))
        status = str(payload.get("status") or "submitted")

        if answers and homework_score is None and not feedback:
            tutor = CourseTutorService()
            evaluation = await tutor.evaluate_homework(
                user_language=user.language if getattr(user, "language", None) else "ru",
                user_level=user.level if getattr(user, "level", None) else "hsk3",
                lesson=lesson,
                submission_text=json.dumps(answers, ensure_ascii=False),
            )
            homework_score = self._to_int(evaluation.get("score"))
            feedback_text = str(evaluation.get("feedback_text") or "").strip()
            if feedback_text:
                feedback = [feedback_text]
            await AIUsageBudgetService(self.session).record_usage(
                telegram_id=telegram_id,
                result=tutor.last_ai_result,
                source="course_miniapp_homework",
            )

        await self.attempt_repo.create(
            user_id=user.id,
            lesson_id=lesson.id,
            attempt_type="homework",
            step_name="miniapp_homework",
            score=homework_score if homework_score is not None else 0,
            passed=True,
            answers_json=json.dumps(
                {
                    "telegram_id": telegram_id,
                    "lesson_id": course_miniapp_lesson_id(lesson),
                    "answers": answers,
                    "homework_score": homework_score,
                    "feedback": feedback,
                    "status": status,
                    "source": "miniapp",
                },
                ensure_ascii=False,
            ),
            ai_feedback="\n".join(feedback) if feedback else None,
        )

        await self.progress_repo.set_homework_status(progress, "completed")
        await self.progress_repo.set_current_lesson_and_step(
            progress=progress,
            lesson_id=lesson.id,
            step="completed",
            waiting_for="none",
        )
        await self.session.commit()

        return {
            "error_key": None,
            "user": user,
            "lesson": lesson,
            "lesson_id": course_miniapp_lesson_id(lesson),
            "answers": answers,
            "homework_score": homework_score,
            "feedback": feedback,
            "status": status,
        }

    def _load_attempt_payload(self, attempt) -> dict:
        if not attempt:
            return {}
        try:
            data = json.loads(getattr(attempt, "answers_json", "") or "{}")
        except (TypeError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    async def build_ai_context(self, user_id: int, lesson_id: int) -> str:
        quiz_attempt = await self.attempt_repo.get_last_attempt(
            user_id=user_id,
            lesson_id=lesson_id,
            attempt_type="quiz",
        )
        homework_attempt = await self.attempt_repo.get_last_attempt(
            user_id=user_id,
            lesson_id=lesson_id,
            attempt_type="homework",
        )

        quiz = self._load_attempt_payload(quiz_attempt)
        homework = self._load_attempt_payload(homework_attempt)
        blocks = []

        if quiz.get("source") == "miniapp":
            wrong_items = normalize_result_items(quiz.get("wrong_items"))
            lines = [
                "MINI APP QUIZ KONTEXTI:",
                f"- lesson_id: {quiz.get('lesson_id')}",
                f"- score: {quiz.get('score')}/{quiz.get('total')} ({quiz.get('percent')}%)",
            ]
            if wrong_items:
                lines.append("- wrong_items:")
                for item in wrong_items[:10]:
                    lines.append(f"  - {escape(str(item))}")
            else:
                lines.append("- wrong_items: none")
            blocks.append("\n".join(lines))

        if homework.get("source") == "miniapp":
            feedback = normalize_result_items(homework.get("feedback"))
            lines = [
                "MINI APP HOMEWORK KONTEXTI:",
                f"- lesson_id: {homework.get('lesson_id')}",
                f"- status: {homework.get('status')}",
                f"- homework_score: {homework.get('homework_score')}",
                f"- answers: {json.dumps(homework.get('answers') or {}, ensure_ascii=False)[:1200]}",
            ]
            if feedback:
                lines.append("- feedback:")
                for item in feedback[:10]:
                    lines.append(f"  - {escape(str(item))}")
            blocks.append("\n".join(lines))

        if not blocks:
            return ""

        return (
            "\n\n".join(blocks)
            + "\n\nAI UCHUN QOIDA: foydalanuvchiga yordam berganda shu Mini App natijalarini "
            "kontekst sifatida ishlat. Ayniqsa wrong_items, homework answers va feedback bo'yicha tushuntir."
        )
