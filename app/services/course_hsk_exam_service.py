"""Server-authoritative HSK 1-4 exam sessions backed by static material."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.repositories.user_repo import UserRepository
from app.services.course_gamification_service import CourseGamificationService
from app.services.course_miniapp_access_service import CourseMiniAppAccessService
from app.services.course_miniapp_analytics_service import CourseMiniAppAnalyticsService
from app.services.course_mistake_service import CourseMistakeService
from app.services.course_question_material import (
    COURSE_HSK_EXAM_SECTIONS,
    COURSE_QUESTION_MATERIAL_VERSION,
    CourseQuestionMaterialError,
    canonical_material_digest,
    canonicalize_hsk_exam_material,
    normalize_hsk_level,
    normalize_material_language,
    public_questions_projection,
    shuffle_exam_questions,
)


HSK_EXAM_SERVICE_VERSION = 2
HSK_EXAM_EVENT_SOURCE = "course_hsk_exam"
HSK_EXAM_BASE_XP = 10
HSK_EXAM_STATIC_DIR = Path(__file__).resolve().parents[1] / "static" / "course_v3_data" / "exams"
HSK_EXAM_ACCESS_FEATURE = "training_test"
HSK_EXAM_GRADING_FIELDS = (
    "material_version",
    "id",
    "format",
    "category",
    "section",
    "prompt",
    "sentence",
    "audio_text",
    "options",
    "option_materials",
    "answer_index",
    "explanation",
)


class CourseHskExamService:
    """Load, issue and grade one immutable HSK exam attempt."""

    def __init__(self, session):
        self.session = session
        self.user_repo = UserRepository(session)
        self.analytics = CourseMiniAppAnalyticsService(session)
        self.access = CourseMiniAppAccessService(session)
        self.mistakes = CourseMistakeService(session)
        self.gamification = CourseGamificationService(session)

    @staticmethod
    def _source_path(level: str) -> str:
        return f"app/static/course_v3_data/exams/{level}.json"

    @classmethod
    def load_material(cls, level: str, lang: str) -> dict[str, Any]:
        """Load and strictly canonicalize the checked-in legacy JSON file."""

        level = normalize_hsk_level(level)
        lang = normalize_material_language(lang)
        path = HSK_EXAM_STATIC_DIR / f"{level}.json"
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise CourseQuestionMaterialError(f"Unable to load HSK exam material: {level}") from error
        return canonicalize_hsk_exam_material(
            raw,
            level=level,
            lang=lang,
            source_path=cls._source_path(level),
        )

    @staticmethod
    def _access_key(user_id: int, access_ref: str) -> str:
        value = f"{int(user_id)}:{access_ref}".encode("utf-8")
        return hashlib.sha256(value).hexdigest()[:24]

    @classmethod
    def _session_id(cls, user_id: int, level: str, access_ref: str) -> str:
        access_key = cls._access_key(user_id, access_ref)
        return f"hsk-exam:{int(user_id)}:{level}:v{HSK_EXAM_SERVICE_VERSION}:{access_key}"

    @staticmethod
    def _started_dedupe_key(access_key: str) -> str:
        return f"hsk-exam:v{HSK_EXAM_SERVICE_VERSION}:access:{access_key}:started"

    @staticmethod
    def _xp_activity_ref(user_id: int, level: str, now: datetime | None = None) -> str:
        day = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).date().isoformat()
        return f"hsk-exam:{int(user_id)}:{normalize_hsk_level(level)}:{day}:xp"

    @staticmethod
    def _grading_snapshot(questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Keep the exact issued grading material, without bulky translations."""

        snapshots = []
        for question in questions:
            snapshot = {
                key: question.get(key)
                for key in HSK_EXAM_GRADING_FIELDS
                if key in question
            }
            materials = question.get("option_materials")
            if isinstance(materials, list):
                snapshot["option_materials"] = [
                    {
                        key: material.get(key)
                        for key in ("zh", "pinyin", "translation")
                        if isinstance(material, dict) and key in material
                    }
                    for material in materials
                ]
            source = question.get("source") if isinstance(question.get("source"), dict) else {}
            snapshot["question_no"] = source.get("question_no")
            snapshots.append(snapshot)
        return snapshots

    @staticmethod
    def _inflate_grading_snapshot(
        questions: list[dict[str, Any]],
        *,
        level: str,
        lang: str,
    ) -> list[dict[str, Any]]:
        inflated = []
        for question in questions:
            audio_text = str(question.get("audio_text") or "")
            section = str(question.get("section") or question.get("category") or "")
            inflated.append(
                {
                    **question,
                    "audio": {"kind": "tts", "text": audio_text} if audio_text else None,
                    "source": {
                        "kind": "static_hsk_exam",
                        "schema_version": 1,
                        "level": level,
                        "section": section,
                        "question_no": question.get("question_no"),
                    },
                    "prompt_translations": {lang: str(question.get("prompt") or "")},
                }
            )
        return inflated

    @staticmethod
    def _event_payload(event: CourseMiniAppEvent | Any) -> dict[str, Any]:
        try:
            payload = json.loads(getattr(event, "payload_json", None) or "{}")
        except (TypeError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    async def _started_event(self, user, session_id: str):
        result = await self.session.execute(
            select(CourseMiniAppEvent)
            .where(
                CourseMiniAppEvent.user_id == user.id,
                CourseMiniAppEvent.telegram_id == int(user.telegram_id),
                CourseMiniAppEvent.event_name == "test_started",
                CourseMiniAppEvent.session_id == session_id,
                CourseMiniAppEvent.source == HSK_EXAM_EVENT_SOURCE,
            )
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def _started_for_access_key(self, user, access_key: str):
        result = await self.session.execute(
            select(CourseMiniAppEvent)
            .where(
                CourseMiniAppEvent.user_id == user.id,
                CourseMiniAppEvent.telegram_id == int(user.telegram_id),
                CourseMiniAppEvent.event_name == "test_started",
                CourseMiniAppEvent.source == HSK_EXAM_EVENT_SOURCE,
                CourseMiniAppEvent.dedupe_key == self._started_dedupe_key(access_key),
            )
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def _completed_event(self, user, session_id: str):
        result = await self.session.execute(
            select(CourseMiniAppEvent).where(
                CourseMiniAppEvent.user_id == user.id,
                CourseMiniAppEvent.telegram_id == int(user.telegram_id),
                CourseMiniAppEvent.event_name == "test_completed",
                CourseMiniAppEvent.session_id == session_id,
                CourseMiniAppEvent.source == HSK_EXAM_EVENT_SOURCE,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _duplicate_response(event) -> dict[str, Any]:
        payload = CourseHskExamService._event_payload(event)
        required = {"score", "total", "percent", "section_scores", "pass_score", "passed"}
        if not required.issubset(payload):
            return {"ok": False, "error": "exam_result_unavailable"}
        return {
            "ok": True,
            "duplicate": True,
            "score": int(payload["score"]),
            "total": int(payload["total"]),
            "percent": int(payload["percent"]),
            "section_scores": payload["section_scores"],
            "pass_score": int(payload["pass_score"]),
            "passed": bool(payload["passed"]),
            "reward": payload.get("reward") or {"awarded_xp": 0, "duplicate": True},
            "wrong_items": payload.get("wrong_items") or [],
        }

    @staticmethod
    def _completed_event_payload(completed_payload: dict[str, Any]) -> dict[str, Any]:
        """Compact the persisted result while keeping the immediate response rich.

        ``CourseMiniAppAnalyticsService`` caps payloads at 8KB. Rich mistake
        material is persisted in ``course_mistakes`` separately, so the
        idempotent result event only needs the fields used by the result UI.
        """

        compact_wrong_items = []
        for raw in completed_payload.get("wrong_items") or []:
            if not isinstance(raw, dict):
                continue
            compact_wrong_items.append(
                {
                    key: raw.get(key)
                    for key in (
                        "question_id",
                        "question",
                        "selected_answer",
                        "correct_answer",
                        "subtype",
                        "category",
                    )
                    if raw.get(key) not in (None, "")
                }
            )
        return {**completed_payload, "wrong_items": compact_wrong_items}

    @staticmethod
    def _validate_started_payload(payload: dict[str, Any], session_id: str) -> dict[str, Any]:
        try:
            level = normalize_hsk_level(payload.get("level"))
            lang = normalize_material_language(payload.get("lang"))
            material_version = int(payload.get("material_version"))
            duration_min = int(payload.get("duration_min"))
            pass_score = int(payload.get("pass_score"))
        except (CourseQuestionMaterialError, TypeError, ValueError) as error:
            raise CourseQuestionMaterialError("Invalid HSK exam session payload") from error
        question_ids = payload.get("question_ids")
        if (
            material_version != COURSE_QUESTION_MATERIAL_VERSION
            or not isinstance(question_ids, list)
            or not question_ids
            or any(not isinstance(value, str) or not value for value in question_ids)
            or len(set(question_ids)) != len(question_ids)
        ):
            raise CourseQuestionMaterialError("Invalid HSK exam session payload")
        shuffle_seed = str(payload.get("shuffle_seed") or "")
        digest = str(payload.get("material_digest") or "")
        material_id = str(payload.get("material_id") or "")
        access_key = str(payload.get("access_key") or "")
        if (
            shuffle_seed != session_id
            or len(digest) != 64
            or not material_id
            or not 1 <= duration_min <= 240
            or not 1 <= pass_score <= 100
            or (access_key and len(access_key) != 24)
        ):
            raise CourseQuestionMaterialError("Invalid HSK exam session payload")

        grading_questions = payload.get("grading_questions")
        if grading_questions is not None:
            if not isinstance(grading_questions, list) or len(grading_questions) != len(question_ids):
                raise CourseQuestionMaterialError("Invalid HSK exam grading snapshot")
            validated_questions = []
            for raw in grading_questions:
                if not isinstance(raw, dict):
                    raise CourseQuestionMaterialError("Invalid HSK exam grading snapshot")
                question_id = str(raw.get("id") or "")
                section = str(raw.get("section") or raw.get("category") or "")
                options = raw.get("options")
                option_materials = raw.get("option_materials")
                answer_raw = raw.get("answer_index")
                if isinstance(answer_raw, bool):
                    raise CourseQuestionMaterialError("Invalid HSK exam grading snapshot")
                try:
                    answer_index = int(answer_raw)
                except (TypeError, ValueError) as error:
                    raise CourseQuestionMaterialError("Invalid HSK exam grading snapshot") from error
                if (
                    not question_id
                    or section not in COURSE_HSK_EXAM_SECTIONS
                    or not isinstance(options, list)
                    or not 2 <= len(options) <= 6
                    or any(not isinstance(option, str) or not option.strip() for option in options)
                    or not isinstance(option_materials, list)
                    or len(option_materials) != len(options)
                    or any(not isinstance(material, dict) for material in option_materials)
                    or not 0 <= answer_index < len(options)
                ):
                    raise CourseQuestionMaterialError("Invalid HSK exam grading snapshot")
                validated_questions.append({**raw, "answer_index": answer_index, "section": section})
            if [question["id"] for question in validated_questions] != question_ids:
                raise CourseQuestionMaterialError("Invalid HSK exam grading snapshot")
            grading_questions = validated_questions
        return {
            "level": level,
            "lang": lang,
            "material_id": material_id,
            "duration_min": duration_min,
            "pass_score": pass_score,
            "question_ids": question_ids,
            "shuffle_seed": shuffle_seed,
            "material_digest": digest,
            "access_key": access_key,
            "grading_questions": grading_questions,
        }

    def _questions_for_started_session(self, session_data: dict[str, Any]) -> list[dict[str, Any]]:
        snapshot = session_data.get("grading_questions")
        if snapshot is not None:
            return self._inflate_grading_snapshot(
                snapshot,
                level=session_data["level"],
                lang=session_data["lang"],
            )

        # Backward-compatible fallback for sessions issued before grading
        # snapshots were stored. Those legacy attempts still use digest checks.
        material = self.load_material(session_data["level"], session_data["lang"])
        if canonical_material_digest(material) != session_data["material_digest"]:
            raise CourseQuestionMaterialError("HSK exam material changed")
        questions = shuffle_exam_questions(material["questions"], session_data["shuffle_seed"])
        if [question["id"] for question in questions] != session_data["question_ids"]:
            raise CourseQuestionMaterialError("HSK exam material changed")
        return questions

    def _public_session_from_started(
        self,
        event,
        *,
        session_id: str,
        requested_level: str,
        requested_lang: str,
        access_key: str,
    ) -> dict[str, Any]:
        try:
            session_data = self._validate_started_payload(self._event_payload(event), session_id)
            if (
                session_data["level"] != requested_level
                or session_data["lang"] != requested_lang
                or (session_data.get("access_key") and session_data["access_key"] != access_key)
            ):
                return {"ok": False, "error": "hsk_exam_access_ref_conflict"}
            questions = self._questions_for_started_session(session_data)
        except CourseQuestionMaterialError as error:
            if "material changed" in str(error).lower():
                return {"ok": False, "error": "hsk_exam_material_changed"}
            return {"ok": False, "error": "invalid_hsk_exam_session"}
        return {
            "ok": True,
            "duplicate": True,
            "session": {
                "id": session_id,
                "level": session_data["level"],
                "duration_min": session_data["duration_min"],
                "pass_score": session_data["pass_score"],
                "questions": public_questions_projection(questions),
            },
        }

    async def start(
        self,
        telegram_id: int,
        *,
        level: str,
        lang: str,
        access_ref: str,
        ad_supported: bool = False,
    ) -> dict[str, Any]:
        level = normalize_hsk_level(level)
        lang = normalize_material_language(lang)
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return {"ok": False, "error": "access_start_first"}

        try:
            access_ref = self.access.normalize_access_ref(access_ref)
        except ValueError:
            return {"ok": False, "error": "invalid_access_ref"}
        if not self.access.is_paid_user(user) and not self.access.is_free_user(user):
            return {"ok": False, "error": "course_access_blocked"}

        access_key = self._access_key(user.id, access_ref)
        session_id = self._session_id(user.id, level, access_ref)
        existing = await self._started_for_access_key(user, access_key)
        if existing:
            existing_session_id = str(getattr(existing, "session_id", None) or "")
            if not existing_session_id:
                return {"ok": False, "error": "invalid_hsk_exam_session"}
            return self._public_session_from_started(
                existing,
                session_id=existing_session_id,
                requested_level=level,
                requested_lang=lang,
                access_key=access_key,
            )

        if ad_supported:
            access = await self.access.verify_ad_authorization(
                user,
                feature_key=HSK_EXAM_ACCESS_FEATURE,
                access_ref=access_ref,
            )
        else:
            access = await self.access.consume_daily_use(
                user,
                feature_key=HSK_EXAM_ACCESS_FEATURE,
                ref=access_ref,
                lifetime=True,
            )
        if not access.get("allowed"):
            return {
                "ok": False,
                "error": access.get("error") or "free_feature_limit_reached",
                "ad": {"available": True, "limited": False},
            }

        material = self.load_material(level, lang)
        questions = shuffle_exam_questions(material["questions"], session_id)
        grading_questions = self._grading_snapshot(questions)
        issued_questions = self._inflate_grading_snapshot(
            grading_questions,
            level=level,
            lang=lang,
        )
        started_payload = {
            "material_version": COURSE_QUESTION_MATERIAL_VERSION,
            "material_id": material["id"],
            "material_digest": canonical_material_digest(material),
            "level": level,
            "lang": lang,
            "duration_min": material["duration_min"],
            "pass_score": material["pass_score"],
            "question_ids": [question["id"] for question in issued_questions],
            "shuffle_seed": session_id,
            "access_key": access_key,
            "grading_questions": grading_questions,
        }
        event = await self.analytics.record_server_event(
            event_name="test_started",
            telegram_id=int(user.telegram_id),
            user_id=user.id,
            source=HSK_EXAM_EVENT_SOURCE,
            level=level,
            session_id=session_id,
            dedupe_key=self._started_dedupe_key(access_key),
            payload=started_payload,
        )
        if not event.get("ok"):
            return {"ok": False, "error": "exam_session_start_failed"}
        if event.get("duplicate"):
            existing = await self._started_for_access_key(user, access_key)
            if existing:
                return self._public_session_from_started(
                    existing,
                    session_id=str(getattr(existing, "session_id", None) or session_id),
                    requested_level=level,
                    requested_lang=lang,
                    access_key=access_key,
                )
        await self.session.commit()
        return {
            "ok": True,
            "duplicate": False,
            "session": {
                "id": session_id,
                "level": level,
                "duration_min": int(material["duration_min"]),
                "pass_score": int(material["pass_score"]),
                "questions": public_questions_projection(issued_questions),
            },
        }

    @staticmethod
    def _submitted_answers(answers: list, questions: list[dict]) -> dict[str, int] | None:
        if not isinstance(answers, list) or len(answers) != len(questions):
            return None
        submitted: dict[str, int] = {}
        for raw in answers:
            if not isinstance(raw, dict):
                return None
            question_id = str(raw.get("question_id") or "")
            selected_raw = raw.get("selected_index")
            if not question_id or question_id in submitted or isinstance(selected_raw, bool):
                return None
            try:
                selected = int(selected_raw)
            except (TypeError, ValueError):
                return None
            submitted[question_id] = selected
        expected = {question["id"] for question in questions}
        return submitted if set(submitted) == expected else None

    @staticmethod
    def _question_text(question: dict) -> str:
        prompt = str(question.get("prompt") or "").strip()
        sentence = str(question.get("sentence") or "").strip()
        if sentence and sentence not in prompt:
            return f"{prompt}\n{sentence}".strip()
        return prompt or sentence

    async def complete(
        self,
        telegram_id: int,
        *,
        session_id: str,
        answers: list,
        level: str | None = None,
        lang: str | None = None,
    ) -> dict[str, Any]:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return {"ok": False, "error": "access_start_first"}
        session_id = str(session_id or "").strip()
        expected_prefix = f"hsk-exam:{int(user.id)}:"
        if not session_id.startswith(expected_prefix) or len(session_id) > 80:
            return {"ok": False, "error": "invalid_hsk_exam_session"}

        started = await self._started_event(user, session_id)
        if not started:
            return {"ok": False, "error": "invalid_hsk_exam_session"}
        completed = await self._completed_event(user, session_id)
        if completed:
            return self._duplicate_response(completed)

        try:
            session_data = self._validate_started_payload(self._event_payload(started), session_id)
            if level is not None and normalize_hsk_level(level) != session_data["level"]:
                raise CourseQuestionMaterialError("Exam level changed during the session")
            if lang is not None and normalize_material_language(lang) != session_data["lang"]:
                raise CourseQuestionMaterialError("Exam language changed during the session")
        except CourseQuestionMaterialError:
            return {"ok": False, "error": "invalid_hsk_exam_session"}

        try:
            questions = self._questions_for_started_session(session_data)
        except CourseQuestionMaterialError:
            return {"ok": False, "error": "hsk_exam_material_changed"}
        submitted = self._submitted_answers(answers, questions)
        if submitted is None:
            return {"ok": False, "error": "hsk_exam_answers_incomplete"}

        section_scores = {
            section: {"score": 0, "total": 0, "percent": 0}
            for section in COURSE_HSK_EXAM_SECTIONS
        }
        score = 0
        wrong_items = []
        for question in questions:
            selected = submitted[question["id"]]
            options = question["options"]
            if not 0 <= selected < len(options):
                return {"ok": False, "error": "hsk_exam_answer_invalid"}
            correct_index = int(question["answer_index"])
            correct = selected == correct_index
            score += int(correct)
            section = str(question.get("section") or question.get("category") or "")
            if section not in section_scores:
                return {"ok": False, "error": "invalid_hsk_exam_material"}
            section_scores[section]["score"] += int(correct)
            section_scores[section]["total"] += 1
            if not correct:
                option_materials = question.get("option_materials")
                correct_option_material = (
                    option_materials[correct_index]
                    if isinstance(option_materials, list)
                    and len(option_materials) == len(options)
                    and isinstance(option_materials[correct_index], dict)
                    else {}
                )
                question_source = question.get("source") if isinstance(question.get("source"), dict) else {}
                category = "grammar" if section == "writing" else "word"
                material_source = {
                    "kind": "static_hsk_exam",
                    "level": session_data["level"],
                    "section": section,
                    "question_no": question_source.get("question_no"),
                    "source_schema_version": question_source.get("schema_version"),
                    "material_ref": question["id"],
                }
                material = {
                    "material_version": COURSE_QUESTION_MATERIAL_VERSION,
                    "material_ref": question["id"],
                    "format": str(question.get("format") or "choice"),
                    "category": category,
                    "language": session_data["lang"],
                    "prompt": self._question_text(question),
                    "sentence": str(question.get("sentence") or ""),
                    "audio_text": str(question.get("audio_text") or ""),
                    "pinyin": str(correct_option_material.get("pinyin") or ""),
                    "translation": str(correct_option_material.get("translation") or ""),
                    "options": list(options),
                    "answer_index": correct_index,
                    "correct_answer": options[correct_index],
                    "explanation": str(question.get("explanation") or ""),
                    "source": material_source,
                }
                wrong_items.append(
                    {
                        "question_id": question["id"],
                        "question": self._question_text(question),
                        "selected_answer": options[selected],
                        "correct_answer": options[correct_index],
                        "explanation": str(question.get("explanation") or ""),
                        "level": session_data["level"],
                        "type": str(question.get("format") or ""),
                        "format": str(question.get("format") or ""),
                        "subtype": section,
                        "category": category,
                        "language": session_data["lang"],
                        "sentence": str(question.get("sentence") or ""),
                        "audio_text": str(question.get("audio_text") or ""),
                        "pinyin": material["pinyin"],
                        "translation": material["translation"],
                        "material_ref": question["id"],
                        "source": material_source,
                        "material": material,
                    }
                )

        for result in section_scores.values():
            result["percent"] = round(result["score"] / result["total"] * 100) if result["total"] else 0
        total = len(questions)
        percent = round(score / total * 100) if total else 0
        pass_score = int(session_data["pass_score"])
        passed = percent >= pass_score

        await self.mistakes.record_items(
            user,
            wrong_items,
            source="test",
            level=session_data["level"],
        )
        reward = await self.gamification.award(
            user,
            activity_type="test",
            activity_ref=self._xp_activity_ref(user.id, session_data["level"]),
            base_xp=HSK_EXAM_BASE_XP,
            level=session_data["level"],
        )
        completed_payload = {
            "material_version": COURSE_QUESTION_MATERIAL_VERSION,
            "material_id": session_data["material_id"],
            "score": score,
            "total": total,
            "percent": percent,
            "section_scores": section_scores,
            "pass_score": pass_score,
            "passed": passed,
            "reward": reward,
            "wrong_items": wrong_items,
        }
        event = await self.analytics.record_server_event(
            event_name="test_completed",
            telegram_id=int(user.telegram_id),
            user_id=user.id,
            source=HSK_EXAM_EVENT_SOURCE,
            level=session_data["level"],
            session_id=session_id,
            dedupe_key=f"{session_id}:completed",
            payload=self._completed_event_payload(completed_payload),
        )
        if not event.get("ok"):
            return {"ok": False, "error": "hsk_exam_result_write_failed"}
        if event.get("duplicate"):
            await self.session.rollback()
            completed = await self._completed_event(user, session_id)
            return self._duplicate_response(completed) if completed else {
                "ok": False,
                "error": "exam_result_unavailable",
            }
        await self.session.commit()
        return {"ok": True, "duplicate": False, **completed_payload}
