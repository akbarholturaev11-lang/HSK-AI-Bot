from datetime import datetime, timezone

from sqlalchemy import select

from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.repositories.course_lesson_repo import CourseLessonRepository
from app.repositories.course_progress_repo import CourseProgressRepository
from app.repositories.user_repo import UserRepository
from app.services.course_miniapp_access_service import CourseMiniAppAccessService
from app.services.course_miniapp_analytics_service import CourseMiniAppAnalyticsService
from app.services.course_miniapp_lesson_service import CourseMiniAppLessonService
from app.services.course_mistake_service import CourseMistakeService
from app.services.course_engine_service import CourseEngineService
from app.services.course_gamification_service import CourseGamificationService
from app.services.course_trial_service import CourseTrialService
from app.services.study_miniapp_service import StudyMiniAppService


LESSON_FLOW_VERSION = 3
CHAPTER_LABELS = ("A", "B", "C", "D")
SECTION_GROUP_SIZE = 3


class CourseMiniAppLessonFlowService:
    def __init__(self, session):
        self.session = session
        self.user_repo = UserRepository(session)
        self.progress_repo = CourseProgressRepository(session)
        self.lesson_repo = CourseLessonRepository(session)
        self.lesson_service = CourseMiniAppLessonService(session)
        self.mistakes = CourseMistakeService(session)
        self.gamification = CourseGamificationService(session)

    @staticmethod
    def _content_level(level: str) -> str:
        normalized = str(level or "").strip().lower()
        return "hsk4" if normalized in {"hsk4", "hsk4a", "hsk4b"} else normalized

    @staticmethod
    def _allowed_level_candidates(level: str | None) -> tuple[str, ...]:
        normalized = str(level or "").strip().lower()
        fallback_map = {
            "beginner": ("hsk1",),
            "hsk1": ("hsk1",),
            "hsk2": ("hsk2", "hsk1"),
            "hsk3": ("hsk3", "hsk2", "hsk1"),
            "hsk4": ("hsk4", "hsk3", "hsk2", "hsk1"),
            "hsk4a": ("hsk4", "hsk3", "hsk2", "hsk1"),
            "hsk4b": ("hsk4", "hsk3", "hsk2", "hsk1"),
        }
        return fallback_map.get(normalized, ("hsk1",))

    @staticmethod
    def _copy(lang: str, key: str) -> str:
        copy = {
            "ru": {
                "active_word": "Новое активное слово",
                "meaning_guess": "Выберите правильное значение",
                "listening_choice": "Послушайте и выберите ответ",
                "pinyin_choice": "Выберите правильный pinyin",
                "hanzi_choice": "Выберите иероглиф",
                "gap_fill": "Заполните пропуск",
                "character_recognition": "Узнайте иероглиф",
                "match_pairs": "Соедините пары",
                "sentence_builder": "Соберите предложение",
                "word_order": "Расставьте слова по порядку",
                "translation_choice": "Выберите правильный перевод",
                "quick_quiz": "Быстрая проверка",
                "short_dialog": "Короткий диалог",
                "unit_words": "Слова",
                "unit_sound": "Звук",
                "unit_character": "Иероглиф",
                "unit_dialog": "Диалог",
                "unit_build": "Сборка",
                "unit_speaking": "Произношение",
                "unit_review": "Проверка",
                "other_meaning": "Другое значение",
                "purpose_intro": "Новые слова",
                "purpose_reinforcement": "Закрепление",
                "purpose_listening": "Аудирование",
                "purpose_usage": "В речи",
                "purpose_dialog": "Короткий диалог",
                "purpose_review": "Повторение",
            },
            "tj": {
                "active_word": "Калимаи нави фаъол",
                "meaning_guess": "Маънои дурустро интихоб кунед",
                "listening_choice": "Гӯш кунед ва ҷавобро интихоб кунед",
                "pinyin_choice": "Pinyin-и дурустро интихоб кунед",
                "hanzi_choice": "Иероглифи дурустро интихоб кунед",
                "gap_fill": "Ҷои холиро пур кунед",
                "character_recognition": "Иероглифро шиносед",
                "match_pairs": "Ҷуфтҳоро мувофиқ кунед",
                "sentence_builder": "Ҷумларо созед",
                "word_order": "Калимаҳоро бо тартиб гузоред",
                "translation_choice": "Тарҷумаи дурустро интихоб кунед",
                "quick_quiz": "Санҷиши зуд",
                "short_dialog": "Муколамаи кӯтоҳ",
                "unit_words": "Калимаҳо",
                "unit_sound": "Овоз",
                "unit_character": "Иероглиф",
                "unit_dialog": "Муколама",
                "unit_build": "Сохтан",
                "unit_speaking": "Талаффуз",
                "unit_review": "Санҷиш",
                "other_meaning": "Маънои дигар",
                "purpose_intro": "Калимаҳои нав",
                "purpose_reinforcement": "Мустаҳкамкунӣ",
                "purpose_listening": "Шунидан",
                "purpose_usage": "Дар ҷумла",
                "purpose_dialog": "Муколамаи кӯтоҳ",
                "purpose_review": "Такрор",
            },
            "uz": {
                "active_word": "Yangi faol so'z",
                "meaning_guess": "To'g'ri ma'noni tanlang",
                "listening_choice": "Tinglang va javobni tanlang",
                "pinyin_choice": "To'g'ri pinyin tanlang",
                "hanzi_choice": "To'g'ri iyeroglifni tanlang",
                "gap_fill": "Bo'sh joyni to'ldiring",
                "character_recognition": "Iyeroglifni taning",
                "match_pairs": "Juftliklarni moslang",
                "sentence_builder": "Gapni tuzing",
                "word_order": "So'zlarni tartibga qo'ying",
                "translation_choice": "To'g'ri tarjimani tanlang",
                "quick_quiz": "Tezkor tekshiruv",
                "short_dialog": "Qisqa dialog",
                "unit_words": "So'zlar",
                "unit_sound": "Tovush",
                "unit_character": "Iyeroglif",
                "unit_dialog": "Dialog",
                "unit_build": "Yig'ish",
                "unit_speaking": "Talaffuz",
                "unit_review": "Tekshiruv",
                "other_meaning": "Boshqa ma'no",
                "purpose_intro": "Yangi so'zlar",
                "purpose_reinforcement": "Mustahkamlash",
                "purpose_listening": "Tinglash",
                "purpose_usage": "Gapda ishlatish",
                "purpose_dialog": "Qisqa dialog",
                "purpose_review": "Takrorlash",
            },
        }
        return copy.get(lang, copy["ru"]).get(key, key)

    @staticmethod
    def _section_size(level: str) -> int:
        normalized = str(level or "").lower()
        if normalized in {"hsk1", "hsk2"}:
            return 2
        if normalized == "hsk3":
            return 3
        return 4

    @classmethod
    def _split_words(cls, vocab: list[dict], *, level: str) -> list[list[dict]]:
        words = [item for item in vocab if isinstance(item, dict) and item.get("zh")]
        if not words:
            return [[]]
        max_size = cls._section_size(level)
        section_count = max(1, (len(words) + max_size - 1) // max_size)
        while section_count > 1 and len(words) // section_count < 2:
            section_count -= 1
        base = len(words) // section_count
        extra = len(words) % section_count
        chunks = []
        cursor = 0
        for index in range(section_count):
            size = base + (1 if index < extra else 0)
            chunks.append(words[cursor : cursor + size])
            cursor += size
        return chunks or [words]

    @staticmethod
    def _chapter_for_section(section_no: int) -> dict:
        chapter_index = max(0, (int(section_no) - 1) // SECTION_GROUP_SIZE)
        label = CHAPTER_LABELS[min(chapter_index, len(CHAPTER_LABELS) - 1)]
        start = chapter_index * SECTION_GROUP_SIZE + 1
        end = start + SECTION_GROUP_SIZE - 1
        return {"index": chapter_index + 1, "key": label.lower(), "label": label, "start": start, "end": end}

    @staticmethod
    def _section_purpose(section_no: int, section_count: int) -> str:
        section_no = max(1, int(section_no or 1))
        sequence = ("intro", "reinforcement", "listening", "usage", "dialog", "review")
        return sequence[min(section_no, len(sequence)) - 1]

    @staticmethod
    def _focus_words_for_section(active_words: list[dict], section_no: int, *, limit: int = 6) -> list[dict]:
        words = [word for word in active_words if isinstance(word, dict) and word.get("zh")]
        if len(words) <= limit:
            return words
        try:
            section_index = max(1, int(section_no or 1))
        except (TypeError, ValueError):
            section_index = 1
        if section_index <= 2:
            start = 0
        else:
            start = (section_index - 2) * limit
        start = min(start, max(0, len(words) - limit))
        return words[start : start + limit]

    @classmethod
    def _section_plan(cls, payload: dict, *, level: str, lesson_order: int, lang: str = "ru") -> list[dict]:
        sections = []
        words = [item for item in payload.get("vocabulary", []) if isinstance(item, dict) and item.get("zh")]
        total = 6
        for index in range(1, total + 1):
            chapter = cls._chapter_for_section(index)
            purpose = cls._section_purpose(index, total)
            sections.append(
                {
                    "section_key": f"{lesson_order}.{index}",
                    "section_no": index,
                    "section_count": total,
                    "section_purpose": purpose,
                    "section_title": cls._copy(lang, f"purpose_{purpose}"),
                    "chapter_key": chapter["key"],
                    "chapter_label": chapter["label"],
                    "chapter_no": chapter["index"],
                    "chapter_start": chapter["start"],
                    "chapter_end": min(chapter["end"], total),
                    "active_words": words,
                }
            )
        return sections

    @classmethod
    def _normalize_section_key(cls, value: str | int | None, *, lesson_order: int) -> str:
        raw = str(value or "").strip()
        if not raw:
            return f"{lesson_order}.1"
        if raw.startswith(f"{lesson_order}."):
            return raw
        if raw.isdigit():
            return f"{lesson_order}.{int(raw)}"
        return raw

    @classmethod
    def _section_by_key(cls, sections: list[dict], value: str | int | None, *, lesson_order: int) -> dict | None:
        key = cls._normalize_section_key(value, lesson_order=lesson_order)
        return next((item for item in sections if item["section_key"] == key), None)

    @staticmethod
    def _client_completed_section_keys(sections: list[dict], values) -> set[str]:
        if isinstance(values, str):
            raw_values = values.split(",")
        elif isinstance(values, (list, tuple, set)):
            raw_values = values
        else:
            raw_values = []
        valid_keys = {str(item.get("section_key") or "") for item in sections}
        return {str(value).strip() for value in raw_values if str(value).strip() in valid_keys}

    @staticmethod
    def _section_keys_before(section: dict, keys: set[str]) -> set[str]:
        try:
            section_no = int(section.get("section_no") or 1)
        except (TypeError, ValueError):
            section_no = 1
        previous = set()
        for key in keys:
            try:
                key_no = int(str(key).split(".", 1)[1])
            except (IndexError, TypeError, ValueError):
                continue
            if key_no < section_no:
                previous.add(str(key))
        return previous

    @staticmethod
    def _required_previous_section_keys(section: dict) -> set[str]:
        try:
            section_no = int(section.get("section_no") or 1)
        except (TypeError, ValueError):
            section_no = 1
        if section_no <= 1:
            return set()
        prefix = str(section.get("section_key") or "").split(".", 1)[0]
        return {f"{prefix}.{index}" for index in range(1, section_no)}

    @staticmethod
    def _progress_completed_count(progress) -> int:
        try:
            return int(getattr(progress, "completed_lessons_count", 0) or 0)
        except (TypeError, ValueError):
            return 0

    @classmethod
    def _book_lesson_unlocked(cls, lesson, progress) -> bool:
        try:
            lesson_order = int(getattr(lesson, "lesson_order", 0) or 0)
        except (TypeError, ValueError):
            lesson_order = 0
        if lesson_order <= 1:
            return True
        if not progress:
            return False
        progress_level = str(getattr(progress, "level", "") or "").lower()
        lesson_level = str(getattr(lesson, "level", "") or "").lower()
        if progress_level and lesson_level and progress_level != lesson_level:
            return False
        return lesson_order <= cls._progress_completed_count(progress) + 1

    @classmethod
    def _book_lesson_already_completed(cls, lesson, progress) -> bool:
        try:
            lesson_order = int(getattr(lesson, "lesson_order", 0) or 0)
        except (TypeError, ValueError):
            return False
        if lesson_order <= 0 or not progress:
            return False
        progress_level = str(getattr(progress, "level", "") or "").lower()
        lesson_level = str(getattr(lesson, "level", "") or "").lower()
        if progress_level and lesson_level and progress_level != lesson_level:
            return False
        return lesson_order <= cls._progress_completed_count(progress)

    @staticmethod
    def _section_ref(section: dict | None, *, lesson_order: int | None = None) -> dict | None:
        if not section:
            return None
        try:
            section_no = int(section.get("section_no") or 1)
        except (TypeError, ValueError):
            section_no = 1
        raw_key = str(section.get("section_key") or "").strip()
        if not raw_key and lesson_order:
            raw_key = f"{lesson_order}.{section_no}"
        try:
            book_lesson_order = int(str(raw_key).split(".", 1)[0])
        except (TypeError, ValueError):
            book_lesson_order = int(lesson_order or 0)
        return {
            "section_key": raw_key,
            "section_no": section_no,
            "book_lesson_order": book_lesson_order,
        }

    @staticmethod
    def _book_lesson_ref(lesson_order: int | str | None) -> dict | None:
        try:
            order = int(lesson_order or 0)
        except (TypeError, ValueError):
            return None
        if order <= 0:
            return None
        return {
            "book_lesson_order": order,
            "lesson_id": order,
            "section_key": f"{order}.1",
            "section_no": 1,
        }

    @staticmethod
    def _level_label(level: str | None) -> str:
        normalized = str(level or "").strip().lower()
        labels = {
            "hsk1": "HSK 1",
            "hsk2": "HSK 2",
            "hsk3": "HSK 3",
            "hsk4": "HSK 4",
            "hsk4a": "HSK 4 上",
            "hsk4b": "HSK 4 下",
        }
        return labels.get(normalized, normalized.upper() or "HSK")

    @staticmethod
    def _next_requested_level(level: str | None, next_lesson_order: int | str | None = None) -> str | None:
        normalized = str(level or "").strip().lower()
        if normalized == "beginner":
            normalized = "hsk1"
        try:
            next_order = int(next_lesson_order or 0)
        except (TypeError, ValueError):
            next_order = 0
        if normalized == "hsk4a" and next_order >= 11:
            return "hsk4b"
        if next_order:
            return None
        order = ("hsk1", "hsk2", "hsk3")
        if normalized not in order:
            return None
        index = order.index(normalized)
        if index == len(order) - 1:
            return "hsk4a"
        return order[index + 1]

    @classmethod
    def _next_level_ref(cls, lesson, *, requested_level: str) -> dict | None:
        ref = cls._book_lesson_ref(getattr(lesson, "lesson_order", None))
        if not ref:
            return None
        ref["level"] = str(requested_level)
        ref["content_level"] = str(getattr(lesson, "level", "") or requested_level)
        return ref

    @classmethod
    def _decorate_next_ref(cls, ref: dict | None, *, requested_level: str, content_level: str) -> dict | None:
        if not ref:
            return None
        decorated = dict(ref)
        decorated["level"] = str(requested_level)
        decorated["content_level"] = str(content_level)
        return decorated

    @classmethod
    def _level_completion_praise(
        cls,
        *,
        lang: str,
        completed_level: str,
        next_level: str | None,
        completed_lessons_count: int,
        completed_sections_count: int,
        percent: int,
        mistakes: int,
    ) -> dict:
        done = cls._level_label(completed_level)
        next_label = cls._level_label(next_level)
        lessons = max(1, int(completed_lessons_count or 0))
        sections = max(1, int(completed_sections_count or 0))
        mistakes = max(0, int(mistakes or 0))
        if lang == "uz":
            title = f"{done} tugadi. Aniq zo'r ish."
            text = (
                f"Siz {done} bo'yicha {lessons} ta dars va {sections} ta bosqichni tugatdingiz. "
                f"Oxirgi natija: {percent}%, xato: {mistakes}. "
                + (f"{next_label} avtomatik ochildi." if next_level else "Kurs yakunlandi.")
            )
            action = f"{next_label} ga o'tish" if next_level else "Kursga qaytish"
        elif lang == "tj":
            title = f"{done} анҷом шуд. Кори аниқ хуб."
            text = (
                f"Шумо дар {done} {lessons} дарс ва {sections} қисмро анҷом додед. "
                f"Натиҷаи охирин: {percent}%, хато: {mistakes}. "
                + (f"{next_label} автоматӣ кушода шуд." if next_level else "Курс анҷом шуд.")
            )
            action = f"Гузаштан ба {next_label}" if next_level else "Бозгашт ба курс"
        else:
            title = f"{done} завершён. Отличная конкретная работа."
            text = (
                f"Вы закрыли {lessons} уроков и {sections} разделов в {done}. "
                f"Последний результат: {percent}%, ошибок: {mistakes}. "
                + (f"{next_label} открыт автоматически." if next_level else "Курс завершён.")
            )
            action = f"Перейти к {next_label}" if next_level else "Вернуться к курсу"
        return {"title": title, "text": text, "action_label": action}

    @staticmethod
    def _lesson_in_requested_scope(lesson, requested_level: str) -> bool:
        normalized = str(requested_level or "").strip().lower()
        try:
            order = int(getattr(lesson, "lesson_order", 0) or 0)
        except (TypeError, ValueError):
            order = 0
        if normalized == "hsk4a":
            return 1 <= order <= 10
        if normalized == "hsk4b":
            return order >= 11
        return True

    async def _completed_section_keys(self, *, telegram_id: int, lesson_id: int) -> set[str]:
        result = await self.session.execute(
            select(CourseMiniAppEvent.dedupe_key).where(
                CourseMiniAppEvent.telegram_id == int(telegram_id),
                CourseMiniAppEvent.lesson_id == int(lesson_id),
                CourseMiniAppEvent.event_name == "section_completed",
            )
        )
        keys = set()
        prefix = f"section:{lesson_id}:"
        for raw in result.scalars().all():
            text = str(raw or "")
            if text.startswith(prefix):
                keys.add(text.removeprefix(prefix).split(":", 1)[0])
        return keys

    async def _completed_section_keys_by_lesson(self, *, telegram_id: int, lesson_ids: list[int]) -> dict[int, set[str]]:
        if not lesson_ids:
            return {}
        result = await self.session.execute(
            select(CourseMiniAppEvent.lesson_id, CourseMiniAppEvent.dedupe_key).where(
                CourseMiniAppEvent.telegram_id == int(telegram_id),
                CourseMiniAppEvent.lesson_id.in_([int(item) for item in lesson_ids]),
                CourseMiniAppEvent.event_name == "section_completed",
            )
        )
        completed: dict[int, set[str]] = {}
        for lesson_id, raw in result.all():
            if lesson_id is None:
                continue
            text = str(raw or "")
            prefix = f"section:{int(lesson_id)}:"
            if text.startswith(prefix):
                completed.setdefault(int(lesson_id), set()).add(text.removeprefix(prefix).split(":", 1)[0])
        return completed

    @staticmethod
    def _section_unlocked(section: dict, completed: set[str]) -> bool:
        return CourseMiniAppLessonFlowService._required_previous_section_keys(section).issubset(completed)

    @staticmethod
    def _section_payload(payload: dict, section: dict) -> dict:
        active_words = [item for item in section.get("active_words", []) if isinstance(item, dict)]
        section_key = str(section.get("section_key") or "")
        try:
            book_lesson_order = int(section_key.split(".", 1)[0])
        except (TypeError, ValueError):
            book_lesson_order = 0
        return {
            **payload,
            "vocabulary": active_words,
            "active_words": active_words,
            "section_key": section_key,
            "section_no": int(section.get("section_no") or 1),
            "section_count": int(section.get("section_count") or 1),
            "section_purpose": str(section.get("section_purpose") or ""),
            "section_title": str(section.get("section_title") or ""),
            "book_lesson_order": book_lesson_order,
            "quiz_questions": [],
            "reinforcement_tasks": [],
        }

    async def get_section_plan(
        self,
        telegram_id: int,
        *,
        level: str,
        lang: str,
    ) -> dict:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return {"ok": False, "error": "access_start_first"}

        requested_level = str(level or "").strip().lower() or "hsk1"
        content_level = self._content_level(requested_level)
        if content_level not in self._allowed_level_candidates(getattr(user, "level", None)):
            return {"ok": False, "error": "course_lesson_not_unlocked"}

        all_lessons = await self.lesson_repo.list_by_level(content_level)
        lessons = [
            lesson
            for lesson in all_lessons
            if self._lesson_in_requested_scope(lesson, requested_level)
        ]
        if not lessons:
            return {"ok": False, "error": "course_no_lesson_found"}

        progress = await self.progress_repo.get_by_user_id(user.id)
        progress_level = str(getattr(progress, "level", "") or "").strip().lower()
        progress_matches_level = bool(progress and progress_level == content_level)
        completed_count = self._progress_completed_count(progress) if progress_matches_level else 0

        current_lesson_order = 0
        if progress_matches_level and getattr(progress, "current_lesson_id", None):
            current_lesson = await self.lesson_repo.get_by_id(int(progress.current_lesson_id))
            if current_lesson and str(getattr(current_lesson, "level", "") or "").strip().lower() == content_level:
                current_lesson_order = int(getattr(current_lesson, "lesson_order", 0) or 0)
        if current_lesson_order <= 0:
            current_lesson_order = completed_count + 1

        completed_by_lesson = await self._completed_section_keys_by_lesson(
            telegram_id=telegram_id,
            lesson_ids=[int(lesson.id) for lesson in lessons],
        )

        planned_lessons = []
        flat_sections = []
        for lesson in lessons:
            lesson_order = int(lesson.lesson_order)
            payload = await self.lesson_service.get_payload(
                lesson_order=lesson_order,
                lang=lang,
                level=str(lesson.level),
            )
            if not payload:
                continue

            raw_sections = self._section_plan(payload, level=str(lesson.level), lesson_order=lesson_order, lang=lang)
            book_completed = lesson_order <= completed_count
            completed_keys = set(completed_by_lesson.get(int(lesson.id), set()))
            if book_completed:
                completed_keys |= {str(item["section_key"]) for item in raw_sections}

            lesson_sections = []
            for index, section in enumerate(raw_sections):
                next_section = raw_sections[index + 1] if index + 1 < len(raw_sections) else None
                if not next_section:
                    next_lesson = next((item for item in lessons if int(item.lesson_order) > lesson_order), None)
                    next_section_ref = self._book_lesson_ref(getattr(next_lesson, "lesson_order", None))
                else:
                    next_section_ref = self._section_ref(next_section, lesson_order=lesson_order)

                section_completed = str(section["section_key"]) in completed_keys
                book_unlocked = self._book_lesson_unlocked(lesson, progress if progress_matches_level else None)
                section_unlocked = book_unlocked and self._section_unlocked(section, completed_keys)
                node = {
                    "level": requested_level,
                    "content_level": str(lesson.level),
                    "book_lesson_order": lesson_order,
                    "lesson_id": lesson_order,
                    "lesson_title": str(payload.get("title") or getattr(lesson, "title", "") or ""),
                    "section_key": section["section_key"],
                    "section_no": int(section["section_no"]),
                    "section_count": int(section["section_count"]),
                    "section_purpose": section["section_purpose"],
                    "section_title": section["section_title"],
                    "section_group": {
                        "key": section["chapter_key"],
                        "label": section["chapter_label"],
                        "no": section["chapter_no"],
                        "section_start": section["chapter_start"],
                        "section_end": section["chapter_end"],
                    },
                    "chapter_key": section["chapter_key"],
                    "chapter_label": section["chapter_label"],
                    "chapter_no": section["chapter_no"],
                    "chapter_start": section["chapter_start"],
                    "chapter_end": section["chapter_end"],
                    "active_words": self._word_refs(section.get("active_words", [])),
                    "is_completed": bool(section_completed),
                    "is_locked": not section_completed and not section_unlocked,
                    "is_current": False,
                    "node_status": "completed" if section_completed else "locked",
                    "next_section": next_section_ref,
                }
                lesson_sections.append(node)
                flat_sections.append(node)

            planned_lessons.append(
                {
                    "level": requested_level,
                    "content_level": str(lesson.level),
                    "lesson_id": lesson_order,
                    "book_lesson_order": lesson_order,
                    "lesson_title": str(payload.get("title") or getattr(lesson, "title", "") or ""),
                    "section_count": len(lesson_sections),
                    "is_completed": book_completed or all(item["is_completed"] for item in lesson_sections),
                    "is_locked": not self._book_lesson_unlocked(lesson, progress if progress_matches_level else None),
                    "sections": lesson_sections,
                }
            )

        current_section = next(
            (
                section
                for section in flat_sections
                if not section["is_completed"]
                and not section["is_locked"]
                and int(section["book_lesson_order"]) == int(current_lesson_order)
            ),
            None,
        ) or next(
            (section for section in flat_sections if not section["is_completed"] and not section["is_locked"]),
            None,
        )
        if current_section:
            current_section["is_current"] = True
            current_section["node_status"] = "current"

        fallback_current = current_section or (flat_sections[-1] if flat_sections else None)
        return {
            "ok": True,
            "level": requested_level,
            "content_level": content_level,
            "completed_book_lessons_count": completed_count,
            "completed_sections_count": sum(1 for item in flat_sections if item["is_completed"]),
            "total_sections": len(flat_sections),
            "current_section": self._section_ref(fallback_current, lesson_order=fallback_current["book_lesson_order"]) if fallback_current else None,
            "lessons": planned_lessons,
            "sections": flat_sections,
        }

    @staticmethod
    def _dialog_lines_for_word(word: dict) -> list[dict]:
        zh = str(word.get("zh") or "").strip()
        pos = str(word.get("pos") or "").lower()
        place_words = {
            "银行",
            "学校",
            "大学",
            "医院",
            "商店",
            "饭店",
            "机场",
            "车站",
            "洗手间",
            "公司",
            "办公室",
            "家",
        }
        if zh == "赚":
            return [
                {"speaker": "A", "text": "你为什么工作？"},
                {"speaker": "B", "text": "我想赚钱。"},
            ]
        if pos.startswith(("v", "verb")):
            prefix = "我需要" if len(zh) >= 2 else "我想"
            return [
                {"speaker": "A", "text": "你今天做什么？"},
                {"speaker": "B", "text": f"{prefix}{zh}。"},
            ]
        if pos.startswith(("adj", "a")):
            return [
                {"speaker": "A", "text": "这个怎么样？"},
                {"speaker": "B", "text": f"很{zh}。"},
            ]
        if zh in place_words or "place" in pos:
            return [
                {"speaker": "A", "text": "你去哪儿？"},
                {"speaker": "B", "text": f"我去{zh}。"},
            ]
        return [
            {"speaker": "A", "text": "这是什么？"},
            {"speaker": "B", "text": f"这是{zh}。"},
        ]

    def _short_dialog_card(self, active_words: list[dict], *, lang: str) -> dict | None:
        target = next((item for item in active_words if item.get("zh") and item.get("meaning")), None)
        if not target:
            return None
        options = [str(item.get("meaning") or "") for item in active_words if item.get("meaning")]
        if str(target.get("meaning") or "") not in options:
            options.insert(0, str(target.get("meaning") or ""))
        options = list(dict.fromkeys([item for item in options if item]))[:4]
        if len(options) < 2:
            return None
        correct = options.index(str(target.get("meaning") or ""))
        prompt = {
            "ru": f"Что означает «{target['zh']}» в диалоге?",
            "tj": f"«{target['zh']}» дар муколама чӣ маъно дорад?",
            "uz": f"Dialogda «{target['zh']}» nimani anglatadi?",
        }.get(lang, f"Что означает «{target['zh']}» в диалоге?")
        return {
            "id": "activity:dialog",
            "type": "dialog_context",
            "title": self._copy(lang, "short_dialog"),
            "unit": self._copy(lang, "unit_dialog"),
            "prompt": prompt,
            "dialog": self._dialog_lines_for_word(target),
            "options": options,
            "correct_index": correct,
            "explanation": f"{target['zh']} = {target.get('meaning') or ''}",
            "source_words": [str(target.get("zh") or "")],
            "required": True,
        }

    async def jump_to_lesson(
        self,
        telegram_id: int,
        *,
        level: str,
        lesson_order: int,
        section_key: str | int | None = None,
        percent: int = 0,
        score: int = 0,
        total: int = 0,
        passed: bool = False,
    ) -> dict:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return {"ok": False, "error": "access_start_first"}

        content_level = self._content_level(level)
        lesson = await self.lesson_repo.get_by_level_and_order(content_level, int(lesson_order or 0))
        if not lesson:
            return {"ok": False, "error": "course_no_lesson_found"}

        progress = await self.progress_repo.get_by_user_id(user.id, for_update=True)
        if not progress:
            progress = await self.progress_repo.create(
                user_id=user.id,
                level=str(lesson.level),
                current_lesson_id=lesson.id,
                current_step="intro",
                waiting_for="none",
            )
        progress.level = str(lesson.level)
        progress.completed_lessons_count = max(
            int(getattr(progress, "completed_lessons_count", 0) or 0),
            max(0, int(lesson.lesson_order) - 1),
        )
        progress.homework_status = "none"
        progress.needs_review_prompt = False
        progress.next_study_at = None
        await self.progress_repo.set_current_lesson_and_step(
            progress=progress,
            lesson_id=lesson.id,
            step="intro",
            waiting_for="none",
        )
        user.level = str(lesson.level)

        safe_percent = max(0, min(100, int(percent or 0)))
        safe_total = max(0, int(total or 0))
        safe_score = max(0, min(safe_total, int(score or 0))) if safe_total else max(0, int(score or 0))
        await CourseMiniAppAnalyticsService(self.session).record_server_event(
            event_name="lesson_jump_selected",
            telegram_id=telegram_id,
            user_id=user.id,
            level=str(lesson.level),
            lesson_id=lesson.id,
            lesson_order=int(lesson.lesson_order),
            dedupe_key=f"lesson-jump:{user.id}:{lesson.id}:{section_key or '1'}",
            payload={
                "section_key": str(section_key or f"{lesson.lesson_order}.1"),
                "percent": safe_percent,
                "score": safe_score,
                "total": safe_total,
                "passed": bool(passed),
                "flow_version": LESSON_FLOW_VERSION,
            },
        )
        await self.session.commit()
        return {
            "ok": True,
            "level": str(lesson.level),
            "lesson_id": int(lesson.lesson_order),
            "book_lesson_order": int(lesson.lesson_order),
            "section_key": str(section_key or f"{lesson.lesson_order}.1"),
            "completed_lessons_count": int(progress.completed_lessons_count or 0),
            "percent": safe_percent,
            "passed": bool(passed),
        }

    async def _context(self, telegram_id: int, *, level: str, lesson_order: int):
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return None, None, None, "access_start_first"

        content_level = self._content_level(level)
        lesson = await self.lesson_repo.get_by_level_and_order(content_level, int(lesson_order or 0))
        if not lesson:
            return user, None, None, "course_no_lesson_found"
        if str(getattr(lesson, "level", "") or "") not in self._allowed_level_candidates(getattr(user, "level", None)):
            return user, None, lesson, "course_lesson_not_unlocked"

        progress = await self.progress_repo.get_by_user_id(user.id, for_update=True)
        if not self._book_lesson_unlocked(lesson, progress):
            return user, progress, lesson, "course_lesson_not_unlocked"

        access = CourseMiniAppAccessService(self.session)
        trial = CourseTrialService(self.session)
        paid = access.is_paid_user(user)
        entitlements = await access.get_entitlements(user)
        if not paid:
            if not entitlements.get("lesson", {}).get("allowed"):
                return user, None, lesson, "free_feature_limit_reached"
            if not await trial.ensure_trial_lesson(user, lesson.id):
                return user, None, lesson, "free_feature_limit_reached"

        if not progress:
            progress = await self.progress_repo.create(
                user_id=user.id,
                level=str(lesson.level),
                current_lesson_id=lesson.id,
                current_step="intro",
                waiting_for="none",
            )
        elif (
            int(getattr(progress, "current_lesson_id", 0) or 0) != int(lesson.id)
            and not self._book_lesson_already_completed(lesson, progress)
        ):
            progress.level = str(lesson.level)
            progress.homework_status = "none"
            progress.needs_review_prompt = False
            progress.next_study_at = None
            await self.progress_repo.set_current_lesson_and_step(
                progress=progress,
                lesson_id=lesson.id,
                step="intro",
                waiting_for="none",
            )
        return user, progress, lesson, ""

    @staticmethod
    def _choice_card(question: dict, *, card_id: str, card_type: str, title: str) -> dict | None:
        options = question.get("opts") or question.get("options")
        try:
            correct_index = int(question.get("ans"))
        except (TypeError, ValueError):
            return None
        if not isinstance(options, list) or len(options) < 2 or not 0 <= correct_index < len(options):
            return None
        clean_options = [str(option) for option in options if str(option or "").strip()]
        if len(clean_options) != len(options):
            return None
        return {
            "id": card_id,
            "type": card_type,
            "title": title,
            "prompt": str(question.get("q") or question.get("prompt") or title),
            "sentence": str(question.get("sentence") or question.get("source") or ""),
            "audio_text": str(question.get("audioText") or ""),
            "options": clean_options,
            "correct_index": correct_index,
            "explanation": str(question.get("expl") or question.get("explanation") or ""),
            "source_words": [str(item) for item in question.get("source_words", []) if str(item or "").strip()],
            "required": True,
        }

    @staticmethod
    def _order_card(task: dict, *, card_id: str, card_type: str, title: str) -> dict | None:
        tokens = task.get("tokens")
        answer = task.get("answer")
        if not isinstance(tokens, list) or not isinstance(answer, list) or len(answer) < 2:
            return None
        return {
            "id": card_id,
            "type": card_type,
            "title": title,
            "prompt": str(task.get("q") or task.get("prompt") or title),
            "sentence": str(task.get("translation") or task.get("source") or ""),
            "tokens": [str(token) for token in tokens],
            "answer_tokens": [str(token) for token in answer],
            "explanation": str(task.get("expl") or task.get("explanation") or ""),
            "source_words": [str(item) for item in task.get("source_words", []) if str(item or "").strip()],
            "required": True,
        }

    @staticmethod
    def _word_value(word: dict, key: str) -> str:
        return str(word.get(key) or "").strip()

    @classmethod
    def _word_options(cls, active_words: list[dict], key: str, answer: str, *, fallback: str = "") -> list[str]:
        options = [answer]
        for word in active_words:
            value = cls._word_value(word, key)
            if value and value not in options:
                options.append(value)
            if len(options) >= 4:
                break
        if len(options) < 2 and fallback and fallback not in options:
            options.append(fallback)
        return options

    @classmethod
    def _word_choice_question(
        cls,
        *,
        word: dict,
        active_words: list[dict],
        option_key: str,
        prompt: str,
        answer: str,
        explanation: str,
        fallback_option: str = "",
        sentence: str = "",
        audio_text: str = "",
    ) -> dict | None:
        answer = str(answer or "").strip()
        if not answer:
            return None
        options = cls._word_options(active_words, option_key, answer, fallback=fallback_option)
        if len(options) < 2:
            return None
        return {
            "q": prompt,
            "sentence": sentence,
            "audioText": audio_text,
            "opts": options,
            "ans": options.index(answer),
            "expl": explanation,
            "source_words": [cls._word_value(word, "zh")],
        }

    @staticmethod
    def _word_refs(words: list[dict]) -> list[dict]:
        refs = []
        for word in words:
            if not isinstance(word, dict):
                continue
            zh = str(word.get("zh") or "").strip()
            if not zh:
                continue
            refs.append(
                {
                    "zh": zh,
                    "pinyin": str(word.get("pinyin") or "").strip(),
                    "meaning": str(word.get("meaning") or "").strip(),
                    "pos": str(word.get("pos") or "").strip(),
                    "sentence": str(word.get("sentence") or word.get("example") or "").strip(),
                }
            )
        return refs

    @staticmethod
    def _single_hanzi(value) -> bool:
        text = str(value or "")
        return len(text) == 1 and "\u4e00" <= text <= "\u9fff"

    @classmethod
    def _character_split_task(cls, tokens: list, answer: list) -> bool:
        return (
            len(answer) > 1
            and all(cls._single_hanzi(item) for item in answer)
            and all(cls._single_hanzi(item) for item in tokens)
        )

    @staticmethod
    def _sentence_text_for_word(word: dict) -> str:
        sentence = str(word.get("sentence") or word.get("example") or "").strip()
        zh = str(word.get("zh") or "").strip()
        return sentence if zh and zh in sentence else ""

    @classmethod
    def _sentence_tokens_for_word(cls, word: dict) -> list[str]:
        sentence = cls._sentence_text_for_word(word)
        if sentence:
            return [char for char in sentence if "\u4e00" <= char <= "\u9fff"]
        zh = str(word.get("zh") or "").strip()
        if not zh:
            return []
        pos = str(word.get("pos") or "").lower()
        place_words = {
            "银行",
            "学校",
            "大学",
            "医院",
            "商店",
            "饭店",
            "机场",
            "车站",
            "洗手间",
            "公司",
            "办公室",
            "家",
        }
        if zh == "赚":
            return ["我", "想", "赚钱"]
        if pos.startswith(("v", "verb")):
            return ["我", "需要" if len(zh) >= 2 else "想", zh]
        if pos.startswith(("adj", "a")):
            return ["很", zh]
        if zh in place_words or "place" in pos:
            return ["我", "去", zh]
        return ["这是", zh]

    def _gap_sentence_for_word(self, word: dict) -> str:
        zh = str(word.get("zh") or "").strip()
        sentence = self._sentence_text_for_word(word)
        if len(zh) < 2 or not sentence or sentence.count(zh) != 1:
            return ""
        return sentence.replace(zh, "____", 1)

    def _sentence_task_for_word(self, word: dict, *, lang: str) -> dict | None:
        tokens = self._sentence_tokens_for_word(word)
        if len(tokens) < 2:
            return None
        sentence = "".join(tokens) + "。"
        return {
            "type": "build_chinese_sentence",
            "prompt": self._copy(lang, "sentence_builder"),
            "source": str(word.get("meaning") or sentence),
            "tokens": [*tokens[1:], tokens[0]],
            "answer": tokens,
            "explanation": sentence,
            "source_words": [str(word.get("zh") or "").strip()],
        }

    @staticmethod
    def _task_source_words(task: dict, active_zh: set[str]) -> list[str]:
        explicit = [
            str(item).strip()
            for item in (task.get("source_words") or [])
            if str(item or "").strip() in active_zh
        ]
        if explicit:
            return list(dict.fromkeys(explicit))
        fields = [
            task.get("q"),
            task.get("prompt"),
            task.get("sentence"),
            task.get("source"),
            task.get("translation"),
            *(task.get("tokens") if isinstance(task.get("tokens"), list) else []),
            *(task.get("answer") if isinstance(task.get("answer"), list) else []),
        ]
        text = " ".join(str(item or "") for item in fields)
        return [word for word in active_zh if word and word in text]

    @staticmethod
    def _card_has_undefined(card: dict) -> bool:
        stack = [card]
        while stack:
            value = stack.pop()
            if isinstance(value, dict):
                stack.extend(value.values())
            elif isinstance(value, list):
                stack.extend(value)
            elif "undefined" in str(value).lower():
                return True
        return False

    @classmethod
    def _card_source_valid(cls, card: dict, active_zh: set[str]) -> bool:
        source_words = {str(item).strip() for item in card.get("source_words", []) if str(item).strip()}
        if card.get("type") == "active_word":
            zh = str((card.get("word") or {}).get("zh") or "").strip()
            source_words.add(zh)
        if not source_words:
            return False
        return source_words <= active_zh

    @staticmethod
    def _card_shape_valid(card: dict) -> bool:
        card_type = str(card.get("type") or "")
        if card_type in {"character_trace", "stroke_preview"}:
            return False
        if card_type == "pronunciation":
            return bool(str(card.get("phrase") or "").strip())
        if card_type == "active_word":
            return bool((card.get("word") or {}).get("zh"))
        if card_type in {
            "meaning_guess",
            "pinyin_choice",
            "hanzi_choice",
            "listening_choice",
            "gap_fill",
            "character_recognition",
            "translation_choice",
            "quick_quiz",
            "dialog_context",
        }:
            options = card.get("options")
            try:
                correct_index = int(card.get("correct_index"))
            except (TypeError, ValueError):
                return False
            if card_type == "gap_fill" and "____" not in str(card.get("sentence") or ""):
                return False
            return isinstance(options, list) and len(options) >= 2 and 0 <= correct_index < len(options)
        if card_type in {"sentence_builder", "word_order"}:
            return len(card.get("answer_tokens") or []) >= 2 and len(card.get("tokens") or []) >= 2
        if card_type == "match_pairs":
            return len(card.get("pairs") or []) >= 2
        return False

    @classmethod
    def _limit_consecutive_card_types(cls, cards: list[dict]) -> list[dict]:
        result: list[dict] = []
        delayed: list[dict] = []
        for card in cards:
            if len(result) >= 2 and result[-1].get("type") == result[-2].get("type") == card.get("type"):
                delayed.append(card)
            else:
                result.append(card)
        for card in delayed:
            inserted = False
            for index in range(len(result) - 1, 0, -1):
                previous_type = result[index - 1].get("type")
                next_type = result[index].get("type")
                if previous_type != card.get("type") and next_type != card.get("type"):
                    result.insert(index, card)
                    inserted = True
                    break
            if not inserted and not (
                len(result) >= 2 and result[-1].get("type") == result[-2].get("type") == card.get("type")
            ):
                result.append(card)
        return result

    @classmethod
    def _validate_cards(cls, cards: list[dict], active_words: list[dict]) -> list[dict]:
        active_zh = {str(word.get("zh") or "").strip() for word in active_words if str(word.get("zh") or "").strip()}
        validated: list[dict] = []
        seen_ids: set[str] = set()
        sentence_cards = 0
        for card in cards:
            if not isinstance(card, dict):
                continue
            card_id = str(card.get("id") or "").strip()
            if not card_id or card_id in seen_ids:
                continue
            if cls._card_has_undefined(card):
                continue
            if not cls._card_shape_valid(card):
                continue
            if not cls._card_source_valid(card, active_zh):
                continue
            if card.get("type") in {"sentence_builder", "word_order"}:
                sentence_cards += 1
                if sentence_cards > 2:
                    continue
            seen_ids.add(card_id)
            validated.append(card)
        return cls._limit_consecutive_card_types(validated)[:12]

    @staticmethod
    def _section_purpose_pattern(purpose: str) -> list[str]:
        patterns = {
            "intro": [
                "word:1",
                "meaning:1",
                "word:2",
                "pinyin:1",
                "hanzi:2",
                "word:3",
                "recognition:1",
                "match",
                "translation:2",
                "listening:1",
                "quiz:3",
            ],
            "reinforcement": [
                "match",
                "meaning:2",
                "pinyin:2",
                "hanzi:3",
                "recognition:2",
                "listening:2",
                "translation:3",
                "quiz:4",
                "word:1",
                "word:2",
            ],
            "listening": [
                "listening:1",
                "pinyin:1",
                "listening:2",
                "meaning:1",
                "pronunciation",
                "hanzi:2",
                "listening:3",
                "translation:2",
                "match",
                "dialog",
            ],
            "usage": [
                "gap:1",
                "builder",
                "meaning:1",
                "order",
                "gap:2",
                "translation:1",
                "quiz:2",
                "dialog",
                "match",
                "hanzi:1",
            ],
            "dialog": [
                "dialog",
                "listening:1",
                "meaning:1",
                "gap:1",
                "translation:2",
                "quiz:3",
                "pinyin:2",
                "match",
                "word:1",
                "recognition:1",
            ],
            "review": [
                "quiz:1",
                "translation:1",
                "meaning:2",
                "pinyin:3",
                "listening:2",
                "hanzi:4",
                "recognition:3",
                "gap:2",
                "match",
                "builder",
                "word:1",
                "order",
            ],
        }
        return patterns.get(str(purpose or "").strip(), patterns["review"])

    def _build_cards(self, payload: dict, *, lang: str, lesson_order: int) -> list[dict]:
        vocab = [item for item in payload.get("vocabulary", []) if isinstance(item, dict)]
        active_words = self._word_refs(vocab)
        if not active_words:
            return []
        try:
            section_no = int(payload.get("section_no") or 1)
        except (TypeError, ValueError):
            section_no = 1
        focus_words = self._focus_words_for_section(active_words, section_no)
        words = []
        for index, word in enumerate(focus_words, 1):
            words.append(
                {
                    "id": f"word:{index}",
                    "type": "active_word",
                    "title": self._copy(lang, "active_word"),
                    "unit": self._copy(lang, "unit_words"),
                    "word": {
                        "zh": str(word.get("zh") or ""),
                        "pinyin": str(word.get("pinyin") or ""),
                        "meaning": str(word.get("meaning") or ""),
                        "pos": str(word.get("pos") or ""),
                    },
                    "required": True,
                }
            )

        tasks = [item for item in payload.get("reinforcement_tasks", []) if isinstance(item, dict)]
        active_zh = {word["zh"] for word in active_words if word.get("zh")}
        order_tasks = []
        for word in focus_words:
            task = self._sentence_task_for_word(word, lang=lang)
            if task:
                order_tasks.append(task)
            if len(order_tasks) >= 4:
                break
        if len(order_tasks) < 2:
            for item in tasks:
                if str(item.get("type") or "") not in {"word_order", "build_chinese_sentence", "build_sentence_chips"}:
                    continue
                tokens = item.get("tokens")
                answer = item.get("answer")
                source_words = self._task_source_words(item, active_zh)
                if not source_words or not isinstance(tokens, list) or not isinstance(answer, list):
                    continue
                if 2 <= len(answer) <= 6 and len(tokens) <= 8 and not self._character_split_task(tokens, answer):
                    order_tasks.append({**item, "source_words": source_words})
                if len(order_tasks) >= 4:
                    break

        activities: dict[str, dict] = {}
        def add_choice_activity(
            key: str,
            *,
            word: dict,
            option_key: str,
            prompt: str,
            answer: str,
            explanation: str,
            card_type: str,
            title_key: str,
            unit_key: str,
            fallback_option: str = "",
            sentence: str = "",
            audio_text: str = "",
        ) -> None:
            source = self._word_choice_question(
                word=word,
                active_words=active_words,
                option_key=option_key,
                prompt=prompt,
                answer=answer,
                explanation=explanation,
                fallback_option=fallback_option,
                sentence=sentence,
                audio_text=audio_text,
            )
            card = self._choice_card(
                source or {},
                card_id=f"activity:{key}",
                card_type=card_type,
                title=self._copy(lang, title_key),
            )
            if card:
                card["unit"] = self._copy(lang, unit_key)
                activities[key] = card

        for index, word in enumerate(focus_words[:6], 1):
            zh = str(word.get("zh") or "")
            pinyin = str(word.get("pinyin") or "")
            meaning = str(word.get("meaning") or "")
            if meaning:
                add_choice_activity(
                    f"meaning:{index}",
                    word=word,
                    option_key="meaning",
                    prompt=f"{zh} — ?",
                    answer=meaning,
                    explanation=f"{zh} = {meaning}",
                    fallback_option=self._copy(lang, "other_meaning"),
                    card_type="meaning_guess",
                    title_key="meaning_guess",
                    unit_key="unit_review",
                )
                character = next((char for char in zh if "\u4e00" <= char <= "\u9fff"), zh[:1])
                add_choice_activity(
                    f"recognition:{index}",
                    word=word,
                    option_key="meaning",
                    prompt=f"{character} — ?",
                    answer=meaning,
                    explanation=f"{zh} = {meaning}",
                    fallback_option=self._copy(lang, "other_meaning"),
                    card_type="character_recognition",
                    title_key="character_recognition",
                    unit_key="unit_character",
                )
                add_choice_activity(
                    f"quiz:{index}",
                    word=word,
                    option_key="meaning",
                    prompt=f"{zh} ({pinyin}) — ?",
                    answer=meaning,
                    explanation=f"{zh} = {meaning}",
                    fallback_option=self._copy(lang, "other_meaning"),
                    card_type="quick_quiz",
                    title_key="quick_quiz",
                    unit_key="unit_review",
                )
            if pinyin:
                add_choice_activity(
                    f"pinyin:{index}",
                    word=word,
                    option_key="pinyin",
                    prompt=f"{zh} — pinyin?",
                    answer=pinyin,
                    explanation=f"{zh} · {pinyin}",
                    card_type="pinyin_choice",
                    title_key="pinyin_choice",
                    unit_key="unit_sound",
                )
            add_choice_activity(
                f"hanzi:{index}",
                word=word,
                option_key="zh",
                prompt=f"{meaning or pinyin or zh} — ?",
                answer=zh,
                explanation=f"{zh} = {meaning or pinyin}",
                card_type="hanzi_choice",
                title_key="hanzi_choice",
                unit_key="unit_character",
            )
            add_choice_activity(
                f"listening:{index}",
                word=word,
                option_key="zh",
                prompt=self._copy(lang, "listening_choice"),
                answer=zh,
                explanation=f"{zh} = {meaning or pinyin}",
                audio_text=zh,
                card_type="listening_choice",
                title_key="listening_choice",
                unit_key="unit_sound",
            )
            add_choice_activity(
                f"translation:{index}",
                word=word,
                option_key="zh",
                prompt=f"{meaning or pinyin or zh} — ?",
                answer=zh,
                explanation=f"{zh} = {meaning or pinyin}",
                card_type="translation_choice",
                title_key="translation_choice",
                unit_key="unit_review",
            )
            add_choice_activity(
                f"gap:{index}",
                word=word,
                option_key="zh",
                prompt=self._copy(lang, "gap_fill"),
                sentence=self._gap_sentence_for_word(word),
                answer=zh,
                explanation=self._gap_sentence_for_word(word).replace("____", zh),
                card_type="gap_fill",
                title_key="gap_fill",
                unit_key="unit_build",
            )

        pronunciation_word = next((item for item in focus_words if item.get("zh")), active_words[0])
        activities["pronunciation"] = {
            "id": "activity:pronunciation",
            "type": "pronunciation",
            "title": self._copy(lang, "unit_speaking"),
            "unit": self._copy(lang, "unit_sound"),
            "prompt": self._copy(lang, "unit_speaking"),
            "phrase": pronunciation_word["zh"],
            "pinyin": str(pronunciation_word.get("pinyin") or ""),
            "translation": str(pronunciation_word.get("meaning") or ""),
            "source_words": [pronunciation_word["zh"]],
            "required": True,
        }

        if order_tasks:
            card = self._order_card(
                order_tasks[0],
                card_id="activity:builder",
                card_type="sentence_builder",
                title=self._copy(lang, "sentence_builder"),
            )
            if card:
                card["unit"] = self._copy(lang, "unit_build")
                activities["builder"] = card
            card = self._order_card(
                order_tasks[1] if len(order_tasks) > 1 else order_tasks[0],
                card_id="activity:order",
                card_type="word_order",
                title=self._copy(lang, "word_order"),
            )
            if card:
                card["unit"] = self._copy(lang, "unit_build")
                activities["order"] = card

        pairs = [
            [word["zh"], word.get("meaning") or word.get("pinyin") or ""]
            for word in focus_words
            if word.get("zh") and (word.get("meaning") or word.get("pinyin"))
        ][:6]
        if len(pairs) >= 2:
            activities["match"] = {
                "id": "activity:match",
                "type": "match_pairs",
                "title": self._copy(lang, "match_pairs"),
                "unit": self._copy(lang, "unit_review"),
                "prompt": self._copy(lang, "match_pairs"),
                "pairs": pairs,
                "source_words": [pair[0] for pair in pairs],
                "required": True,
            }
        dialog_card = self._short_dialog_card(focus_words, lang=lang)
        if dialog_card:
            activities["dialog"] = dialog_card

        purpose = str(payload.get("section_purpose") or self._section_purpose(payload.get("section_no") or 1, payload.get("section_count") or 1))
        pattern = self._section_purpose_pattern(purpose)
        word_map = {card["id"]: card for card in words}
        cards = []
        for key in pattern:
            card = word_map.get(key) or activities.get(key)
            if card and card not in cards:
                cards.append(card)
        fallback = [*words, *activities.values()]
        for card in fallback:
            if card not in cards:
                cards.append(card)
        return self._validate_cards(cards, active_words)

    async def get_flow(
        self,
        telegram_id: int,
        *,
        level: str,
        lesson_order: int,
        lang: str,
        section_key: str | int | None = None,
        client_completed_sections=None,
    ) -> dict:
        user, _progress, lesson, error = await self._context(
            telegram_id,
            level=level,
            lesson_order=lesson_order,
        )
        if error:
            return {"ok": False, "error": error}

        payload = await self.lesson_service.get_payload(
            lesson_order=int(lesson.lesson_order),
            lang=lang,
            level=str(lesson.level),
        )
        if not payload:
            return {"ok": False, "error": "lesson_not_found"}
        sections = self._section_plan(payload, level=str(lesson.level), lesson_order=int(lesson.lesson_order), lang=lang)
        section = self._section_by_key(sections, section_key, lesson_order=int(lesson.lesson_order))
        if not section:
            return {"ok": False, "error": "course_section_not_found"}
        completed_sections = await self._completed_section_keys(telegram_id=telegram_id, lesson_id=lesson.id)
        completed_sections |= self._section_keys_before(
            section,
            self._client_completed_section_keys(sections, client_completed_sections),
        )
        if not self._section_unlocked(section, completed_sections):
            return {"ok": False, "error": "course_section_not_unlocked"}
        section_payload = self._section_payload(payload, section)
        cards = self._build_cards(section_payload, lang=lang, lesson_order=lesson.lesson_order)
        if not cards:
            return {"ok": False, "error": "course_lesson_has_no_activities"}

        analytics = CourseMiniAppAnalyticsService(self.session)
        chapter_key = str(section["chapter_key"])
        await analytics.record_server_event(
            event_name="chapter_started",
            telegram_id=telegram_id,
            user_id=user.id,
            level=str(lesson.level),
            lesson_id=lesson.id,
            lesson_order=lesson.lesson_order,
            dedupe_key=f"chapter:{lesson.id}:{chapter_key}:started",
            payload={
                "chapter_key": chapter_key,
                "chapter_label": section["chapter_label"],
                "flow_version": LESSON_FLOW_VERSION,
            },
        )
        await analytics.record_server_event(
            event_name="section_started",
            telegram_id=telegram_id,
            user_id=user.id,
            level=str(lesson.level),
            lesson_id=lesson.id,
            lesson_order=lesson.lesson_order,
            dedupe_key=f"section:{lesson.id}:{section['section_key']}:started",
            payload={
                "section_key": section["section_key"],
                "section_no": section["section_no"],
                "section_count": section["section_count"],
                "chapter_key": chapter_key,
                "chapter_label": section["chapter_label"],
                "flow_version": LESSON_FLOW_VERSION,
                "card_count": len(cards),
            },
        )
        await analytics.record_server_event(
            event_name="lesson_started",
            telegram_id=telegram_id,
            user_id=user.id,
            level=str(lesson.level),
            lesson_id=lesson.id,
            lesson_order=lesson.lesson_order,
            dedupe_key=f"lesson:{lesson.id}:started",
            payload={"flow_version": LESSON_FLOW_VERSION, "card_count": len(cards), "section_key": section["section_key"]},
        )
        await self.session.commit()
        return {
            "ok": True,
            "flow": {
                "id": f"lesson:{lesson.id}:{section['section_key']}:v{LESSON_FLOW_VERSION}",
                "version": LESSON_FLOW_VERSION,
                "level": str(lesson.level),
                "lesson_id": int(lesson.lesson_order),
                "book_lesson_order": int(lesson.lesson_order),
                "section_key": section["section_key"],
                "section_no": section["section_no"],
                "section_count": section["section_count"],
                "section_purpose": section["section_purpose"],
                "section_title": section["section_title"],
                "active_words": self._word_refs(section.get("active_words", [])),
                "chapter_key": chapter_key,
                "chapter_label": section["chapter_label"],
                "chapter_no": section["chapter_no"],
                "chapter_start": section["chapter_start"],
                "chapter_end": section["chapter_end"],
                "title": str(payload.get("title") or ""),
                "cards": cards,
            },
        }

    @staticmethod
    def _response_is_correct(card: dict, response: dict) -> tuple[bool, bool]:
        card_type = str(card.get("type") or "")
        if card_type in {"active_word", "match_pairs", "pronunciation"}:
            return bool(response.get("completed")), False
        if card_type in {
            "meaning_guess",
            "pinyin_choice",
            "hanzi_choice",
            "listening_choice",
            "gap_fill",
            "character_recognition",
            "translation_choice",
            "quick_quiz",
            "dialog_context",
        }:
            try:
                selected = int(response.get("selected_index"))
            except (TypeError, ValueError):
                return False, True
            return selected == int(card.get("correct_index", -1)), True
        if card_type in {"sentence_builder", "word_order"}:
            actual = [str(item) for item in response.get("answer_tokens", [])]
            expected = [str(item) for item in card.get("answer_tokens", [])]
            return bool(expected and actual == expected), True
        return False, False

    async def complete_flow(
        self,
        telegram_id: int,
        *,
        level: str,
        lesson_order: int,
        lang: str,
        responses: list,
        section_key: str | int | None = None,
        client_completed_sections=None,
    ) -> dict:
        user, progress, lesson, error = await self._context(
            telegram_id,
            level=level,
            lesson_order=lesson_order,
        )
        if error:
            return {"ok": False, "error": error}
        payload = await self.lesson_service.get_payload(
            lesson_order=int(lesson.lesson_order),
            lang=lang,
            level=str(lesson.level),
        )
        sections = self._section_plan(payload or {}, level=str(lesson.level), lesson_order=int(lesson.lesson_order), lang=lang)
        section = self._section_by_key(sections, section_key, lesson_order=int(lesson.lesson_order))
        if not section:
            return {"ok": False, "error": "course_section_not_found"}
        completed_sections = await self._completed_section_keys(telegram_id=telegram_id, lesson_id=lesson.id)
        completed_sections |= self._section_keys_before(
            section,
            self._client_completed_section_keys(sections, client_completed_sections),
        )
        if not self._section_unlocked(section, completed_sections):
            return {"ok": False, "error": "course_section_not_unlocked"}
        cards = self._build_cards(
            self._section_payload(payload or {}, section),
            lang=lang,
            lesson_order=lesson.lesson_order,
        )
        required_cards = [card for card in cards if card.get("required")]

        response_map = {}
        for response in responses if isinstance(responses, list) else []:
            if not isinstance(response, dict):
                continue
            card_id = str(response.get("card_id") or "")
            if card_id and card_id not in response_map:
                response_map[card_id] = response
        if set(response_map) != {str(card.get("id")) for card in required_cards}:
            return {"ok": False, "error": "lesson_required_activities_incomplete"}

        graded = []
        correct_count = 0
        wrong_items = []
        for card in required_cards:
            response = response_map[str(card["id"])]
            correct, scored = self._response_is_correct(card, response)
            if scored:
                graded.append(correct)
                correct_count += int(correct)
                if not correct:
                    card_type = str(card.get("type") or "")
                    if "selected_index" in response:
                        try:
                            selected_index = int(response.get("selected_index"))
                        except (TypeError, ValueError):
                            selected_index = -1
                        options = card.get("options") or []
                        user_answer = options[selected_index] if 0 <= selected_index < len(options) else ""
                        correct_index = int(card.get("correct_index", -1))
                        correct_answer = options[correct_index] if 0 <= correct_index < len(options) else ""
                    else:
                        user_answer = " ".join(str(item) for item in response.get("answer_tokens", []))
                        correct_answer = " ".join(str(item) for item in card.get("answer_tokens", []))
                    wrong_items.append(
                        {
                            "question": str(card.get("prompt") or card.get("title") or ""),
                            "selected_answer": user_answer,
                            "correct_answer": correct_answer,
                            "explanation": str(card.get("explanation") or ""),
                            "type": card_type,
                        }
                    )
        if not graded:
            return {"ok": False, "error": "course_lesson_has_no_graded_activities"}
        percent = round((correct_count / len(graded)) * 100)
        await self.mistakes.record_items(
            user,
            wrong_items,
            source="lesson",
            level=str(lesson.level),
            lesson_id=lesson.id,
            lesson_order=lesson.lesson_order,
        )
        if percent < 60:
            await self.session.commit()
            return {
                "ok": False,
                "error": "lesson_score_too_low",
                "percent": percent,
                "correct": correct_count,
                "total": len(graded),
            }

        access_result = await CourseMiniAppAccessService(self.session).consume_free_use(
            user,
            feature_key="lesson",
            usage_ref=f"section:{lesson.id}:{section['section_key']}:v{LESSON_FLOW_VERSION}",
        )
        if not access_result.get("allowed"):
            return {"ok": False, "error": access_result.get("error") or "free_feature_limit_reached"}

        section_reward = await self.gamification.award(
            user,
            activity_type="section",
            activity_ref=f"section:{lesson.id}:{section['section_key']}:v{LESSON_FLOW_VERSION}",
            base_xp=8,
            level=str(lesson.level),
        )
        completed_after = {section["section_key"], *completed_sections}
        chapter_sections = [
            item["section_key"]
            for item in sections
            if item["chapter_key"] == section["chapter_key"]
        ]
        chapter_completed = all(item in completed_after for item in chapter_sections)
        book_lesson_completed = all(item["section_key"] in completed_after for item in sections)
        chapter_reward = None
        book_reward = None
        level_completed = False
        completed_level = None
        next_level = None
        next_level_ref = None
        completion_praise = None
        result = {
            "ok": True,
            "completed_lesson": None,
            "next_lesson": None,
            "completed_lessons_count": None,
        }
        if chapter_completed:
            chapter_reward = await self.gamification.award(
                user,
                activity_type="chapter",
                activity_ref=f"chapter:{lesson.id}:{section['chapter_key']}:v{LESSON_FLOW_VERSION}",
                base_xp=12,
                level=str(lesson.level),
            )
        if book_lesson_completed:
            if self._book_lesson_already_completed(lesson, progress):
                next_lesson = await self.lesson_repo.get_next_lesson(
                    level=str(lesson.level),
                    lesson_order=int(lesson.lesson_order),
                )
                result = {
                    "ok": True,
                    "completed_lesson": int(lesson.lesson_order),
                    "next_lesson": getattr(next_lesson, "lesson_order", None),
                    "completed_lessons_count": self._progress_completed_count(progress),
                }
            else:
                result = await StudyMiniAppService(self.session).complete_v2_lesson(
                    telegram_id,
                    level=self._content_level(level),
                    lesson_order=int(lesson.lesson_order),
                    percent=percent,
                )
                if not result.get("ok"):
                    return result
            book_reward = await self.gamification.award(
                user,
                activity_type="book_lesson",
                activity_ref=f"book-lesson:{lesson.id}:v{LESSON_FLOW_VERSION}",
                base_xp=20,
                level=str(lesson.level),
            )
            requested_level = str(level or "").strip().lower() or self._content_level(str(lesson.level))
            same_content_next_order = result.get("next_lesson")
            split_next_level = self._next_requested_level(requested_level, same_content_next_order)
            if split_next_level and same_content_next_order:
                next_level = split_next_level
                completed_level = requested_level
                next_level_ref = self._decorate_next_ref(
                    self._book_lesson_ref(same_content_next_order),
                    requested_level=next_level,
                    content_level=str(lesson.level),
                )
                level_completed = True
            elif not same_content_next_order:
                target_next_level = self._next_requested_level(requested_level)
                if target_next_level:
                    engine = CourseEngineService(self.session)
                    _, updated_progress, _, promoted_lesson, promote_error = await engine.advance_to_next_level(
                        telegram_id
                    )
                    if not promote_error and promoted_lesson:
                        next_level = "hsk4a" if str(getattr(promoted_lesson, "level", "")).lower() == "hsk4" else str(getattr(promoted_lesson, "level", "") or target_next_level)
                        if requested_level == "hsk4a":
                            next_level = "hsk4b"
                        completed_level = requested_level
                        next_level_ref = self._next_level_ref(promoted_lesson, requested_level=next_level)
                        level_completed = True
                        result["next_lesson"] = getattr(promoted_lesson, "lesson_order", None)
                        result["completed_lessons_count"] = getattr(updated_progress, "completed_lessons_count", 0)
            if level_completed:
                completion_praise = self._level_completion_praise(
                    lang=lang,
                    completed_level=completed_level or requested_level,
                    next_level=next_level,
                    completed_lessons_count=int(result.get("completed_lesson") or lesson.lesson_order or 1),
                    completed_sections_count=int(lesson.lesson_order or 1) * len(sections),
                    percent=percent,
                    mistakes=max(0, len(graded) - correct_count),
                )

        analytics = CourseMiniAppAnalyticsService(self.session)
        for card in required_cards:
            await analytics.record_server_event(
                event_name="interaction_completed",
                telegram_id=telegram_id,
                user_id=user.id,
                level=str(lesson.level),
                lesson_id=lesson.id,
                lesson_order=lesson.lesson_order,
                dedupe_key=f"section:{lesson.id}:{section['section_key']}:card:{card['id']}",
                payload={
                    "section_key": section["section_key"],
                    "chapter_key": section["chapter_key"],
                    "card_id": card["id"],
                    "card_type": card["type"],
                },
            )
        await analytics.record_server_event(
            event_name="section_completed",
            telegram_id=telegram_id,
            user_id=user.id,
            level=str(lesson.level),
            lesson_id=lesson.id,
            lesson_order=lesson.lesson_order,
            dedupe_key=f"section:{lesson.id}:{section['section_key']}:completed",
            payload={
                "section_key": section["section_key"],
                "section_no": section["section_no"],
                "section_count": section["section_count"],
                "chapter_key": section["chapter_key"],
                "chapter_label": section["chapter_label"],
                "percent": percent,
                "correct": correct_count,
                "total": len(graded),
                "flow_version": LESSON_FLOW_VERSION,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        if chapter_completed:
            await analytics.record_server_event(
                event_name="chapter_completed",
                telegram_id=telegram_id,
                user_id=user.id,
                level=str(lesson.level),
                lesson_id=lesson.id,
                lesson_order=lesson.lesson_order,
                dedupe_key=f"chapter:{lesson.id}:{section['chapter_key']}:completed",
                payload={
                    "chapter_key": section["chapter_key"],
                    "chapter_label": section["chapter_label"],
                    "section_count": len(chapter_sections),
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        if book_lesson_completed:
            book_payload = {
                "section_count": len(sections),
                "percent": percent,
                "correct": correct_count,
                "total": len(graded),
                "flow_version": LESSON_FLOW_VERSION,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
            await analytics.record_server_event(
                event_name="book_lesson_completed",
                telegram_id=telegram_id,
                user_id=user.id,
                level=str(lesson.level),
                lesson_id=lesson.id,
                lesson_order=lesson.lesson_order,
                dedupe_key=f"book-lesson:{lesson.id}:completed",
                payload=book_payload,
            )
            await analytics.record_server_event(
                event_name="lesson_completed",
                telegram_id=telegram_id,
                user_id=user.id,
                level=str(lesson.level),
                lesson_id=lesson.id,
                lesson_order=lesson.lesson_order,
                dedupe_key=f"lesson:{lesson.id}:completed",
                payload=book_payload,
            )
        if level_completed:
            await analytics.record_server_event(
                event_name="level_completed",
                telegram_id=telegram_id,
                user_id=user.id,
                level=str(lesson.level),
                lesson_id=lesson.id,
                lesson_order=lesson.lesson_order,
                dedupe_key=f"level:{completed_level or level}:completed:v{LESSON_FLOW_VERSION}",
                payload={
                    "completed_level": completed_level,
                    "next_level": next_level,
                    "next_section": next_level_ref,
                    "percent": percent,
                    "correct": correct_count,
                    "total": len(graded),
                    "flow_version": LESSON_FLOW_VERSION,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        await self.session.commit()
        next_section = next(
            (item for item in sections if int(item["section_no"]) == int(section["section_no"]) + 1),
            None,
        )
        next_section_ref = self._section_ref(next_section, lesson_order=int(lesson.lesson_order))
        next_book_lesson_ref = self._book_lesson_ref(result.get("next_lesson")) if book_lesson_completed else None
        if next_level_ref:
            next_book_lesson_ref = next_level_ref
        return {
            **result,
            "percent": percent,
            "correct": correct_count,
            "total": len(graded),
            "wrong_items": wrong_items,
            "reward": book_reward or chapter_reward or section_reward,
            "section_reward": section_reward,
            "chapter_reward": chapter_reward,
            "book_lesson_reward": book_reward,
            "section_key": section["section_key"],
            "section_no": section["section_no"],
            "section_count": section["section_count"],
            "section_purpose": section["section_purpose"],
            "section_title": section["section_title"],
            "chapter_key": section["chapter_key"],
            "chapter_label": section["chapter_label"],
            "chapter_completed": chapter_completed,
            "book_lesson_completed": book_lesson_completed,
            "level_completed": level_completed,
            "completed_level": completed_level,
            "next_level": next_level,
            "completion_praise": completion_praise,
            "next_section": next_section_ref,
            "next_section_key": next_section_ref["section_key"] if next_section_ref else None,
            "next_book_lesson": next_book_lesson_ref,
        }
