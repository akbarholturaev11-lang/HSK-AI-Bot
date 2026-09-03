import json
from pathlib import Path

from app.repositories.course_lesson_repo import CourseLessonRepository
from app.repositories.user_repo import UserRepository
from app.services.course_miniapp_access_service import CourseMiniAppAccessService
from app.services.course_miniapp_analytics_service import CourseMiniAppAnalyticsService
from app.services.course_miniapp_lesson_service import CourseMiniAppLessonService
from app.services.course_mistake_service import CourseMistakeService
from app.services.course_gamification_service import CourseGamificationService
from app.services.course_question_material import COURSE_QUESTION_MATERIAL_VERSION


PRACTICE_VERSION = 1
PRACTICE_MODES = {"placement", "mock", "training"}
TRAINING_SKILLS = {"listening", "writing", "characters", "pronunciation", "pinyin"}
COURSE_V3_DATA_ROOT = Path(__file__).resolve().parents[1] / "static" / "course_v3_data"
STATIC_LOCALE_KEYS = {"uz", "ru", "tj"}
STATIC_CHOICE_CARD_TYPES = {
    "meaning_guess",
    "pinyin_choice",
    "hanzi_choice",
    "listening_choice",
    "translation_choice",
    "quick_quiz",
    "gap_fill",
    "character_recognition",
}
STATIC_CARD_SUBTYPES = {
    "meaning_guess": "hanzi_to_meaning",
    "pinyin_choice": "hanzi_to_pinyin",
    "hanzi_choice": "meaning_to_hanzi",
    "listening_choice": "listening",
    "translation_choice": "meaning_to_hanzi",
    "quick_quiz": "hanzi_to_meaning",
    "gap_fill": "fill_blank",
    "character_recognition": "hanzi_to_meaning",
}


class CourseMiniAppPracticeService:
    def __init__(self, session, bot=None):
        self.session = session
        # Ixtiyoriy: bo'lsa limit tugagani haqida Telegram xabari ham ketadi.
        # Bo'lmasa xabar faqat ilova ichidagi lentaga yoziladi.
        self.bot = bot
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

    @staticmethod
    def _choice_question(question: dict, *, level: str, lesson_order: int, index: int) -> dict | None:
        options = question.get("opts") or question.get("options")
        try:
            answer_index = int(question.get("ans"))
        except (TypeError, ValueError):
            return None
        if not isinstance(options, list) or len(options) < 2 or not 0 <= answer_index < len(options):
            return None
        question_type = str(question.get("type") or "multiple_choice")
        subtype = str(question.get("subtype") or "")
        audio_text = str(question.get("audioText") or "")
        material_format = (
            "listening_choice"
            if audio_text or question_type in {"listening_choice", "listen_and_fill"}
            else "meaning_choice"
            if subtype == "hanzi_to_meaning"
            else "pinyin_choice"
            if subtype == "hanzi_to_pinyin"
            else "hanzi_choice"
            if subtype in {"meaning_to_hanzi", "pinyin_to_hanzi"}
            else "sentence_choice"
        )
        normalized_options = [str(option) for option in options]
        return {
            "material_version": COURSE_QUESTION_MATERIAL_VERSION,
            "id": f"{level}:{lesson_order}:{index}",
            "level": level,
            "lesson": lesson_order,
            "format": material_format,
            "category": "grammar" if material_format == "sentence_choice" else "word",
            "type": question_type,
            "subtype": subtype,
            "prompt": str(question.get("q") or question.get("prompt") or ""),
            "sentence": str(question.get("sentence") or question.get("source") or ""),
            "audio_text": audio_text,
            "pinyin": str(question.get("pinyin") or question.get("py") or ""),
            "options": normalized_options,
            "option_materials": [
                {"id": f"{level}:{lesson_order}:{index}:option:{option_index + 1}", "text": value}
                for option_index, value in enumerate(normalized_options)
            ],
            "answer_index": answer_index,
            "explanation": str(question.get("expl") or question.get("explanation") or ""),
            "source": {
                "kind": "course_quiz",
                "level": level,
                "lesson": lesson_order,
                "question_no": index,
            },
        }

    @classmethod
    def _localized_static_value(cls, value, *, lang: str):
        if isinstance(value, dict):
            keys = set(value)
            if keys and keys <= STATIC_LOCALE_KEYS:
                return str(value.get(lang) or value.get("uz") or value.get("ru") or value.get("tj") or "")
            return {
                key: cls._localized_static_value(item, lang=lang)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [cls._localized_static_value(item, lang=lang) for item in value]
        return value

    @staticmethod
    def _static_lesson_order(path: Path) -> int:
        try:
            return int(path.stem.rsplit("_", 1)[1])
        except (IndexError, TypeError, ValueError):
            return 0

    @classmethod
    def _static_card_question(
        cls,
        card: dict,
        *,
        level: str,
        lesson_order: int,
        section_no: int,
        card_index: int,
        question_index: int,
    ) -> dict | None:
        card_type = str(card.get("type") or "").strip()
        if card_type not in STATIC_CHOICE_CARD_TYPES:
            return None

        options = card.get("options")
        try:
            answer_index = int(card.get("correct_index"))
        except (TypeError, ValueError):
            return None
        if not isinstance(options, list) or len(options) < 2 or not 0 <= answer_index < len(options):
            return None

        normalized_options = [str(option) for option in options]
        question_type = "fill_blank_choice" if card_type == "gap_fill" else card_type
        subtype = STATIC_CARD_SUBTYPES.get(card_type, "")
        audio_text = str(card.get("audio_text") or card.get("audioText") or "")
        sentence = str(
            card.get("sentence")
            or card.get("zh")
            or card.get("phrase")
            or (audio_text if card_type == "listening_choice" else "")
            or ""
        )
        material_format = (
            "listening_choice"
            if audio_text or question_type in {"listening_choice", "listen_and_fill"}
            else "pinyin_choice"
            if card_type == "pinyin_choice"
            else "hanzi_choice"
            if card_type in {"hanzi_choice", "translation_choice"}
            else "sentence_choice"
            if card_type == "gap_fill"
            else "meaning_choice"
        )

        return {
            "material_version": COURSE_QUESTION_MATERIAL_VERSION,
            "id": f"{level}:{lesson_order}:v3:{section_no}:{card_index}:{question_index}",
            "level": level,
            "lesson": lesson_order,
            "format": material_format,
            "category": "grammar" if material_format == "sentence_choice" else "word",
            "type": question_type,
            "subtype": subtype,
            "prompt": str(card.get("prompt") or card.get("title") or ""),
            "sentence": sentence,
            "audio_text": audio_text,
            "pinyin": str(card.get("pinyin") or ""),
            "options": normalized_options,
            "option_materials": [
                {"id": f"{level}:{lesson_order}:v3:{section_no}:{card_index}:option:{option_index + 1}", "text": value}
                for option_index, value in enumerate(normalized_options)
            ],
            "answer_index": answer_index,
            "explanation": str(card.get("explanation") or ""),
            "source": {
                "kind": "course_v3_static_card",
                "level": level,
                "lesson": lesson_order,
                "section_no": section_no,
                "card_no": card_index,
            },
        }

    @classmethod
    def _static_level_questions(
        cls,
        level: str,
        lang: str,
        limit: int,
        skill: str = "",
        max_lesson: int | None = None,
    ) -> list[dict]:
        level_dir = COURSE_V3_DATA_ROOT / level
        if not level_dir.exists():
            return []

        questions: list[dict] = []
        paths = sorted(level_dir.glob("lesson_*.json"), key=cls._static_lesson_order)
        for path in paths:
            lesson_order = cls._static_lesson_order(path)
            if lesson_order <= 0:
                continue
            if max_lesson is not None and lesson_order > int(max_lesson):
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict):
                continue
            payload = cls._localized_static_value(payload, lang=lang)
            for section_index, section in enumerate(payload.get("sections", []), 1):
                if not isinstance(section, dict):
                    continue
                try:
                    section_no = int(section.get("section_no") or section_index)
                except (TypeError, ValueError):
                    section_no = section_index
                for card_index, card in enumerate(section.get("cards", []), 1):
                    if not isinstance(card, dict):
                        continue
                    normalized = cls._static_card_question(
                        card,
                        level=level,
                        lesson_order=lesson_order,
                        section_no=section_no,
                        card_index=card_index,
                        question_index=len(questions) + 1,
                    )
                    if normalized:
                        questions.append(normalized)

            enough_pool = len(questions) >= max(limit * 4, 20)
            enough_skill = not skill or sum(cls._skill_match(item, skill) for item in questions) >= limit
            if enough_pool and enough_skill:
                break
        return questions

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
        if skill == "pronunciation":
            return bool(question.get("audio_text")) or subtype in {"hanzi_to_pinyin", "pinyin_to_hanzi"}
        if skill == "pinyin":
            return subtype in {"hanzi_to_pinyin", "pinyin_to_hanzi"} or question_type in {"pinyin_choice"}
        return True

    @staticmethod
    def _balanced_questions(questions: list[dict], limit: int) -> list[dict]:
        remaining = list(questions)
        selected = []
        seen_lessons: set[int] = set()
        seen_types: set[str] = set()
        seen_subtypes: set[str] = set()
        while remaining and len(selected) < limit:
            best_index = 0
            best_score = -1.0
            for index, item in enumerate(remaining):
                lesson = int(item.get("lesson") or 0)
                question_type = str(item.get("type") or "")
                subtype = str(item.get("subtype") or "")
                score = 0.0
                if lesson not in seen_lessons:
                    score += 4
                if question_type and question_type not in seen_types:
                    score += 3
                if subtype and subtype not in seen_subtypes:
                    score += 2
                score -= index / 1000
                if score > best_score:
                    best_score = score
                    best_index = index
            picked = remaining.pop(best_index)
            selected.append(picked)
            seen_lessons.add(int(picked.get("lesson") or 0))
            seen_types.add(str(picked.get("type") or ""))
            seen_subtypes.add(str(picked.get("subtype") or ""))
        return selected

    async def _level_questions(
        self, level: str, lang: str, limit: int, skill: str = "", max_lesson: int | None = None
    ) -> list[dict]:
        lessons = await self.lesson_repo.list_by_level(level)
        # Dars progressi gate: savollar faqat userning o'rganilgan darslaridan
        # (max_lesson = tugatilgan + 1). None = butun level (eski xatti-harakat).
        if max_lesson is not None:
            lessons = [item for item in lessons if int(item.lesson_order) <= int(max_lesson)]
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
        if not pool:
            pool = self._static_level_questions(
                level,
                lang,
                limit,
                skill,
                max_lesson=max_lesson,
            )
        filtered = [item for item in pool if not skill or self._skill_match(item, skill)]
        if len(filtered) < limit:
            filtered.extend(item for item in pool if item not in filtered)
        if not filtered:
            return []
        return self._balanced_questions(filtered, limit)

    async def _questions(
        self, mode: str, level: str, lang: str, skill: str, max_lesson: int | None = None
    ) -> list[dict]:
        if mode == "placement":
            questions = []
            for item_level, count in (("hsk1", 3), ("hsk2", 3), ("hsk3", 2), ("hsk4", 2)):
                questions.extend(await self._level_questions(item_level, lang, count))
            return questions
        return await self._level_questions(
            level, lang, 10, skill if mode == "training" else "", max_lesson=max_lesson
        )

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
        session_scope = skill or level
        # Bepul userga KUNIGA 1 ta test/training sessiya (har kuni qayta ochiladi).
        # ref orqali bir xil sessiyaning qayta yuklanishi qo'shimcha slot egallamaydi.
        access = await self.access.consume_daily_use(
            user,
            feature_key=feature,
            ref=f"{mode}:{session_scope}",
            notify_bot=self.bot,
        )
        if not access.get("allowed"):
            # `reset_at` — klient "qachon ochiladi" deb ayta olishi uchun.
            # Umrbod limitda u None bo'ladi va klient vaqt ko'rsatmaydi.
            return {
                "ok": False,
                "error": access.get("error") or "free_feature_limit_reached",
                "reset_at": access.get("reset_at"),
                "lifetime": bool(access.get("lifetime")),
            }

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
        # Start'da band qilingan kunlik sessiya bilan bir xil ref — idempotent,
        # ya'ni yakunlash qo'shimcha slot egallamaydi.
        access = await self.access.consume_daily_use(
            user,
            feature_key=feature,
            ref=f"{mode}:{session_scope}",
            notify_bot=self.bot,
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
                        "format": question.get("format") or "sentence_choice",
                        "sentence": question.get("sentence") or "",
                        "audio_text": question.get("audio_text") or "",
                        "pinyin": question.get("pinyin") or "",
                        "language": lang,
                        "options": list(question.get("options") or []),
                        "source": {
                            **(
                                question.get("source")
                                if isinstance(question.get("source"), dict)
                                else {}
                            ),
                            "material_ref": str(question.get("id") or ""),
                        },
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
            base_xp=8 if mode == "training" else 10,
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
