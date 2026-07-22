import hashlib
import json
import re
from datetime import datetime, timezone

from sqlalchemy import func, select

from app.db.models.course_mistake import COURSE_MISTAKE_CATEGORIES, CourseMistake
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.course_miniapp_access_service import CourseMiniAppAccessService
from app.services.course_miniapp_analytics_service import (
    MAX_EVENT_PAYLOAD_CHARS,
    CourseMiniAppAnalyticsService,
)
from app.services.course_gamification_service import CourseGamificationService


MISTAKE_REVIEW_VERSION = 1
MISTAKE_REVIEW_MATERIAL_VERSION = 2
MISTAKE_REVIEW_FORMATS = {
    "word": "word_choice",
    "grammar": "grammar_correction",
    "character": "character_choice",
    "pronunciation": "pronunciation_correction",
}
MISTAKE_MATERIAL_LANGUAGES = {"uz", "ru", "tj"}
TRUSTED_MISTAKE_REWARD_SOURCES = {"test", "challenge", "voice", "training"}


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

    @classmethod
    def _language(cls, value) -> str:
        language = cls._text(value, 8).lower()
        return language if language in MISTAKE_MATERIAL_LANGUAGES else "und"

    @staticmethod
    def _json_dict(value) -> dict:
        if isinstance(value, dict):
            return value
        if isinstance(value, str) and value:
            try:
                parsed = json.loads(value)
            except (TypeError, json.JSONDecodeError):
                return {}
            return parsed if isinstance(parsed, dict) else {}
        return {}

    @classmethod
    def _material_payload(
        cls,
        raw: dict,
        *,
        category: str,
        source: str,
        level: str | None,
        lesson_order: int | None,
        prompt: str,
        correct_answer: str,
        explanation: str | None,
        user_language: str | None,
    ) -> dict:
        supplied = cls._json_dict(raw.get("material"))
        source_data = supplied.get("source") if isinstance(supplied.get("source"), dict) else {}
        raw_source = raw.get("source") if isinstance(raw.get("source"), dict) else {}
        source_data = {**raw_source, **source_data}

        material_ref = cls._text(
            supplied.get("material_ref")
            or raw.get("material_ref")
            or raw.get("question_id"),
            160,
        )
        material_format = cls._text(
            supplied.get("format") or raw.get("format") or raw.get("type"),
            64,
        ) or MISTAKE_REVIEW_FORMATS.get(category, "word_choice")
        language = cls._language(
            supplied.get("language")
            or raw.get("language")
            or raw.get("lang")
            or user_language
        )

        options_raw = supplied.get("options") if isinstance(supplied.get("options"), list) else raw.get("options")
        options = []
        if isinstance(options_raw, list):
            for value in options_raw[:12]:
                normalized = cls._text(value)
                if normalized and normalized not in options:
                    options.append(normalized)

        def token_list(field: str) -> list[str]:
            values = supplied.get(field)
            if not isinstance(values, list):
                return []
            return [
                normalized
                for normalized in (cls._text(value, 200) for value in values[:30])
                if normalized
            ]

        source_payload = {
            "kind": source,
            "trusted": source in TRUSTED_MISTAKE_REWARD_SOURCES,
            "level": cls._text(level or source_data.get("level") or raw.get("level"), 32) or None,
            "lesson": lesson_order if lesson_order is not None else source_data.get("lesson") or raw.get("lesson"),
            "section": source_data.get("section"),
            "card": source_data.get("card"),
            "question_no": source_data.get("question_no"),
            "material_ref": material_ref or None,
            "source_schema_version": source_data.get("source_schema_version"),
        }
        material = {
            "material_version": MISTAKE_REVIEW_MATERIAL_VERSION,
            "material_ref": material_ref,
            "format": material_format,
            "category": category,
            "language": language,
            "prompt": cls._text(supplied.get("prompt") or prompt),
            "sentence": cls._text(supplied.get("sentence") or raw.get("sentence")),
            "audio_text": cls._text(supplied.get("audio_text") or raw.get("audio_text")),
            "pinyin": cls._text(supplied.get("pinyin") or raw.get("pinyin"), 500),
            "translation": cls._text(supplied.get("translation"), 2000),
            "options": options,
            "tokens": token_list("tokens"),
            "answer_tokens": token_list("answer_tokens"),
            "correct_answer": correct_answer,
            "explanation": cls._text(supplied.get("explanation") or explanation),
            "source": source_payload,
        }
        try:
            answer_index = int(supplied.get("answer_index"))
        except (TypeError, ValueError):
            answer_index = None
        if answer_index is not None and 0 <= answer_index < len(options):
            material["answer_index"] = answer_index
        return material

    @classmethod
    def _stored_material(cls, item: CourseMistake) -> dict:
        material = cls._json_dict(getattr(item, "material_json", None))
        try:
            version = int(material.get("material_version") or 0)
        except (TypeError, ValueError):
            return {}
        return material if version >= 2 else {}

    @classmethod
    def _material_key(cls, category: str, material: dict, prompt: str, correct_answer: str) -> str:
        material_ref = cls._text(material.get("material_ref"), 160)
        if material_ref:
            normalized = f"{category}|material:{material_ref}".casefold()
            return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return cls._key(category, prompt, correct_answer)

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
            supplied_material = self._json_dict(raw.get("material"))
            prompt = self._text(
                supplied_material.get("prompt")
                or raw.get("question")
                or raw.get("prompt")
                or raw.get("correction")
            )
            correct_answer = self._text(
                supplied_material.get("correct_answer")
                or raw.get("correct_answer")
                or raw.get("correct")
                or raw.get("correction")
            )
            if not prompt or not correct_answer:
                continue
            category = self._category({**raw, **supplied_material}, normalized_source)
            explanation = self._text(
                supplied_material.get("explanation") or raw.get("explanation")
            ) or None
            material = self._material_payload(
                raw,
                category=category,
                source=normalized_source,
                level=level,
                lesson_order=lesson_order,
                prompt=prompt,
                correct_answer=correct_answer,
                explanation=explanation,
                user_language=getattr(user, "language", None),
            )
            normalized.append(
                {
                    "mistake_key": self._material_key(category, material, prompt, correct_answer),
                    "legacy_mistake_key": self._key(category, prompt, correct_answer),
                    "category": category,
                    "prompt": prompt,
                    "user_answer": self._text(raw.get("selected_answer") or raw.get("user_answer")) or None,
                    "correct_answer": correct_answer,
                    "explanation": explanation,
                    "material_json": json.dumps(material, ensure_ascii=False, separators=(",", ":")),
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
            if not mistake and data["legacy_mistake_key"] != data["mistake_key"]:
                legacy_result = await self.session.execute(
                    select(CourseMistake).where(
                        CourseMistake.user_id == user.id,
                        CourseMistake.mistake_key == data["legacy_mistake_key"],
                    )
                )
                mistake = legacy_result.scalar_one_or_none()
            if mistake:
                mistake.mistake_key = data["mistake_key"]
                mistake.wrong_count = int(mistake.wrong_count or 0) + 1
                mistake.category = data["category"]
                mistake.prompt = data["prompt"]
                mistake.user_answer = data["user_answer"]
                mistake.correct_answer = data["correct_answer"]
                mistake.explanation = data["explanation"] or mistake.explanation
                mistake.material_json = data["material_json"]
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
                        material_json=data["material_json"],
                        first_seen_at=now,
                        last_seen_at=now,
                    )
                )
            recorded += 1
        await self.session.flush()
        return recorded

    async def _items(
        self,
        user_id: int,
        limit: int = 50,
        *,
        category: str | None = None,
        offset: int = 0,
    ) -> list[CourseMistake]:
        weakness = CourseMistake.wrong_count - CourseMistake.resolved_count
        query = (
            select(CourseMistake)
            .where(CourseMistake.user_id == user_id, weakness > 0)
            .order_by(weakness.desc(), CourseMistake.last_seen_at.desc())
        )
        if category in COURSE_MISTAKE_CATEGORIES:
            query = query.where(CourseMistake.category == category)
        result = await self.session.execute(query.offset(max(0, int(offset or 0))).limit(max(1, int(limit or 1))))
        return list(result.scalars().all())

    async def overview(
        self,
        telegram_id: int,
        *,
        category: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return {"ok": False, "error": "access_start_first"}
        category = self._text(category, 24).lower() or None
        if category and category not in COURSE_MISTAKE_CATEGORIES:
            return {"ok": False, "error": "invalid_mistake_category"}
        try:
            limit = max(1, min(100, int(limit)))
            offset = max(0, min(100000, int(offset)))
        except (TypeError, ValueError):
            return {"ok": False, "error": "invalid_mistake_pagination"}
        page_items = await self._items(
            user.id,
            limit=limit + 1,
            category=category,
            offset=offset,
        )
        has_more = len(page_items) > limit
        items = page_items[:limit]
        counts_result = await self.session.execute(
            select(CourseMistake.category, func.sum(CourseMistake.wrong_count - CourseMistake.resolved_count))
            .where(
                CourseMistake.user_id == user.id,
                CourseMistake.wrong_count > CourseMistake.resolved_count,
            )
            .group_by(CourseMistake.category)
        )
        category_counts = {str(category): int(count or 0) for category, count in counts_result.all()}
        overview_items = []
        for item in items:
            material = self._stored_material(item)
            source = material.get("source") if isinstance(material.get("source"), dict) else {}
            overview_items.append(
                {
                    "id": item.id,
                    "category": item.category,
                    "source": item.source,
                    "level": item.level,
                    "lesson": item.lesson_order,
                    "section": source.get("section"),
                    "card": source.get("card"),
                    "material_ref": material.get("material_ref") or "",
                    "material_version": int(material.get("material_version") or 1),
                    "format": material.get("format")
                    or MISTAKE_REVIEW_FORMATS.get(item.category, "word_choice"),
                    "language": material.get("language") or "und",
                    "question": material.get("prompt") or item.prompt,
                    "sentence": material.get("sentence") or "",
                    "audio_text": material.get("audio_text") or "",
                    "pinyin": material.get("pinyin") or "",
                    "user_answer": item.user_answer,
                    "correct_answer": item.correct_answer,
                    "explanation": item.explanation,
                    "count": self._weakness(item),
                }
            )
        return {
            "ok": True,
            "summary": {
                "total": sum(category_counts.values()),
                "categories": category_counts,
            },
            "filter": {"category": category},
            "pagination": {
                "offset": offset,
                "limit": limit,
                "returned": len(items),
                "has_more": has_more,
            },
            "items": overview_items,
        }

    @classmethod
    def _review_question(cls, item: CourseMistake, category_answers: list[str]) -> dict | None:
        material = cls._stored_material(item)
        correct_answer = cls._text(item.correct_answer)
        user_answer = cls._text(item.user_answer)
        options = []
        if user_answer and user_answer != correct_answer:
            options.append(user_answer)
        material_options = material.get("options") if isinstance(material.get("options"), list) else []
        for value in (correct_answer, *material_options, *category_answers):
            normalized = cls._text(value)
            if normalized and normalized not in options:
                options.append(normalized)
        options = options[:4]
        if len(options) < 2:
            return None
        options.sort(
            key=lambda value: hashlib.sha256(
                f"mistake-review:{item.id}:{value}".encode("utf-8")
            ).digest()
        )

        lesson_order = getattr(item, "lesson_order", None)
        try:
            lesson_order = int(lesson_order) if lesson_order is not None else None
        except (TypeError, ValueError):
            lesson_order = None
        category = cls._text(getattr(item, "category", None), 24).lower() or "word"
        source = material.get("source") if isinstance(material.get("source"), dict) else {}
        source = {
            **source,
            "kind": cls._text(getattr(item, "source", None), 32) or source.get("kind") or "unknown",
            "level": cls._text(getattr(item, "level", None), 32) or source.get("level") or None,
            "lesson": lesson_order if lesson_order is not None else source.get("lesson"),
        }
        return {
            "id": f"mistake:{item.id}",
            "category": category,
            "prompt": cls._text(material.get("prompt")) or item.prompt,
            "options": options,
            "answer_index": options.index(correct_answer),
            "explanation": item.explanation or item.correct_answer,
            "material_version": MISTAKE_REVIEW_MATERIAL_VERSION,
            "material_ref": cls._text(material.get("material_ref"), 160),
            "format": cls._text(material.get("format"), 64)
            or MISTAKE_REVIEW_FORMATS.get(category, "word_choice"),
            "language": cls._language(material.get("language")),
            "source": source,
            "sentence": cls._text(material.get("sentence"))
            or cls._text(getattr(item, "sentence", None)),
            "audio_text": cls._text(material.get("audio_text"))
            or cls._text(getattr(item, "audio_text", None)),
            "pinyin": cls._text(material.get("pinyin"), 500)
            or cls._text(getattr(item, "pinyin", None), 500),
        }

    @classmethod
    def _review_questions(cls, items: list[CourseMistake]) -> list[tuple[CourseMistake, dict]]:
        category_answers: dict[tuple[str, str, str], list[str]] = {}
        for item in items:
            category = cls._text(getattr(item, "category", None), 24).lower() or "word"
            material = cls._stored_material(item)
            material_format = cls._text(material.get("format"), 64) or MISTAKE_REVIEW_FORMATS.get(
                category, "word_choice"
            )
            language = cls._language(material.get("language"))
            answer = cls._text(getattr(item, "correct_answer", None))
            answers = category_answers.setdefault((category, material_format, language), [])
            if answer and answer not in answers:
                answers.append(answer)

        questions = []
        for item in items:
            category = cls._text(getattr(item, "category", None), 24).lower() or "word"
            material = cls._stored_material(item)
            material_format = cls._text(material.get("format"), 64) or MISTAKE_REVIEW_FORMATS.get(
                category, "word_choice"
            )
            language = cls._language(material.get("language"))
            question = cls._review_question(
                item,
                category_answers.get((category, material_format, language), []),
            )
            if question:
                questions.append((item, question))
        return questions

    @classmethod
    def _review_session_question(cls, question: dict) -> dict:
        """Compact one issued question for the immutable event snapshot.

        Analytics events are capped at 8 KB. The browser only needs these
        render/grading fields on a retry; source metadata remains in
        ``course_mistakes.material_json``.
        """

        options = [cls._text(value, 700) for value in (question.get("options") or [])[:4]]
        return {
            "id": cls._text(question.get("id"), 160),
            "category": cls._text(question.get("category"), 24),
            "prompt": cls._text(question.get("prompt"), 600),
            "options": options,
            "answer_index": int(question.get("answer_index")),
            "explanation": cls._text(question.get("explanation"), 600),
            "sentence": cls._text(question.get("sentence"), 600),
            "audio_text": cls._text(question.get("audio_text"), 600),
            "pinyin": cls._text(question.get("pinyin"), 300),
        }

    @staticmethod
    def _review_started_payload_size(payload: dict) -> int:
        return len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))

    @staticmethod
    def _public_review_question(question: dict) -> dict:
        """Return render fields only; grading data stays in the server snapshot."""

        return {
            key: value
            for key, value in question.items()
            if key not in {"answer_index", "explanation"}
        }

    @staticmethod
    def _legacy_review_question(item: CourseMistake, distractors: list[str]) -> dict:
        """Rebuild an already-issued v1 question exactly for in-flight sessions."""
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

    async def _existing_review_session(self, user, session_id: str) -> dict | None:
        result = await self.session.execute(
            select(CourseMiniAppEvent).where(
                CourseMiniAppEvent.user_id == user.id,
                CourseMiniAppEvent.event_name == "mistake_review_started",
                CourseMiniAppEvent.session_id == session_id,
            )
        )
        event = result.scalar_one_or_none()
        if not event:
            return None
        payload = self._json_dict(getattr(event, "payload_json", None))
        questions = payload.get("questions")
        mistake_ids = payload.get("mistake_ids")
        if not isinstance(questions, list) or not questions or not isinstance(mistake_ids, list):
            return {"ok": False, "error": "invalid_mistake_review_session"}
        return {
            "ok": True,
            "duplicate": True,
            "session": {
                "id": session_id,
                "questions": [self._public_review_question(question) for question in questions],
            },
        }

    async def start_review(
        self,
        telegram_id: int,
        *,
        ad_supported: bool = False,
        access_ref: str = "",
    ) -> dict:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return {"ok": False, "error": "access_start_first"}
        try:
            access_ref = self.access.normalize_access_ref(access_ref)
        except ValueError:
            return {"ok": False, "error": "invalid_access_ref"}
        session_digest = hashlib.sha256(
            f"mistake-review:{user.id}:{access_ref}".encode("utf-8")
        ).hexdigest()[:16]
        session_id = f"mistake-review:{user.id}:v{MISTAKE_REVIEW_VERSION}:{session_digest}"
        existing = await self._existing_review_session(user, session_id)
        if existing:
            return existing
        items = await self._items(user.id, limit=10)
        if not items:
            return {"ok": False, "error": "mistake_review_empty"}
        review_items = self._review_questions(items)
        if not review_items:
            return {"ok": False, "error": "mistake_review_empty"}
        usage_ref = f"mistake-review:v{MISTAKE_REVIEW_VERSION}"
        # Xatolar bo'limi AI token sarflamaydi — reklama bilan davom CHEKSIZ.
        # Bepul: umrbod 1 marta (consume_free_use, lifetime). Bepul tugagach ham
        # ad_supported=True bo'lsa slot band qilinmasdan davom etadi.
        if ad_supported:
            ad_access = await self.access.verify_ad_authorization(
                user,
                feature_key="mistake_review",
                access_ref=access_ref,
            )
            if not ad_access.get("allowed"):
                return {
                    "ok": False,
                    "error": ad_access.get("error") or "ad_authorization_required",
                }
        else:
            access = await self.access.consume_free_use(
                user,
                feature_key="training_test",
                usage_ref=f"{usage_ref}:{access_ref}",
            )
            if not access.get("allowed"):
                return {
                    "ok": False,
                    "error": access.get("error") or "free_feature_limit_reached",
                    # Reklama cheksiz (AI emas) — har doim mavjud.
                    "ad": {"available": True, "limited": False},
                }
        items = [item for item, _ in review_items]
        questions = [question for _, question in review_items]
        question_snapshot = [self._review_session_question(question) for question in questions]
        started_payload = {
            "question_count": len(question_snapshot),
            "mistake_ids": [item.id for item in items],
            "questions": question_snapshot,
            "answer_commit_required": True,
            "access_ref": access_ref,
            "ad_supported": bool(ad_supported),
        }
        # Keep the immutable snapshot intact instead of letting the analytics
        # serializer replace an oversized payload with a truncated preview.
        while (
            len(items) > 1
            and self._review_started_payload_size(started_payload) > MAX_EVENT_PAYLOAD_CHARS - 200
        ):
            items.pop()
            questions.pop()
            question_snapshot.pop()
            started_payload["question_count"] = len(question_snapshot)
            started_payload["mistake_ids"] = [item.id for item in items]
        if self._review_started_payload_size(started_payload) > MAX_EVENT_PAYLOAD_CHARS - 200:
            return {"ok": False, "error": "mistake_review_material_too_large"}
        event = await CourseMiniAppAnalyticsService(self.session).record_server_event(
            event_name="mistake_review_started",
            telegram_id=telegram_id,
            user_id=user.id,
            session_id=session_id,
            dedupe_key=f"{session_id}:started",
            payload=started_payload,
        )
        if not event.get("ok"):
            return {"ok": False, "error": "mistake_review_session_write_failed"}
        if event.get("duplicate"):
            existing = await self._existing_review_session(user, session_id)
            if not existing:
                return {"ok": False, "error": "invalid_mistake_review_session"}
            await self.session.commit()
            return existing
        await self.session.commit()
        return {
            "ok": True,
            "session": {
                "id": session_id,
                "questions": [self._public_review_question(question) for question in questions],
            },
        }

    @classmethod
    def _answer_feedback_from_event(cls, event) -> dict | None:
        payload = cls._json_dict(getattr(event, "payload_json", None))
        try:
            selected_index = int(payload.get("selected_index"))
            correct_index = int(payload.get("correct_index"))
        except (TypeError, ValueError):
            return None
        question_id = cls._text(payload.get("question_id"), 160)
        if not question_id or selected_index < 0 or correct_index < 0:
            return None
        return {
            "ok": True,
            "question_id": question_id,
            "selected_index": selected_index,
            "correct": selected_index == correct_index,
            "correct_index": correct_index,
            "correct_answer": cls._text(payload.get("correct_answer"), 700),
            "explanation": cls._text(payload.get("explanation"), 600),
        }

    async def answer_review_question(
        self,
        telegram_id: int,
        *,
        session_id: str,
        question_id: str,
        selected_index,
    ) -> dict:
        """Commit one choice before revealing its answer and explanation."""

        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return {"ok": False, "error": "access_start_first"}
        expected_prefix = f"mistake-review:{user.id}:v{MISTAKE_REVIEW_VERSION}:"
        if not session_id.startswith(expected_prefix) or len(session_id) > 80:
            return {"ok": False, "error": "invalid_mistake_review_session"}
        question_id = self._text(question_id, 160)
        try:
            selected_index = int(selected_index)
        except (TypeError, ValueError):
            return {"ok": False, "error": "mistake_review_answer_invalid"}

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

        started_payload = self._json_dict(getattr(started, "payload_json", None))
        snapshot = started_payload.get("questions")
        if not isinstance(snapshot, list) or not snapshot:
            return {"ok": False, "error": "invalid_mistake_review_session"}
        question = next(
            (
                raw
                for raw in snapshot
                if isinstance(raw, dict) and self._text(raw.get("id"), 160) == question_id
            ),
            None,
        )
        if not question:
            return {"ok": False, "error": "mistake_review_answer_invalid"}
        options = question.get("options")
        try:
            correct_index = int(question.get("answer_index"))
        except (TypeError, ValueError):
            return {"ok": False, "error": "invalid_mistake_review_session"}
        if (
            not isinstance(options, list)
            or not 0 <= selected_index < len(options)
            or not 0 <= correct_index < len(options)
        ):
            return {"ok": False, "error": "mistake_review_answer_invalid"}

        answer_digest = hashlib.sha256(question_id.encode("utf-8")).hexdigest()[:12]
        dedupe_key = f"{session_id}:answer:{answer_digest}"
        existing_result = await self.session.execute(
            select(CourseMiniAppEvent).where(
                CourseMiniAppEvent.user_id == user.id,
                CourseMiniAppEvent.event_name == "mistake_review_answered",
                CourseMiniAppEvent.session_id == session_id,
                CourseMiniAppEvent.dedupe_key == dedupe_key,
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing:
            feedback = self._answer_feedback_from_event(existing)
            if not feedback:
                return {"ok": False, "error": "invalid_mistake_review_session"}
            return {**feedback, "duplicate": True}

        payload = {
            "question_id": question_id,
            "selected_index": selected_index,
            "correct_index": correct_index,
            "correct_answer": self._text(options[correct_index], 700),
            "explanation": self._text(question.get("explanation"), 600),
        }
        event = await CourseMiniAppAnalyticsService(self.session).record_server_event(
            event_name="mistake_review_answered",
            telegram_id=telegram_id,
            user_id=user.id,
            session_id=session_id,
            dedupe_key=dedupe_key,
            payload=payload,
        )
        if not event.get("ok"):
            return {"ok": False, "error": "mistake_review_answer_write_failed"}
        if event.get("duplicate"):
            retry_result = await self.session.execute(
                select(CourseMiniAppEvent).where(
                    CourseMiniAppEvent.user_id == user.id,
                    CourseMiniAppEvent.event_name == "mistake_review_answered",
                    CourseMiniAppEvent.session_id == session_id,
                    CourseMiniAppEvent.dedupe_key == dedupe_key,
                )
            )
            feedback = self._answer_feedback_from_event(retry_result.scalar_one_or_none())
            if not feedback:
                return {"ok": False, "error": "invalid_mistake_review_session"}
            await self.session.commit()
            return {**feedback, "duplicate": True}

        await self.session.commit()
        return {
            "ok": True,
            "question_id": question_id,
            "selected_index": selected_index,
            "correct": selected_index == correct_index,
            "correct_index": correct_index,
            "correct_answer": payload["correct_answer"],
            "explanation": payload["explanation"],
        }

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
            started_payload = json.loads(started.payload_json or "{}")
            mistake_ids = [int(value) for value in started_payload.get("mistake_ids", [])]
        except (TypeError, ValueError, json.JSONDecodeError):
            started_payload = {}
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
        snapshot = started_payload.get("questions")
        if isinstance(snapshot, list) and snapshot:
            questions = {}
            for raw in snapshot:
                if not isinstance(raw, dict):
                    return {"ok": False, "error": "invalid_mistake_review_session"}
                question_id = str(raw.get("id") or "")
                options = raw.get("options")
                try:
                    answer_index = int(raw.get("answer_index"))
                except (TypeError, ValueError):
                    return {"ok": False, "error": "invalid_mistake_review_session"}
                if (
                    not question_id
                    or question_id in questions
                    or not isinstance(options, list)
                    or not 0 <= answer_index < len(options)
                ):
                    return {"ok": False, "error": "invalid_mistake_review_session"}
                questions[question_id] = {**raw, "answer_index": answer_index}
            if set(questions) != {f"mistake:{item_id}" for item_id in mistake_ids}:
                return {"ok": False, "error": "invalid_mistake_review_session"}
        else:
            # Legacy sessions stored only mistake_ids. Rebuild the already-issued
            # v1 question exactly; new sessions never use this filler/cross-category path.
            distractors = [item.correct_answer for item in items]
            questions = {
                question["id"]: question
                for question in (self._legacy_review_question(item, distractors) for item in items)
            }
        if started_payload.get("answer_commit_required"):
            answered_result = await self.session.execute(
                select(CourseMiniAppEvent).where(
                    CourseMiniAppEvent.user_id == user.id,
                    CourseMiniAppEvent.event_name == "mistake_review_answered",
                    CourseMiniAppEvent.session_id == session_id,
                )
            )
            submitted = {}
            for event in answered_result.scalars().all():
                answer_payload = self._json_dict(getattr(event, "payload_json", None))
                question_id = self._text(answer_payload.get("question_id"), 160)
                try:
                    selected_index = int(answer_payload.get("selected_index"))
                except (TypeError, ValueError):
                    return {"ok": False, "error": "invalid_mistake_review_session"}
                if not question_id or question_id in submitted:
                    return {"ok": False, "error": "invalid_mistake_review_session"}
                submitted[question_id] = {
                    "question_id": question_id,
                    "selected_index": selected_index,
                }
        else:
            # Legacy in-flight clients submitted all answers at completion.
            submitted = {
                str(item.get("question_id") or ""): item
                for item in answers if isinstance(item, dict) and item.get("question_id")
            }
        if not questions or set(submitted) != set(questions):
            return {"ok": False, "error": "mistake_review_answers_incomplete"}

        now = datetime.now(timezone.utc)
        score = 0
        resolved_delta = 0
        reward_eligible_resolved = 0
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
                before = int(item.resolved_count or 0)
                item.resolved_count = min(int(item.wrong_count or 0), before + 1)
                item_resolved_delta = max(0, int(item.resolved_count or 0) - before)
                resolved_delta += item_resolved_delta
                if self._text(getattr(item, "source", None), 32).lower() in TRUSTED_MISTAKE_REWARD_SOURCES:
                    reward_eligible_resolved += item_resolved_delta
            item.last_reviewed_at = now

        total = len(items)
        percent = round((score / total) * 100) if total else 0
        await self.session.flush()
        remaining_result = await self.session.execute(
            select(func.coalesce(func.sum(CourseMistake.wrong_count - CourseMistake.resolved_count), 0)).where(
                CourseMistake.user_id == user.id,
                CourseMistake.wrong_count > CourseMistake.resolved_count,
            )
        )
        remaining = int(remaining_result.scalar_one() or 0)
        if reward_eligible_resolved:
            reward = await self.gamification.award(
                user,
                activity_type="mistake_review",
                activity_ref=f"{session_id}:xp",
                base_xp=5,
                level=getattr(user, "level", None),
            )
        else:
            reward = {"awarded_xp": 0, "duplicate": False}
        event = await CourseMiniAppAnalyticsService(self.session).record_server_event(
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
                "resolved": resolved_delta,
                "reward_eligible_resolved": reward_eligible_resolved,
            },
        )
        if not event.get("ok"):
            return {"ok": False, "error": "mistake_review_result_write_failed"}
        if event.get("duplicate"):
            await self.session.rollback()
            return {"ok": False, "error": "mistake_review_already_completed"}
        await self.session.commit()
        return {
            "ok": True,
            "score": score,
            "total": total,
            "percent": percent,
            "remaining": remaining,
            "reward": reward,
        }
