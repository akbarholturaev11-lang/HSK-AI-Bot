import hashlib
import logging
import unicodedata
import json
import re
from datetime import datetime, timezone
from types import SimpleNamespace

from sqlalchemy import func, or_, select

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
from app.services.course_levels import is_hsk30_level
from app.services.course_mistake_target_store import (
    UNRESOLVABLE_TARGET_KEY,
    CourseMistakeTargetStore,
    aware,
    drill_target,
    split_csv,
)
from app.services import mistake_drill_factory as drills
from app.services.mistake_target_resolver import resolve_target, target_key as make_target_key


logger = logging.getLogger(__name__)

# v3: takror NISHON bo'yicha (so'z/gap), har nishon 3 xil mashqda
# (`mistake_drill_factory`). v1/v2 — savolning o'zini qayta o'ynatardi.
MISTAKE_REVIEW_VERSION = 3
# Answer/complete still accept v1/v2: a learner who was already inside a
# review when the backend deploys must be able to finish it.
MISTAKE_REVIEW_ACCEPTED_VERSIONS = frozenset({1, 2, MISTAKE_REVIEW_VERSION})
# Bitta sessiyada nechta nishon (har biri 3 tagacha mashq bilan).
MISTAKE_REVIEW_TARGETS = 4
MISTAKE_REVIEW_TARGET_CANDIDATES = 40
MISTAKE_REVIEW_MATERIAL_VERSION = 2
MISTAKE_REVIEW_FORMATS = {
    "word": "word_choice",
    "grammar": "grammar_correction",
    "character": "character_choice",
    "pronunciation": "pronunciation_correction",
}
MISTAKE_MATERIAL_LANGUAGES = {"uz", "ru", "tj"}
# Ko'rsatma-matnli savollar: "Tinglang — qaysi so'z?", "Bo'sh joyga mos
# ieroglifni tanlang", "Dialogni to'ldiring". Bunday savol o'z-o'zicha
# javob berib bo'lmaydigan — unga audio yoki gap KERAK. Eski (material'siz)
# xatolarda o'sha kontent yo'q, shuning uchun ular review'ga chiqarilmaydi.
# Faqat BUYRUQ shakllari: "tinglamoq/eshitmoq" kabi infinitivlar mustaqil
# savolning matni bo'lishi mumkin, ular bu ro'yxatga kirmaydi.
MISTAKE_REVIEW_QUESTIONS = 10
MISTAKE_REVIEW_CANDIDATES = 30
MISTAKE_LISTEN_PROMPTS = (
    "tinglang", "eshitganingizni",
    "послушайте", "что вы услышали",
    "гӯш кунед", "шунидед",
)
MISTAKE_FILL_PROMPTS = (
    "to'ldiring", "bo'sh joyga", "dialogni",
    "дополните", "заполните", "подходящий иероглиф", "пропуск",
    "пурра кунед", "мувофиқро интихоб", "ҷойи холӣ",
)

# Faqat aynan qayta ijro qila oladigan interaction formatlari review'ga chiqadi.
# Builder serverda token ketma-ketligi bilan baholanadi; ovoz/matching esa
# alohida interaction renderer bo'lmaguncha generic MCQ ga aylantirilmaydi.
MISTAKE_BUILDER_FORMATS = {
    "sentence_builder",
    "sentence_reorder",
    "word_order",
    "reorder",
    "listen_builder",
}
MISTAKE_UNSUPPORTED_EXACT_FORMATS = {
    "pronunciation_correction",
    "voice_pronunciation",
    "match_pairs",
    "pair_match",
    "matching",
}

# "Ishonchli" = xato SERVERDA aniqlangan, mijozning so'zi bilan emas. Faqat
# shu manbalardagi xatoni tuzatish takrorlash sessiyasiga XP beradi (5 XP,
# sessiyaga bir marta). `pronunciation` — talaffuz balli serverda hisoblanadi
# (VoicePracticeService.score_pronunciation), shuning uchun u ham ishonchli.
TRUSTED_MISTAKE_REWARD_SOURCES = {
    "test",
    "challenge",
    "voice",
    "training",
    "pronunciation",
}


class CourseMistakeService:
    def __init__(self, session):
        self.session = session
        self.user_repo = UserRepository(session)
        self.access = CourseMiniAppAccessService(session)
        self.gamification = CourseGamificationService(session)

    @staticmethod
    def _text(value, limit: int = 2000) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]

    @staticmethod
    def _track_for_level(level: str | None) -> str:
        return "hsk30" if is_hsk30_level(level) else "hsk20"

    @classmethod
    def _scope_target_to_track(cls, target: dict, level: str | None) -> dict:
        scoped = dict(target)
        scoped["level"] = cls._text(level, 32) or scoped.get("level")
        if cls._track_for_level(level) == "hsk30":
            raw = cls._text(scoped.get("key"), 128)
            scoped["key"] = hashlib.sha256(f"hsk30|{raw}".encode("utf-8")).hexdigest()
        return scoped

    @staticmethod
    def _valid_review_session_id(user_id: int, session_id: str) -> bool:
        if len(session_id) > 80:
            return False
        return any(
            session_id.startswith(f"mistake-review:{int(user_id)}:v{version}:")
            for version in MISTAKE_REVIEW_ACCEPTED_VERSIONS
        )

    @classmethod
    def _category(cls, item: dict, source: str) -> str:
        explicit = cls._text(item.get("category"), 24).lower()
        if explicit in COURSE_MISTAKE_CATEGORIES:
            return explicit
        if source == "voice":
            # ORQAGA MOSLIK: AI Voice endi har bir xato uchun `category` ni
            # o'zi beradi (grammar/word/pronunciation). Bu tarmoq faqat
            # error_type joriy qilinishidan OLDIN boshlangan sessiyalar uchun.
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
    def _completed_review_response(cls, event: CourseMiniAppEvent) -> dict:
        """Replay a committed completion without granting rewards twice."""
        payload = cls._json_dict(getattr(event, "payload_json", None))

        def number(key: str) -> int:
            try:
                return max(0, int(payload.get(key) or 0))
            except (TypeError, ValueError):
                return 0

        return {
            "ok": True,
            "duplicate": True,
            "score": number("score"),
            "total": number("total"),
            "percent": number("percent"),
            "remaining": number("remaining"),
            "cleared": number("cleared"),
            "reward": {"awarded_xp": 0, "duplicate": True},
        }

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
    def _material_key(
        cls,
        category: str,
        material: dict,
        prompt: str,
        correct_answer: str,
        *,
        level: str | None = None,
    ) -> str:
        material_ref = cls._text(material.get("material_ref"), 160)
        if material_ref:
            normalized = f"{category}|material:{material_ref}".casefold()
        else:
            normalized = f"{category}|{prompt}|{correct_answer}".casefold()
        if cls._track_for_level(level) == "hsk30":
            normalized = f"hsk30|{normalized}"
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

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
        record_level = self._text(level or getattr(user, "level", None), 32) or None
        record_track = self._track_for_level(record_level)
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
                level=record_level,
                lesson_order=lesson_order,
                prompt=prompt,
                correct_answer=correct_answer,
                explanation=explanation,
                user_language=getattr(user, "language", None),
            )
            normalized.append(
                {
                    "mistake_key": self._material_key(
                        category,
                        material,
                        prompt,
                        correct_answer,
                        level=record_level,
                    ),
                    "legacy_mistake_key": self._key(category, prompt, correct_answer),
                    "track": record_track,
                    "category": category,
                    "prompt": prompt,
                    "user_answer": self._text(raw.get("selected_answer") or raw.get("user_answer")) or None,
                    "correct_answer": correct_answer,
                    "explanation": explanation,
                    "material_json": json.dumps(material, ensure_ascii=False, separators=(",", ":")),
                    "material": material,
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
            if (
                not mistake
                and data["track"] == "hsk20"
                and data["legacy_mistake_key"] != data["mistake_key"]
            ):
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
                mistake.level = record_level or mistake.level
                mistake.lesson_id = lesson_id or mistake.lesson_id
                mistake.lesson_order = lesson_order or mistake.lesson_order
                mistake.last_seen_at = now
            else:
                mistake = CourseMistake(
                    user_id=user.id,
                    lesson_id=lesson_id,
                    mistake_key=data["mistake_key"],
                    category=data["category"],
                    source=normalized_source,
                    level=record_level,
                    lesson_order=lesson_order,
                    prompt=data["prompt"],
                    user_answer=data["user_answer"],
                    correct_answer=data["correct_answer"],
                    explanation=data["explanation"],
                    material_json=data["material_json"],
                    first_seen_at=now,
                    last_seen_at=now,
                )
                self.session.add(mistake)
            await self._link_target(
                user.id,
                mistake,
                material=data["material"],
                source=normalized_source,
                now=now,
            )
            recorded += 1
        await self.session.flush()
        return recorded

    # ------------------------------------------------------------ nishon ---

    @property
    def targets(self) -> CourseMistakeTargetStore:
        store = getattr(self, "_target_store", None)
        if store is None:
            store = CourseMistakeTargetStore(self.session)
            self._target_store = store
        return store

    @classmethod
    def _resolve_row_target(cls, row, material: dict) -> dict | None:
        """Xato qatoridan nishon; topilmasa eski savolning o'zi (`question`)."""
        category = cls._text(getattr(row, "category", None), 24).lower() or "word"
        try:
            target = resolve_target(
                category=category,
                source=cls._text(getattr(row, "source", None), 32),
                material=material,
                prompt=cls._text(getattr(row, "prompt", None)),
                correct_answer=cls._text(getattr(row, "correct_answer", None)),
                user_answer=cls._text(getattr(row, "user_answer", None)),
                explanation=cls._text(getattr(row, "explanation", None)),
                level=getattr(row, "level", None),
                language=material.get("language"),
            )
        except Exception:  # noqa: BLE001 — nishon topilmasa ham xato yozuvi saqlanadi
            logger.exception("Mistake target resolution failed")
            target = None
        if target:
            return cls._scope_target_to_track(
                target,
                getattr(row, "level", None),
            )
        probe = SimpleNamespace(
            id=0,
            category=category,
            source=getattr(row, "source", None),
            level=getattr(row, "level", None),
            lesson_order=getattr(row, "lesson_order", None),
            prompt=getattr(row, "prompt", None) or "",
            user_answer=getattr(row, "user_answer", None),
            correct_answer=getattr(row, "correct_answer", None) or "",
            explanation=getattr(row, "explanation", None),
            material_json=json.dumps(material, ensure_ascii=False) if material else None,
        )
        question = cls._review_question(probe, [])
        if not question:
            return None
        stored = {
            key: question.get(key)
            for key in (
                "prompt", "format", "sentence", "audio_text", "pinyin", "options",
                "answer_index", "tokens", "answer_tokens", "correct_answer", "explanation",
            )
            if question.get(key) not in (None, "", [])
        }
        if "answer_index" in question:
            stored["answer_index"] = question["answer_index"]
        ref = cls._text(material.get("material_ref"), 160) or cls._text(getattr(row, "mistake_key", None), 64)
        return cls._scope_target_to_track(
            {
                "kind": "question",
                "zh": cls._text(question.get("prompt"), 300),
                "key": make_target_key(
                    "question",
                    ref or cls._text(getattr(row, "prompt", None)),
                ),
                "level": getattr(row, "level", None),
                "payload": {"question": stored},
            },
            getattr(row, "level", None),
        )

    async def _link_target(self, user_id: int, row, *, material: dict, source: str, now) -> None:
        """Yangi xatoni nishonga bog'laydi (yangi xato progressni nolga tushiradi)."""
        target = self._resolve_row_target(row, material or {})
        if not target:
            row.target_key = UNRESOLVABLE_TARGET_KEY
            return
        await self.targets.upsert(
            user_id,
            category=row.category,
            target=target,
            source=source,
            now=now,
        )
        row.target_key = target["key"]

    async def _sync_targets(self, user) -> bool:
        """Nishonga bog'lanmagan eski faol xatolarni bog'laydi (lazy backfill)."""
        track = self._track_for_level(getattr(user, "level", None))
        rows = await self.targets.unsynced_rows(user.id, track=track)
        if not rows:
            return False
        await self.session.execute(select(User.id).where(User.id == user.id).with_for_update())
        now = datetime.now(timezone.utc)
        for row in rows:
            target = self._resolve_row_target(row, self._stored_material(row))
            if not target:
                row.target_key = UNRESOLVABLE_TARGET_KEY
                continue
            existing = await self.targets.get(user.id, row.category, target["key"])
            if (
                existing is not None
                and existing.status == "cleared"
                and existing.cleared_at is not None
                and aware(row.last_seen_at) <= aware(existing.cleared_at)
            ):
                # Nishon bu xatodan KEYIN yopilgan — qator ham yopiladi.
                row.target_key = target["key"]
                row.resolved_count = row.wrong_count
                continue
            await self.targets.upsert(
                user.id,
                category=row.category,
                target=target,
                source=self._text(row.source, 32),
                now=now,
                weight=self._weakness(row),
                seen_at=row.last_seen_at,
                new_mistake=existing is not None and existing.status == "cleared",
            )
            row.target_key = target["key"]
        await self.session.flush()
        return True

    async def _items(
        self,
        user_id: int,
        limit: int = 50,
        *,
        category: str | None = None,
        offset: int = 0,
        track: str | None = None,
    ) -> list[CourseMistake]:
        weakness = CourseMistake.wrong_count - CourseMistake.resolved_count
        query = (
            select(CourseMistake)
            .where(CourseMistake.user_id == user_id, weakness > 0)
            .order_by(weakness.desc(), CourseMistake.last_seen_at.desc())
        )
        if category in COURSE_MISTAKE_CATEGORIES:
            query = query.where(CourseMistake.category == category)
        if track == "hsk30":
            query = query.where(CourseMistake.level.like("nhsk%"))
        elif track == "hsk20":
            query = query.where(
                or_(CourseMistake.level.is_(None), ~CourseMistake.level.like("nhsk%"))
            )
        result = await self.session.execute(query.offset(max(0, int(offset or 0))).limit(max(1, int(limit or 1))))
        return list(result.scalars().all())

    @staticmethod
    def _review_language(user, language: str | None = None) -> str:
        for value in (language, getattr(user, "language", None)):
            normalized = str(value or "").strip().lower()
            if normalized in {"tg", "tg-cyrl"}:
                normalized = "tj"
            if normalized in MISTAKE_MATERIAL_LANGUAGES:
                return normalized
        return "uz"

    async def _target_overview(
        self,
        user,
        *,
        category: str | None,
        limit: int,
        offset: int,
        language: str,
    ) -> tuple[list[dict], bool]:
        track = self._track_for_level(getattr(user, "level", None))
        rows = await self.targets.active(
            user.id,
            category=category,
            limit=limit + 1,
            offset=offset,
            track=track,
        )
        has_more = len(rows) > limit
        rows = rows[:limit]
        last_answers: dict[tuple[str, str], str] = {}
        keys = [row.target_key for row in rows]
        if keys:
            result = await self.session.execute(
                select(CourseMistake.category, CourseMistake.target_key, CourseMistake.user_answer)
                .where(CourseMistake.user_id == user.id, CourseMistake.target_key.in_(keys))
                .order_by(CourseMistake.last_seen_at.desc(), CourseMistake.id.desc())
            )
            for row_category, row_key, user_answer in result.all():
                text = self._text(user_answer, 300)
                if text:
                    last_answers.setdefault((str(row_category), str(row_key)), text)
        items = []
        for row in rows:
            target = drill_target(row)
            payload = target["payload"]
            available = drills.available_questions(
                target, language=language, seed="overview", client_formats=drills.ALL_FORMATS
            )
            required = min(drills.REQUIRED_FORMATS, len(available)) or 1
            passed = min(len(split_csv(row.passed_formats)), required)
            item = {
                "id": int(row.id),
                "category": row.category,
                "kind": row.kind,
                "zh": row.zh,
                "pinyin": self._text(payload.get("pinyin"), 300),
                "meaning": self._text((payload.get("meaning") or {}).get(language), 300),
                "translation": self._text((payload.get("translation") or {}).get(language), 400),
                "wrong": self._text(
                    ((payload.get("wrong") or [None])[-1])
                    or last_answers.get((row.category, row.target_key)),
                    300,
                ),
                "passed": passed,
                "required": required,
                "count": int(row.wrong_count or 0),
                "level": row.level,
                "sources": split_csv(row.sources),
            }
            if row.kind == "question":
                question = payload.get("question") or {}
                options = question.get("options") or []
                answer_index = question.get("answer_index")
                answer = self._text(question.get("correct_answer"))
                if not answer and isinstance(answer_index, int) and 0 <= answer_index < len(options):
                    answer = self._text(options[answer_index])
                item.update(
                    {
                        "zh": self._text(question.get("sentence")) or row.zh,
                        "question": self._text(question.get("prompt")),
                        "answer": answer,
                    }
                )
            items.append(item)
        return items, has_more

    async def overview(
        self,
        telegram_id: int,
        *,
        category: str | None = None,
        limit: int = 50,
        offset: int = 0,
        view: str | None = None,
        language: str | None = None,
    ) -> dict:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return {"ok": False, "error": "access_start_first"}
        track = self._track_for_level(getattr(user, "level", None))
        category = self._text(category, 24).lower() or None
        if category and category not in COURSE_MISTAKE_CATEGORIES:
            return {"ok": False, "error": "invalid_mistake_category"}
        try:
            limit = max(1, min(100, int(limit)))
            offset = max(0, min(100000, int(offset)))
        except (TypeError, ValueError):
            return {"ok": False, "error": "invalid_mistake_pagination"}
        view = self._text(view, 16).lower()
        if view == "targets":
            try:
                if await self._sync_targets(user):
                    await self.session.commit()
            except Exception:  # noqa: BLE001 — backfill ro'yxatni yiqitmasin
                logger.exception("Mistake target sync failed for user %s", user.id)
                await self.session.rollback()
            target_counts = await self.targets.counts(user.id, track=track)
            language = self._review_language(user, language)
            targets, has_more = await self._target_overview(
                user, category=category, limit=limit, offset=offset, language=language
            )
            return {
                "ok": True,
                "summary": {
                    "total": sum(target_counts.values()),
                    "categories": target_counts,
                    "unit": "targets",
                },
                "filter": {"category": category},
                "pagination": {
                    "offset": offset,
                    "limit": limit,
                    "returned": len(targets),
                    "has_more": has_more,
                },
                "targets": targets,
                "items": [],
            }
        page_items = await self._items(
            user.id,
            limit=limit + 1,
            category=category,
            offset=offset,
            track=track,
        )
        has_more = len(page_items) > limit
        items = page_items[:limit]
        counts_query = select(
            CourseMistake.category,
            func.sum(CourseMistake.wrong_count - CourseMistake.resolved_count),
        ).where(
            CourseMistake.user_id == user.id,
            CourseMistake.wrong_count > CourseMistake.resolved_count,
        )
        if track == "hsk30":
            counts_query = counts_query.where(CourseMistake.level.like("nhsk%"))
        else:
            counts_query = counts_query.where(
                or_(CourseMistake.level.is_(None), ~CourseMistake.level.like("nhsk%"))
            )
        counts_result = await self.session.execute(
            counts_query.group_by(CourseMistake.category)
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

    @staticmethod
    def _answer_key(value: str) -> str:
        """Ikki javob KO'RINISHDA bir xilmi.

        Bosh harf, ortiqcha bo'shliq va tinish belgilari e'tiborga olinmaydi:
        ekranda "Салом ..." va "салом ..." bitta variant, ikkita emas.
        """

        text = unicodedata.normalize("NFKC", str(value or "")).casefold()
        text = re.sub(r"[\s\u00a0]+", " ", text)
        text = re.sub(r"[.,;:!?()\[\]{}«»\"'’`\-—–/\\]", "", text)
        return text.strip()

    @classmethod
    def _review_question(cls, item: CourseMistake, category_answers: list[str]) -> dict | None:
        material = cls._stored_material(item)
        correct_answer = cls._text(item.correct_answer)
        user_answer = cls._text(item.user_answer)
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
        prompt_text = cls._text(material.get("prompt")) or item.prompt or ""
        material_format = cls._text(material.get("format"), 64) or MISTAKE_REVIEW_FORMATS.get(
            category, "word_choice"
        )
        sentence = cls._text(material.get("sentence"))
        audio_text = cls._text(material.get("audio_text"))
        pinyin = cls._text(material.get("pinyin"), 500)

        if cls._answer_key(prompt_text) == cls._answer_key(correct_answer):
            return None
        if material_format in MISTAKE_UNSUPPORTED_EXACT_FORMATS:
            # Interactionni aynan qaytara olmaymiz. Generic MCQ yasash
            # foydalanuvchiga boshqa mashq ko'rsatadi, shuning uchun skip.
            return None

        low_prompt = prompt_text.casefold()
        needs_listen = material_format == "listening_choice" or any(
            key in low_prompt for key in MISTAKE_LISTEN_PROMPTS
        )
        needs_fill = material_format in {"gap_fill", "dialog_cloze", "dialog_context"} or any(
            key in low_prompt for key in MISTAKE_FILL_PROMPTS
        )
        if needs_listen and not audio_text:
            return None
        if needs_fill and not sentence and not audio_text:
            return None
        if needs_listen:
            pinyin = ""
        if (
            material_format == "listening_choice"
            and sentence
            and cls._answer_key(sentence) == cls._answer_key(audio_text)
        ):
            # Eski mashq/bellashuv xatolarida `sentence` = `audio_text`, ya'ni
            # to'g'ri javob yozilgan. `audio_truefalse` bu yerga kirmaydi: u
            # yerda yozilgan gap savolning o'zi.
            sentence = ""

        if material_format in MISTAKE_BUILDER_FORMATS:
            tokens = [
                cls._text(value, 200)
                for value in (material.get("tokens") or [])[:30]
                if cls._text(value, 200)
            ]
            answer_tokens = [
                cls._text(value, 200)
                for value in (material.get("answer_tokens") or [])[:30]
                if cls._text(value, 200)
            ]
            if (
                len(tokens) < 2
                or len(tokens) != len(answer_tokens)
                or sorted(tokens) != sorted(answer_tokens)
            ):
                return None
            # Builderda to'g'ri gapni material sifatida oldindan ko'rsatish
            # javobni ochib beradi. Context boshqa bo'lsa saqlanadi.
            joined_answer = "".join(answer_tokens)
            if sentence and cls._answer_key(sentence) in {
                cls._answer_key(joined_answer),
                cls._answer_key(correct_answer),
            }:
                sentence = ""
            return {
                "id": f"mistake:{item.id}",
                "category": category,
                "prompt": prompt_text,
                "options": [],
                "explanation": item.explanation or item.correct_answer,
                "material_version": MISTAKE_REVIEW_MATERIAL_VERSION,
                "material_ref": cls._text(material.get("material_ref"), 160),
                "format": material_format,
                "language": cls._language(material.get("language")),
                "source": source,
                "sentence": sentence,
                "audio_text": audio_text,
                "pinyin": pinyin,
                "tokens": tokens,
                "answer_tokens": answer_tokens,
                "correct_answer": correct_answer or joined_answer,
            }

        material_options = material.get("options") if isinstance(material.get("options"), list) else []
        seen: set[str] = set()
        options: list[str] = []

        def take(value) -> None:
            text = cls._text(value)
            if not text:
                return
            key = cls._answer_key(text)
            if not key or key in seen:
                return
            seen.add(key)
            options.append(text)

        take(correct_answer)
        for value in (user_answer, *material_options, *category_answers):
            take(value)
        options = options[:4]
        if len(options) < 2:
            return None
        # Savol matni variantlardan biriga teng bo'lsa (AI Voice: savol ham,
        # "sizning javobingiz" ham o'quvchining o'z gapi) — bu savol emas.
        prompt_key = cls._answer_key(prompt_text)
        if any(cls._answer_key(option) == prompt_key for option in options):
            return None
        if needs_listen and sentence and cls._answer_key(correct_answer) in cls._answer_key(sentence):
            # Tinglash savolida ekrandagi gap javobni ochib qo'ymasin.
            sentence = ""
        options.sort(
            key=lambda value: hashlib.sha256(
                f"mistake-review:{item.id}:{value}".encode("utf-8")
            ).digest()
        )

        return {
            "id": f"mistake:{item.id}",
            "category": category,
            "prompt": prompt_text,
            "options": options,
            "answer_index": options.index(correct_answer),
            "explanation": item.explanation or item.correct_answer,
            "material_version": MISTAKE_REVIEW_MATERIAL_VERSION,
            "material_ref": cls._text(material.get("material_ref"), 160),
            "format": material_format,
            "language": cls._language(material.get("language")),
            "source": source,
            "sentence": sentence,
            "audio_text": audio_text,
            "pinyin": pinyin,
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
        """Compact one issued question for the immutable event snapshot."""

        material_format = cls._text(question.get("format"), 64)
        base = {
            "id": cls._text(question.get("id"), 160),
            "category": cls._text(question.get("category"), 24),
            "prompt": cls._text(question.get("prompt"), 600),
            "explanation": cls._text(question.get("explanation"), 600),
            "material_version": int(
                question.get("material_version") or MISTAKE_REVIEW_MATERIAL_VERSION
            ),
            "material_ref": cls._text(question.get("material_ref"), 160),
            "format": material_format,
            "language": cls._language(question.get("language")),
            "sentence": cls._text(question.get("sentence"), 600),
            "audio_text": cls._text(question.get("audio_text"), 600),
            "pinyin": cls._text(question.get("pinyin"), 300),
        }
        if material_format in MISTAKE_BUILDER_FORMATS:
            base.update(
                {
                    "options": [],
                    "tokens": [
                        cls._text(value, 200)
                        for value in (question.get("tokens") or [])[:30]
                        if cls._text(value, 200)
                    ],
                    "answer_tokens": [
                        cls._text(value, 200)
                        for value in (question.get("answer_tokens") or [])[:30]
                        if cls._text(value, 200)
                    ],
                    "correct_answer": cls._text(question.get("correct_answer"), 700),
                }
            )
            return base
        options = [cls._text(value, 700) for value in (question.get("options") or [])[:4]]
        base.update(
            {
                "options": options,
                "answer_index": int(question.get("answer_index")),
            }
        )
        return base

    @staticmethod
    def _review_started_payload_size(payload: dict) -> int:
        return len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))

    @staticmethod
    def _public_review_question(question: dict) -> dict:
        """Return render fields only; grading data stays in the server snapshot."""

        return {
            key: value
            for key, value in question.items()
            if key not in {"answer_index", "answer_tokens", "correct_answer", "explanation"}
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
        if not isinstance(questions, list) or not questions:
            return {"ok": False, "error": "invalid_mistake_review_session"}
        if int(payload.get("version") or 0) == MISTAKE_REVIEW_VERSION:
            return {
                "ok": True,
                "duplicate": True,
                "session": {
                    "id": session_id,
                    "version": MISTAKE_REVIEW_VERSION,
                    "category": payload.get("category") or "all",
                    "targets": len(payload.get("target_ids") or []),
                    "questions": [drills.public_question(question) for question in questions],
                },
            }
        if not isinstance(payload.get("mistake_ids"), list):
            return {"ok": False, "error": "invalid_mistake_review_session"}
        return {
            "ok": True,
            "duplicate": True,
            "session": {
                "id": session_id,
                "questions": [self._public_review_question(question) for question in questions],
            },
        }

    @classmethod
    def _client_formats(cls, formats) -> frozenset:
        """Klient ko'rsata oladigan mashq turlari. Ro'yxat yo'q — eski klient."""
        if not isinstance(formats, (list, tuple)):
            return drills.LEGACY_CLIENT_FORMATS
        declared = frozenset(cls._text(value, 40) for value in formats[:40]) & drills.ALL_FORMATS
        return declared or drills.LEGACY_CLIENT_FORMATS

    @classmethod
    def _review_v3_snapshot_question(cls, question: dict) -> dict:
        """Sessiya snapshot'i uchun ixcham savol (baholash maydonlari bilan)."""
        base = {
            "id": cls._text(question.get("id"), 160),
            "target_id": int(question.get("target_id") or 0),
            "category": cls._text(question.get("category"), 24),
            "format": cls._text(question.get("format"), 64),
            "language": cls._language(question.get("language")),
            "prompt": cls._text(question.get("prompt"), 600),
            "sentence": cls._text(question.get("sentence"), 600),
            "pinyin": cls._text(question.get("pinyin"), 300),
            "audio_text": cls._text(question.get("audio_text"), 240),
            "explanation": cls._text(question.get("explanation"), 600),
            "material_version": int(question.get("material_version") or drills.DRILL_MATERIAL_VERSION),
        }
        if question.get("replay_format"):
            base["replay_format"] = cls._text(question.get("replay_format"), 64)
        tokens = question.get("tokens")
        if isinstance(tokens, list) and tokens:
            base.update(
                {
                    "options": [],
                    "tokens": [cls._text(value, 200) for value in tokens[:30]],
                    "answer_tokens": [cls._text(value, 200) for value in (question.get("answer_tokens") or [])[:30]],
                    "correct_answer": cls._text(question.get("correct_answer"), 700),
                }
            )
            return base
        base.update(
            {
                "options": [cls._text(value, 300) for value in (question.get("options") or [])[:6]],
                "answer_index": int(question.get("answer_index")),
            }
        )
        return base

    @staticmethod
    def _interleave(plans: list[tuple]) -> list[dict]:
        """Bitta nishonning mashqlari ketma-ket kelmasin: t1f1, t2f1, ..., t1f2, ..."""
        ordered = []
        depth = max((len(questions) for _, questions, _ in plans), default=0)
        for index in range(depth):
            for _, questions, _ in plans:
                if index < len(questions):
                    ordered.append(questions[index])
        return ordered

    async def start_review(
        self,
        telegram_id: int,
        *,
        ad_supported: bool = False,
        access_ref: str = "",
        category: str | None = None,
        formats=None,
        language: str | None = None,
    ) -> dict:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return {"ok": False, "error": "access_start_first"}
        try:
            access_ref = self.access.normalize_access_ref(access_ref)
        except ValueError:
            return {"ok": False, "error": "invalid_access_ref"}
        category = self._text(category, 24).lower() or None
        if category == "all":
            category = None
        if category and category not in COURSE_MISTAKE_CATEGORIES:
            return {"ok": False, "error": "invalid_mistake_category"}
        scope = category or "all"
        client_formats = self._client_formats(formats)
        session_digest = hashlib.sha256(
            f"mistake-review:{user.id}:{access_ref}:{scope}".encode("utf-8")
        ).hexdigest()[:16]
        session_id = f"mistake-review:{user.id}:v{MISTAKE_REVIEW_VERSION}:{session_digest}"
        existing = await self._existing_review_session(user, session_id)
        if existing:
            return existing
        language = self._review_language(user, language)
        try:
            await self._sync_targets(user)
        except Exception:  # noqa: BLE001 — backfill takrorni yiqitmasin
            logger.exception("Mistake target sync failed for user %s", user.id)
            await self.session.rollback()

        # Nomzodlar ko'p olinadi: ba'zi nishon shu klientda savol bera olmasligi
        # mumkin (masalan eski klient builder'ni ko'rsata olmaydi).
        track = self._track_for_level(getattr(user, "level", None))
        rows = await self.targets.active(
            user.id,
            category=category,
            limit=MISTAKE_REVIEW_TARGET_CANDIDATES,
            track=track,
        )
        plans = []
        for row in rows:
            questions, required = drills.plan_target(
                drill_target(row),
                language=language,
                seed=session_id,
                client_formats=client_formats,
                passed=set(split_csv(row.passed_formats)),
            )
            if questions:
                plans.append((row, questions, required))
            if len(plans) >= MISTAKE_REVIEW_TARGETS:
                break
        if not plans:
            await self.session.commit()
            return {"ok": False, "error": "mistake_review_empty", "category": scope}

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
                await self.session.commit()
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
                await self.session.commit()
                return {
                    "ok": False,
                    "error": access.get("error") or "free_feature_limit_reached",
                    # Reklama cheksiz (AI emas) — har doim mavjud.
                    "ad": {"available": True, "limited": False},
                }

        questions = self._interleave(plans)
        snapshot = [self._review_v3_snapshot_question(question) for question in questions]
        required = {str(int(row.id)): int(need) for row, _, need in plans}

        def payload_for(items: list[dict]) -> dict:
            target_ids = []
            for item in items:
                if item["target_id"] not in target_ids:
                    target_ids.append(item["target_id"])
            return {
                "version": MISTAKE_REVIEW_VERSION,
                "question_count": len(items),
                "target_ids": target_ids,
                "required": {key: value for key, value in required.items() if int(key) in target_ids},
                "questions": items,
                "answer_commit_required": True,
                "access_ref": access_ref,
                "ad_supported": bool(ad_supported),
                "category": scope,
                "language": language,
            }

        started_payload = payload_for(snapshot)
        # Snapshot butun qolishi shart (analitika katta payload'ni kesib qo'yardi).
        while (
            len(snapshot) > 1
            and self._review_started_payload_size(started_payload) > MAX_EVENT_PAYLOAD_CHARS - 200
        ):
            snapshot.pop()
            started_payload = payload_for(snapshot)
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
                "version": MISTAKE_REVIEW_VERSION,
                "category": scope,
                "targets": len(started_payload["target_ids"]),
                "questions": [drills.public_question(question) for question in snapshot],
            },
        }

    @classmethod
    def _answer_feedback_from_event(cls, event) -> dict | None:
        payload = cls._json_dict(getattr(event, "payload_json", None))
        question_id = cls._text(payload.get("question_id"), 160)
        if not question_id:
            return None
        if payload.get("answer_type") == "tokens":
            selected_tokens = payload.get("selected_tokens")
            if not isinstance(selected_tokens, list):
                return None
            selected_tokens = [cls._text(value, 200) for value in selected_tokens]
            if not selected_tokens or any(not value for value in selected_tokens):
                return None
            return {
                "ok": True,
                "question_id": question_id,
                "selected_tokens": selected_tokens,
                "correct": payload.get("correct") is True,
                "correct_answer": cls._text(payload.get("correct_answer"), 700),
                "explanation": cls._text(payload.get("explanation"), 600),
            }
        try:
            selected_index = int(payload.get("selected_index"))
            correct_index = int(payload.get("correct_index"))
        except (TypeError, ValueError):
            return None
        if selected_index < 0 or correct_index < 0:
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
        """Commit one exact interaction answer before revealing feedback."""

        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return {"ok": False, "error": "access_start_first"}
        if not self._valid_review_session_id(user.id, session_id):
            return {"ok": False, "error": "invalid_mistake_review_session"}
        question_id = self._text(question_id, 160)
        raw_answer = selected_index

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

        material_format = self._text(question.get("format"), 64)
        if material_format in MISTAKE_BUILDER_FORMATS:
            if not isinstance(raw_answer, list):
                return {"ok": False, "error": "mistake_review_answer_invalid"}
            selected_tokens = [self._text(value, 200) for value in raw_answer[:30]]
            tokens = [self._text(value, 200) for value in (question.get("tokens") or [])[:30]]
            answer_tokens = [
                self._text(value, 200) for value in (question.get("answer_tokens") or [])[:30]
            ]
            if (
                not selected_tokens
                or any(not value for value in selected_tokens)
                or len(selected_tokens) != len(tokens)
                or len(answer_tokens) != len(tokens)
                or sorted(selected_tokens) != sorted(tokens)
                or sorted(answer_tokens) != sorted(tokens)
            ):
                return {"ok": False, "error": "mistake_review_answer_invalid"}
            correct = selected_tokens == answer_tokens
            answer_payload = {
                "question_id": question_id,
                "answer_type": "tokens",
                "selected_tokens": selected_tokens,
                "correct": correct,
                "correct_answer": self._text(question.get("correct_answer"), 700)
                or "".join(answer_tokens),
                "explanation": self._text(question.get("explanation"), 600),
            }
        else:
            options = question.get("options")
            try:
                selected_value = int(raw_answer)
                correct_index = int(question.get("answer_index"))
            except (TypeError, ValueError):
                return {"ok": False, "error": "mistake_review_answer_invalid"}
            if (
                not isinstance(options, list)
                or not 0 <= selected_value < len(options)
                or not 0 <= correct_index < len(options)
            ):
                return {"ok": False, "error": "mistake_review_answer_invalid"}
            answer_payload = {
                "question_id": question_id,
                "selected_index": selected_value,
                "correct_index": correct_index,
                "correct_answer": self._text(options[correct_index], 700),
                "explanation": self._text(question.get("explanation"), 600),
            }

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

        event = await CourseMiniAppAnalyticsService(self.session).record_server_event(
            event_name="mistake_review_answered",
            telegram_id=telegram_id,
            user_id=user.id,
            session_id=session_id,
            dedupe_key=dedupe_key,
            payload=answer_payload,
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
        if answer_payload.get("answer_type") == "tokens":
            return {
                "ok": True,
                "question_id": question_id,
                "selected_tokens": answer_payload["selected_tokens"],
                "correct": bool(answer_payload["correct"]),
                "correct_answer": answer_payload["correct_answer"],
                "explanation": answer_payload["explanation"],
            }
        return {
            "ok": True,
            "question_id": question_id,
            "selected_index": answer_payload["selected_index"],
            "correct": answer_payload["selected_index"] == answer_payload["correct_index"],
            "correct_index": answer_payload["correct_index"],
            "correct_answer": answer_payload["correct_answer"],
            "explanation": answer_payload["explanation"],
        }

    async def _v3_submitted(self, user, session_id: str, questions: dict[str, dict]) -> dict | None:
        """Serverga Tekshirish'da yozilgan javoblar (savol id -> tanlov)."""
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
            if not question_id or question_id in submitted or question_id not in questions:
                return None
            if answer_payload.get("answer_type") == "tokens":
                selected = answer_payload.get("selected_tokens")
                if not isinstance(selected, list):
                    return None
                submitted[question_id] = [self._text(value, 200) for value in selected]
            else:
                try:
                    submitted[question_id] = int(answer_payload.get("selected_index"))
                except (TypeError, ValueError):
                    return None
        return submitted

    async def _hand_off_to_word_mastery(self, user, rows: list) -> None:
        """Yopilgan so'z interval takroriga o'tadi (1 -> 3 -> 7 -> 21 kun).

        SAVEPOINT ichida: bu yozuv muvaffaqiyatsiz bo'lsa ham takror natijasi saqlanadi.
        """
        words = [row for row in rows if row.kind == "word"]
        if not words or not hasattr(self.session, "begin_nested"):
            return
        from app.services.course_word_mastery_service import CourseWordMasteryService

        try:
            async with self.session.begin_nested():
                service = CourseWordMasteryService(self.session)
                for skill, group in (
                    ("pronunciation", [row for row in words if row.category == "pronunciation"]),
                    ("recognition", [row for row in words if row.category != "pronunciation"]),
                ):
                    if group:
                        await service.record_drill(
                            user,
                            skill=skill,
                            results=[{"hanzi": row.zh, "correct": True} for row in group],
                        )
        except Exception:  # noqa: BLE001
            logger.exception("Word mastery hand-off failed for user %s", getattr(user, "id", None))

    async def _complete_review_v3(self, user, telegram_id: int, session_id: str, started_payload: dict) -> dict:
        snapshot = started_payload.get("questions")
        if not isinstance(snapshot, list) or not snapshot:
            return {"ok": False, "error": "invalid_mistake_review_session"}
        questions: dict[str, dict] = {}
        for raw in snapshot:
            if not isinstance(raw, dict):
                return {"ok": False, "error": "invalid_mistake_review_session"}
            question_id = self._text(raw.get("id"), 160)
            if not question_id or question_id in questions:
                return {"ok": False, "error": "invalid_mistake_review_session"}
            questions[question_id] = raw
        submitted = await self._v3_submitted(user, session_id, questions)
        if submitted is None:
            return {"ok": False, "error": "invalid_mistake_review_session"}
        if set(submitted) != set(questions):
            return {"ok": False, "error": "mistake_review_answers_incomplete"}

        try:
            target_ids = [int(value) for value in started_payload.get("target_ids") or []]
        except (TypeError, ValueError):
            return {"ok": False, "error": "invalid_mistake_review_session"}
        required = started_payload.get("required") if isinstance(started_payload.get("required"), dict) else {}
        rows = await self.targets.by_ids(user.id, target_ids, lock=True)
        now = datetime.now(timezone.utc)
        progress = {target_id: set(split_csv(row.passed_formats)) for target_id, row in rows.items()}
        answered_correct: set[int] = set()
        score = 0
        for raw in snapshot:
            question_id = self._text(raw.get("id"), 160)
            selected = submitted[question_id]
            if isinstance(raw.get("tokens"), list) and raw.get("tokens"):
                correct = isinstance(selected, list) and selected == [
                    self._text(value, 200) for value in raw.get("answer_tokens") or []
                ]
            else:
                try:
                    correct = int(selected) == int(raw.get("answer_index"))
                except (TypeError, ValueError):
                    correct = False
            score += int(correct)
            try:
                target_id = int(raw.get("target_id"))
            except (TypeError, ValueError):
                continue
            row = rows.get(target_id)
            if row is None:
                continue
            row.review_count = int(row.review_count or 0) + 1
            row.last_reviewed_at = now
            format_key = "replay" if raw.get("replay_format") else self._text(raw.get("format"), 64)
            if correct:
                progress[target_id].add(format_key)
                answered_correct.add(target_id)
            else:
                # Xato — progress nolga: nishon keyingi sessiyada qaytadi.
                progress[target_id].clear()

        cleared = []
        for target_id, row in rows.items():
            need = max(1, int(required.get(str(target_id)) or drills.REQUIRED_FORMATS))
            passed = progress.get(target_id, set())
            if row.status == "active" and len(passed) >= need:
                row.status = "cleared"
                row.cleared_at = now
                row.cleared_count = int(row.cleared_count or 0) + 1
                row.passed_formats = ""
                await self.targets.resolve_rows(row, now)
                cleared.append(row)
            else:
                row.passed_formats = ",".join(sorted(passed))[:300]
        await self.session.flush()
        await self._hand_off_to_word_mastery(user, cleared)

        total = len(snapshot)
        percent = round((score / total) * 100) if total else 0
        remaining = sum(
            (
                await self.targets.counts(
                    user.id,
                    track=self._track_for_level(getattr(user, "level", None)),
                )
            ).values()
        )
        # "Ishonchli" manbadan kelgan nishonda to'g'ri javob bo'lsa — 5 XP
        # (sessiyaga bir marta). Qoida v2 bilan bir xil: mijoz o'zi
        # "yozgan" xatoni tuzatib XP yig'a olmasin.
        reward_eligible = any(
            set(split_csv(rows[target_id].sources)) & TRUSTED_MISTAKE_REWARD_SOURCES
            for target_id in answered_correct
            if target_id in rows
        )
        if reward_eligible:
            reward = await self.gamification.award(
                user,
                activity_type="mistake_review",
                activity_ref=f"{session_id}:xp",
                base_xp=5,
                level=getattr(user, "level", None),
            )
        else:
            reward = {"awarded_xp": 0, "duplicate": False}
        cleared_items = [
            {"id": int(row.id), "zh": row.zh, "category": row.category, "kind": row.kind}
            for row in cleared
        ]
        event = await CourseMiniAppAnalyticsService(self.session).record_server_event(
            event_name="mistake_review_completed",
            telegram_id=telegram_id,
            user_id=user.id,
            session_id=session_id,
            dedupe_key=f"{session_id}:completed",
            payload={
                "version": MISTAKE_REVIEW_VERSION,
                "score": score,
                "total": total,
                "percent": percent,
                "remaining": remaining,
                "cleared": len(cleared),
                "cleared_targets": cleared_items[:10],
                "category": started_payload.get("category") or "all",
            },
        )
        if not event.get("ok"):
            return {"ok": False, "error": "mistake_review_result_write_failed"}
        if event.get("duplicate"):
            await self.session.rollback()
            completed_result = await self.session.execute(
                select(CourseMiniAppEvent).where(
                    CourseMiniAppEvent.user_id == user.id,
                    CourseMiniAppEvent.event_name == "mistake_review_completed",
                    CourseMiniAppEvent.session_id == session_id,
                )
            )
            completed = completed_result.scalar_one_or_none()
            if completed:
                return self._completed_review_response(completed)
            return {"ok": False, "error": "mistake_review_result_write_failed"}
        await self.session.commit()
        return {
            "ok": True,
            "score": score,
            "total": total,
            "percent": percent,
            "remaining": remaining,
            "cleared": len(cleared),
            "cleared_targets": cleared_items,
            "reward": reward,
        }

    async def complete_review(self, telegram_id: int, *, session_id: str, answers: list) -> dict:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return {"ok": False, "error": "access_start_first"}
        if not self._valid_review_session_id(user.id, session_id):
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
            select(CourseMiniAppEvent).where(
                CourseMiniAppEvent.user_id == user.id,
                CourseMiniAppEvent.event_name == "mistake_review_completed",
                CourseMiniAppEvent.session_id == session_id,
            )
        )
        completed = completed_result.scalar_one_or_none()
        if completed:
            return self._completed_review_response(completed)
        v3_payload = self._json_dict(getattr(started, "payload_json", None))
        if int(v3_payload.get("version") or 0) == MISTAKE_REVIEW_VERSION:
            return await self._complete_review_v3(user, telegram_id, session_id, v3_payload)
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
                if not question_id or question_id in questions:
                    return {"ok": False, "error": "invalid_mistake_review_session"}
                material_format = self._text(raw.get("format"), 64)
                if material_format in MISTAKE_BUILDER_FORMATS:
                    tokens = [self._text(value, 200) for value in (raw.get("tokens") or [])[:30]]
                    answer_tokens = [
                        self._text(value, 200) for value in (raw.get("answer_tokens") or [])[:30]
                    ]
                    if (
                        len(tokens) < 2
                        or any(not value for value in tokens + answer_tokens)
                        or len(tokens) != len(answer_tokens)
                        or sorted(tokens) != sorted(answer_tokens)
                    ):
                        return {"ok": False, "error": "invalid_mistake_review_session"}
                    questions[question_id] = {
                        **raw,
                        "tokens": tokens,
                        "answer_tokens": answer_tokens,
                    }
                else:
                    options = raw.get("options")
                    try:
                        answer_index = int(raw.get("answer_index"))
                    except (TypeError, ValueError):
                        return {"ok": False, "error": "invalid_mistake_review_session"}
                    if not isinstance(options, list) or not 0 <= answer_index < len(options):
                        return {"ok": False, "error": "invalid_mistake_review_session"}
                    questions[question_id] = {**raw, "answer_index": answer_index}
            if set(questions) != {f"mistake:{item_id}" for item_id in mistake_ids}:
                return {"ok": False, "error": "invalid_mistake_review_session"}
        else:
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
                if not question_id or question_id in submitted or question_id not in questions:
                    return {"ok": False, "error": "invalid_mistake_review_session"}
                question = questions[question_id]
                if self._text(question.get("format"), 64) in MISTAKE_BUILDER_FORMATS:
                    selected_tokens = answer_payload.get("selected_tokens")
                    if not isinstance(selected_tokens, list):
                        return {"ok": False, "error": "invalid_mistake_review_session"}
                    selected_tokens = [self._text(value, 200) for value in selected_tokens]
                    if (
                        len(selected_tokens) != len(question["tokens"])
                        or any(not value for value in selected_tokens)
                        or sorted(selected_tokens) != sorted(question["tokens"])
                    ):
                        return {"ok": False, "error": "invalid_mistake_review_session"}
                    submitted[question_id] = {
                        "question_id": question_id,
                        "selected_tokens": selected_tokens,
                    }
                else:
                    try:
                        selected_value = int(answer_payload.get("selected_index"))
                    except (TypeError, ValueError):
                        return {"ok": False, "error": "invalid_mistake_review_session"}
                    submitted[question_id] = {
                        "question_id": question_id,
                        "selected_index": selected_value,
                    }
        else:
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
            if self._text(question.get("format"), 64) in MISTAKE_BUILDER_FORMATS:
                selected_tokens = submitted[question["id"]].get("selected_tokens")
                if not isinstance(selected_tokens, list):
                    return {"ok": False, "error": "mistake_review_answer_invalid"}
                correct = selected_tokens == question["answer_tokens"]
            else:
                try:
                    selected_value = int(submitted[question["id"]].get("selected_index"))
                except (TypeError, ValueError):
                    return {"ok": False, "error": "mistake_review_answer_invalid"}
                correct = selected_value == int(question["answer_index"])
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
            completed_result = await self.session.execute(
                select(CourseMiniAppEvent).where(
                    CourseMiniAppEvent.user_id == user.id,
                    CourseMiniAppEvent.event_name == "mistake_review_completed",
                    CourseMiniAppEvent.session_id == session_id,
                )
            )
            completed = completed_result.scalar_one_or_none()
            if completed:
                return self._completed_review_response(completed)
            return {"ok": False, "error": "mistake_review_result_write_failed"}
        await self.session.commit()
        return {
            "ok": True,
            "score": score,
            "total": total,
            "percent": percent,
            "remaining": remaining,
            "reward": reward,
        }
