import json
from typing import Any

from app.bot.utils.course_miniapp import (
    course_miniapp_lesson_id,
    is_course_miniapp_supported,
    normalize_result_items,
)
from app.repositories.course_attempt_repo import CourseAttemptRepository
from app.repositories.course_lesson_repo import CourseLessonRepository
from app.repositories.course_pilot_event_repo import CoursePilotEventRepository
from app.repositories.course_progress_repo import CourseProgressRepository
from app.repositories.user_repo import UserRepository
from app.services.course_engine_service import (
    CourseEngineService,
    get_block_no_from_step,
    is_block_quiz_step,
)
from app.services.ai_usage_budget_service import AIUsageBudgetService
from app.services.access_service import AccessService
from app.services.conversion_funnel_service import ConversionFunnelService
from app.services.course_miniapp_lesson_service import CourseMiniAppLessonService
from app.services.course_tutor_service import CourseTutorService
from app.services.course_trial_service import CourseTrialService


class CourseMiniAppResultService:
    def __init__(self, session):
        self.session = session
        self.user_repo = UserRepository(session)
        self.lesson_repo = CourseLessonRepository(session)
        self.progress_repo = CourseProgressRepository(session)
        self.attempt_repo = CourseAttemptRepository(session)
        self.pilot_event_repo = CoursePilotEventRepository(session)

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

    @staticmethod
    def _has_homework_answers(answers: dict) -> bool:
        required_groups = (
            ("vocab_sentences",),
            ("grammar_sentences",),
            ("translations", "translation_exercises"),
        )
        for keys in required_groups:
            value = next((answers.get(key) for key in keys if answers.get(key) is not None), None)
            if isinstance(value, dict):
                value = value.get("answer")
            if not str(value or "").strip():
                return False
        return True

    @staticmethod
    def _normalize_token_list(value: Any) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split() if item.strip()]
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    @staticmethod
    def _normalize_pair_set(value: Any) -> set[tuple[str, str]]:
        if not isinstance(value, list):
            return set()
        pairs = set()
        for item in value:
            if isinstance(item, dict):
                left = str(item.get("left") or "").strip()
                right = str(item.get("right") or "").strip()
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                left = str(item[0] or "").strip()
                right = str(item[1] or "").strip()
            else:
                continue
            if left and right:
                pairs.add((left, right))
        return pairs

    async def _grade_reinforcement(self, user, lesson, payload: dict, answers: dict) -> dict | None:
        submitted = answers.get("reinforcement_results") or answers.get("practice_results")
        if not isinstance(submitted, list) or not submitted:
            return None

        lesson_payload = await CourseMiniAppLessonService(self.session).get_payload(
            lesson_order=course_miniapp_lesson_id(lesson),
            lang=getattr(user, "language", None) or "ru",
            level=getattr(lesson, "level", None) or "hsk1",
            block_no=self._to_int(payload.get("block_no") or payload.get("block")) or None,
        )
        tasks = (lesson_payload or {}).get("reinforcement_tasks")
        if not isinstance(tasks, list) or not tasks:
            return None

        submitted_by_id = {}
        for item in submitted:
            if not isinstance(item, dict):
                return None
            task_id = str(item.get("task_id") or item.get("id") or "").strip()
            if not task_id or task_id in submitted_by_id:
                return None
            submitted_by_id[task_id] = item

        task_ids = {str(task.get("id") or "") for task in tasks}
        if set(submitted_by_id) != task_ids:
            return None

        score = 0
        normalized_results = []
        feedback = []
        for task in tasks:
            task_id = str(task.get("id") or "")
            task_type = str(task.get("type") or "")
            submitted_item = submitted_by_id[task_id]
            correct = False

            if task_type in {"multiple_choice", "listening_choice", "fill_blank"}:
                options = task.get("options") or task.get("opts") or []
                answer = str(task.get("answer") or "")
                selected_answer = str(submitted_item.get("selected_answer") or "").strip()
                selected_index = self._to_int(submitted_item.get("selected_index"), -1)
                if not selected_answer and isinstance(options, list) and 0 <= selected_index < len(options):
                    selected_answer = str(options[selected_index])
                correct = bool(answer and selected_answer == answer)
                normalized_answer = selected_answer
            elif task_type in {"word_order", "build_chinese_sentence", "build_sentence_chips"}:
                expected = self._normalize_token_list(task.get("answer"))
                actual = self._normalize_token_list(
                    submitted_item.get("answer_tokens") or submitted_item.get("tokens")
                )
                correct = bool(expected and actual == expected)
                normalized_answer = actual
            elif task_type == "match_pairs":
                expected_pairs = self._normalize_pair_set(task.get("pairs"))
                actual_pairs = self._normalize_pair_set(submitted_item.get("pairs"))
                correct = bool(expected_pairs and actual_pairs == expected_pairs)
                normalized_answer = sorted(actual_pairs)
            elif task_type == "stroke_preview":
                correct = bool(submitted_item.get("completed") or submitted_item.get("seen"))
                normalized_answer = "seen" if correct else ""
            else:
                return None

            if correct:
                score += 1
            else:
                feedback.append(
                    {
                        "question": str(task.get("prompt") or task_type),
                        "correct_answer": task.get("answer") or task.get("explanation") or "",
                        "explanation": str(task.get("explanation") or ""),
                    }
                )

            normalized_results.append(
                {
                    "task_id": task_id,
                    "type": task_type,
                    "correct": correct,
                    "answer": normalized_answer,
                }
            )

        total = len(tasks)
        percent = round((score / total) * 100) if total else 0
        return {
            "results": normalized_results,
            "score": score,
            "total": total,
            "percent": percent,
            "passed": total > 0,
            "feedback": normalize_result_items(feedback),
        }

    def _validate_quiz_state(self, progress, block_no: int) -> bool:
        current_step = str(getattr(progress, "current_step", "") or "")
        if getattr(progress, "waiting_for", "none") != "quiz_result":
            return False

        if is_block_quiz_step(current_step):
            expected_block_no = get_block_no_from_step(current_step)
            return bool(expected_block_no and block_no == expected_block_no)

        return current_step == "exercise" and block_no == 0

    async def _record_pilot_event(
        self,
        *,
        user,
        lesson,
        event_type: str,
        step_name: str,
        mode: str,
        block_no: int | None = None,
        payload: dict | None = None,
    ) -> None:
        await self.pilot_event_repo.record(
            telegram_id=user.telegram_id,
            user_id=user.id,
            lesson_id=lesson.id,
            level=getattr(lesson, "level", None) or getattr(user, "level", "hsk1"),
            lesson_order=course_miniapp_lesson_id(lesson),
            block_no=block_no,
            event_type=event_type,
            step_name=step_name,
            mode=mode,
            payload=payload,
        )

    async def _grade_quiz(self, user, lesson, block_no: int, payload: dict) -> dict | None:
        lesson_payload = await CourseMiniAppLessonService(self.session).get_payload(
            lesson_order=course_miniapp_lesson_id(lesson),
            lang=getattr(user, "language", None) or "ru",
            level=getattr(lesson, "level", None) or "hsk1",
            block_no=block_no or None,
        )
        canonical_questions = (lesson_payload or {}).get("quiz_questions")
        submitted_answers = payload.get("answers")
        if not isinstance(canonical_questions, list) or not canonical_questions:
            return None
        if not isinstance(submitted_answers, list) or len(submitted_answers) != len(canonical_questions):
            return None

        submitted_by_id = {}
        for answer in submitted_answers:
            if not isinstance(answer, dict):
                return None
            question_id = str(answer.get("question_id") or "").strip()
            if not question_id or question_id in submitted_by_id:
                return None
            submitted_by_id[question_id] = answer

        if set(submitted_by_id) != {str(question.get("id") or "") for question in canonical_questions}:
            return None

        choice_types = {
            "multiple_choice",
            "listening_choice",
            "fill_blank",
            "fill_blank_choice",
            "tap_missing_word",
            "choose_meaning_in_context",
            "grammar_in_context",
            "listen_and_fill",
            "odd_one_out",
            "grammar_example_to_pattern",
            "grammar_pattern_to_example",
        }
        order_types = {"word_order", "build_chinese_sentence", "build_sentence_chips"}

        score = 0
        wrong_items = []
        normalized_answers = []
        for question in canonical_questions:
            question_id = str(question.get("id") or "")
            question_type = str(question.get("type") or "multiple_choice")
            answer = submitted_by_id[question_id]

            if question_type in order_types:
                expected = self._normalize_token_list(question.get("answer"))
                actual = self._normalize_token_list(answer.get("answer_tokens") or answer.get("tokens"))
                if not actual:
                    actual = self._normalize_token_list(answer.get("selected_answer"))
                if not expected or not actual:
                    return None
                is_correct = actual == expected
                selected_answer = " ".join(actual)
                correct_answer = " ".join(expected)
                normalized_answers.append(
                    {
                        "question_id": question_id,
                        "selected_index": None,
                        "selected_answer": selected_answer,
                        "answer_tokens": actual,
                    }
                )
            elif question_type in choice_types or question.get("opts"):
                options = question.get("opts") or question.get("options")
                try:
                    correct_index = int(question.get("ans"))
                except (TypeError, ValueError):
                    return None
                if not isinstance(options, list) or not (0 <= correct_index < len(options)):
                    return None

                selected_answer = str(answer.get("selected_answer") or "")
                selected_index = self._to_int(answer.get("selected_index"), -1)
                if not (0 <= selected_index < len(options)):
                    if selected_answer not in options:
                        return None
                    selected_index = options.index(selected_answer)
                if selected_answer and selected_answer != str(options[selected_index]):
                    return None

                selected_answer = str(options[selected_index])
                correct_answer = str(options[correct_index])
                is_correct = selected_index == correct_index
                normalized_answers.append(
                    {
                        "question_id": question_id,
                        "selected_index": selected_index,
                        "selected_answer": selected_answer,
                    }
                )
            else:
                return None

            if is_correct:
                score += 1
            else:
                wrong_items.append(
                    {
                        "question": str(question.get("q") or question.get("prompt") or ""),
                        "selected_answer": selected_answer,
                        "correct_answer": correct_answer,
                        "explanation": str(question.get("expl") or question.get("explanation") or ""),
                    }
                )


        total = len(canonical_questions)
        return {
            "answers": normalized_answers,
            "score": score,
            "total": total,
            "percent": round((score / total) * 100) if total else 0,
            "wrong_items": wrong_items,
        }

    async def _resolve_context(self, telegram_id: int, mini_lesson_id: int):
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return None, None, None, "access_start_first"

        await AccessService(self.session).ensure_active_course_access(user)
        trial_service = CourseTrialService(self.session)
        if not (trial_service.is_paid_user(user) or trial_service.is_free_user(user)):
            await self.session.commit()
            return user, None, None, "course_only_active_users"

        progress = await self.progress_repo.get_by_user_id(user.id, for_update=True)
        if not progress or not progress.current_lesson_id:
            return user, progress, None, "course_no_lesson_found"

        lesson = await self.lesson_repo.get_by_id(progress.current_lesson_id)
        if not lesson:
            return user, progress, None, "course_no_lesson_found"

        if not trial_service.can_access_lesson(user, lesson.id):
            return user, progress, lesson, "course_only_active_users"

        if not is_course_miniapp_supported(lesson):
            return user, progress, lesson, "course_miniapp_unsupported_lesson"

        if mini_lesson_id <= 0 or course_miniapp_lesson_id(lesson) != mini_lesson_id:
            return user, progress, lesson, "course_miniapp_lesson_mismatch"

        return user, progress, lesson, ""

    async def save_quiz_result(self, telegram_id: int, payload: dict) -> dict:
        mini_lesson_id = self._to_int(payload.get("lesson_id"))
        block_no = self._to_int(payload.get("block_no") or payload.get("block"))
        user, progress, lesson, error_key = await self._resolve_context(telegram_id, mini_lesson_id)
        if error_key:
            return {"error_key": error_key}
        if not self._validate_quiz_state(progress, block_no):
            return {"error_key": "course_miniapp_lesson_mismatch"}

        grading = await self._grade_quiz(user, lesson, block_no, payload)
        if not grading:
            return {"error_key": "course_miniapp_lesson_mismatch"}

        score = grading["score"]
        total = grading["total"]
        percent = grading["percent"]
        wrong_items = normalize_result_items(grading["wrong_items"])
        passed = percent >= 60

        await self.attempt_repo.create(
            user_id=user.id,
            lesson_id=lesson.id,
            attempt_type="quiz",
            step_name=f"block_quiz_{block_no}" if block_no else "miniapp_quiz",
            score=percent,
            passed=passed,
            answers_json=json.dumps(
                {
                    "telegram_id": telegram_id,
                    "lesson_id": course_miniapp_lesson_id(lesson),
                    "score": score,
                    "total": total,
                    "percent": percent,
                    "block_no": block_no or None,
                    "answers": grading["answers"],
                    "wrong_items": wrong_items,
                    "source": "miniapp_server_graded",
                },
                ensure_ascii=False,
            ),
            ai_feedback=None,
        )
        await self._record_pilot_event(
            user=user,
            lesson=lesson,
            event_type="completed",
            step_name=f"quiz_block_{block_no}" if block_no else "quiz",
            mode="quiz",
            block_no=block_no or None,
            payload={"score": score, "total": total, "percent": percent, "passed": passed},
        )

        if block_no:
            next_step = CourseEngineService(self.session).get_next_step_name(
                f"block_quiz_{block_no}",
                lesson,
            )
            await self.progress_repo.set_current_lesson_and_step(
                progress=progress,
                lesson_id=lesson.id,
                step=next_step,
                waiting_for="none",
            )
            trial_service = CourseTrialService(self.session)
            if trial_service.should_start_force_sub_at_step(next_step):
                await trial_service.mark_force_sub_required(user)
        else:
            next_step = "satisfaction_check"
            await self.progress_repo.set_current_lesson_and_step(
                progress=progress,
                lesson_id=lesson.id,
                step=next_step,
                waiting_for="satisfaction_answer",
            )
        await self.session.commit()
        await ConversionFunnelService().record(
            event_name="quiz_completed",
            user=user,
            source="course_miniapp",
            lesson_id=lesson.id,
            payload={
                "lesson_order": course_miniapp_lesson_id(lesson),
                "block_no": block_no or None,
                "score": score,
                "total": total,
                "percent": percent,
                "passed": passed,
            },
        )

        return {
            "error_key": None,
            "user": user,
            "lesson": lesson,
            "lesson_id": course_miniapp_lesson_id(lesson),
            "block_no": block_no or None,
            "next_step": next_step,
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
        if (
            getattr(progress, "current_step", None) != "homework"
            or getattr(progress, "waiting_for", None) != "homework_result"
        ):
            return {"error_key": "course_miniapp_lesson_mismatch"}

        answers = self._normalize_homework_answers(payload.get("answers"))
        reinforcement = await self._grade_reinforcement(user, lesson, payload, answers)
        if reinforcement:
            homework_score = int(reinforcement["percent"])
            await self.attempt_repo.create(
                user_id=user.id,
                lesson_id=lesson.id,
                attempt_type="homework",
                step_name="miniapp_reinforcement",
                score=homework_score,
                passed=True,
                answers_json=json.dumps(
                    {
                        "telegram_id": telegram_id,
                        "lesson_id": course_miniapp_lesson_id(lesson),
                        "answers": answers,
                        "reinforcement_results": reinforcement["results"],
                        "homework_score": homework_score,
                        "feedback": reinforcement["feedback"],
                        "status": "completed",
                        "source": "miniapp_reinforcement_graded",
                    },
                    ensure_ascii=False,
                ),
                ai_feedback="\n".join(reinforcement["feedback"]) if reinforcement["feedback"] else None,
            )
            await self._record_pilot_event(
                user=user,
                lesson=lesson,
                event_type="completed",
                step_name="reinforcement",
                mode="homework",
                block_no=self._to_int(payload.get("block_no") or payload.get("block")) or None,
                payload={"score": reinforcement["score"], "total": reinforcement["total"], "percent": homework_score},
            )
            await self.progress_repo.set_homework_status(progress, "completed")
            await self.progress_repo.set_current_lesson_and_step(
                progress=progress,
                lesson_id=lesson.id,
                step="completed",
                waiting_for="none",
            )
            await CourseTrialService(self.session).mark_trial_completed(user, lesson.id)
            await self.session.commit()
            await ConversionFunnelService().record(
                event_name="homework_completed",
                user=user,
                source="course_miniapp_reinforcement",
                lesson_id=lesson.id,
                payload={
                    "lesson_order": course_miniapp_lesson_id(lesson),
                    "score": reinforcement["score"],
                    "total": reinforcement["total"],
                    "percent": homework_score,
                },
            )

            return {
                "error_key": None,
                "user": user,
                "lesson": lesson,
                "lesson_id": course_miniapp_lesson_id(lesson),
                "answers": answers,
                "homework_score": homework_score,
                "feedback": reinforcement["feedback"],
                "status": "completed",
                "passed": True,
            }

        if not self._has_homework_answers(answers):
            return {"error_key": "course_homework_empty"}

        tutor = CourseTutorService()
        evaluation = await tutor.evaluate_homework(
            user_language=user.language if getattr(user, "language", None) else "ru",
            user_level=user.level if getattr(user, "level", None) else "hsk3",
            lesson=lesson,
            submission_text=json.dumps(answers, ensure_ascii=False),
        )
        homework_score = self._to_int(evaluation.get("score"))
        passed = bool(evaluation.get("passed"))
        feedback_text = str(evaluation.get("feedback_text") or "").strip()
        feedback = [feedback_text] if feedback_text else []
        status = "completed" if passed else "needs_revision"
        await AIUsageBudgetService(self.session).record_usage(
            telegram_id=telegram_id,
            result=tutor.last_ai_result,
            source="course_miniapp_homework",
        )
        await AccessService(self.session).downgrade_non_paid_active_if_budget_depleted(telegram_id)

        await self.attempt_repo.create(
            user_id=user.id,
            lesson_id=lesson.id,
            attempt_type="homework",
            step_name="miniapp_homework",
            score=homework_score if homework_score is not None else 0,
            passed=passed,
            answers_json=json.dumps(
                {
                    "telegram_id": telegram_id,
                    "lesson_id": course_miniapp_lesson_id(lesson),
                    "answers": answers,
                    "homework_score": homework_score,
                    "feedback": feedback,
                    "status": status,
                    "source": "miniapp_server_graded",
                },
                ensure_ascii=False,
            ),
            ai_feedback="\n".join(feedback) if feedback else None,
        )
        await self._record_pilot_event(
            user=user,
            lesson=lesson,
            event_type="completed" if passed else "revision",
            step_name="homework",
            mode="homework",
            block_no=self._to_int(payload.get("block_no") or payload.get("block")) or None,
            payload={"score": homework_score, "passed": passed, "status": status},
        )

        if passed:
            await self.progress_repo.set_homework_status(progress, "completed")
            await self.progress_repo.set_current_lesson_and_step(
                progress=progress,
                lesson_id=lesson.id,
                step="completed",
                waiting_for="none",
            )
            await CourseTrialService(self.session).mark_trial_completed(user, lesson.id)
        else:
            await self.progress_repo.set_homework_status(progress, "assigned")
            await self.progress_repo.set_current_lesson_and_step(
                progress=progress,
                lesson_id=lesson.id,
                step="homework",
                waiting_for="homework_decision",
            )
        await self.session.commit()
        if passed:
            await ConversionFunnelService().record(
                event_name="homework_completed",
                user=user,
                source="course_miniapp_homework",
                lesson_id=lesson.id,
                payload={
                    "lesson_order": course_miniapp_lesson_id(lesson),
                    "score": homework_score,
                    "passed": passed,
                    "status": status,
                },
            )

        return {
            "error_key": None,
            "user": user,
            "lesson": lesson,
            "lesson_id": course_miniapp_lesson_id(lesson),
            "answers": answers,
            "homework_score": homework_score,
            "feedback": feedback,
            "status": status,
            "passed": passed,
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
        context_payload = {}

        if quiz.get("source") in {"miniapp", "miniapp_server_graded"}:
            wrong_items = normalize_result_items(quiz.get("wrong_items"))
            context_payload["miniapp_quiz_result"] = {
                "lesson_id": quiz.get("lesson_id"),
                "block_no": quiz.get("block_no"),
                "score": quiz.get("score"),
                "total": quiz.get("total"),
                "percent": quiz.get("percent"),
                "wrong_items": wrong_items[:10],
            }

        if homework.get("source") in {"miniapp", "miniapp_server_graded", "miniapp_reinforcement_graded"}:
            feedback = normalize_result_items(homework.get("feedback"))
            context_payload["miniapp_homework_result"] = {
                "lesson_id": homework.get("lesson_id"),
                "status": homework.get("status"),
                "homework_score": homework.get("homework_score"),
                "answers": homework.get("answers") or {},
                "feedback": feedback[:10],
            }

        if not context_payload:
            return ""

        return (
            "MINI APP RESULT CONTEXT (JSON):\n"
            + json.dumps(context_payload, ensure_ascii=False, indent=2)[:4000]
            + "\n\nAI UCHUN QOIDA: foydalanuvchiga yordam berganda shu Mini App natijalarini "
            "yangi course block materiali bilan birga ishlat. Ayniqsa wrong_items, homework answers "
            "va feedback bo'yicha aynan qaysi savolda/xatoda muammo bo'lganini tushuntir."
        )
