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
from app.services.course_gamification_service import CourseGamificationService
from app.services.course_trial_service import CourseTrialService
from app.services.study_miniapp_service import StudyMiniAppService


LESSON_FLOW_VERSION = 2
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
        }
        return fallback_map.get(normalized, ("hsk1",))

    @staticmethod
    def _copy(lang: str, key: str) -> str:
        copy = {
            "ru": {
                "active_word": "Новое активное слово",
                "meaning_guess": "Выберите правильное значение",
                "listening_choice": "Послушайте и выберите ответ",
                "sentence_builder": "Соберите предложение",
                "word_order": "Расставьте слова по порядку",
                "translation_choice": "Выберите правильный перевод",
                "pronunciation": "Произнесите фразу вслух",
                "quick_quiz": "Быстрая проверка",
                "short_dialog": "Короткий диалог",
            },
            "tj": {
                "active_word": "Калимаи нави фаъол",
                "meaning_guess": "Маънои дурустро интихоб кунед",
                "listening_choice": "Гӯш кунед ва ҷавобро интихоб кунед",
                "sentence_builder": "Ҷумларо созед",
                "word_order": "Калимаҳоро бо тартиб гузоред",
                "translation_choice": "Тарҷумаи дурустро интихоб кунед",
                "pronunciation": "Ибораро бо овози баланд гӯед",
                "quick_quiz": "Санҷиши зуд",
                "short_dialog": "Муколамаи кӯтоҳ",
            },
            "uz": {
                "active_word": "Yangi faol so'z",
                "meaning_guess": "To'g'ri ma'noni tanlang",
                "listening_choice": "Tinglang va javobni tanlang",
                "sentence_builder": "Gapni tuzing",
                "word_order": "So'zlarni tartibga qo'ying",
                "translation_choice": "To'g'ri tarjimani tanlang",
                "pronunciation": "Iborani ovoz chiqarib ayting",
                "quick_quiz": "Tezkor tekshiruv",
                "short_dialog": "Qisqa dialog",
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

    @classmethod
    def _section_plan(cls, payload: dict, *, level: str, lesson_order: int) -> list[dict]:
        sections = []
        chunks = cls._split_words(
            [item for item in payload.get("vocabulary", []) if isinstance(item, dict)],
            level=level,
        )
        total = len(chunks)
        for index, words in enumerate(chunks, 1):
            chapter = cls._chapter_for_section(index)
            sections.append(
                {
                    "section_key": f"{lesson_order}.{index}",
                    "section_no": index,
                    "section_count": total,
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
        if raw.startswith(f"{lesson_order}."):
            return raw
        if raw.isdigit():
            return f"{lesson_order}.{int(raw)}"
        return f"{lesson_order}.1"

    @classmethod
    def _section_by_key(cls, sections: list[dict], value: str | int | None, *, lesson_order: int) -> dict:
        key = cls._normalize_section_key(value, lesson_order=lesson_order)
        return next((item for item in sections if item["section_key"] == key), sections[0])

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

    @staticmethod
    def _section_unlocked(section: dict, completed: set[str]) -> bool:
        section_no = int(section.get("section_no") or 1)
        if section_no <= 1:
            return True
        previous_key = f"{str(section.get('section_key')).split('.', 1)[0]}.{section_no - 1}"
        return previous_key in completed

    @staticmethod
    def _section_payload(payload: dict, section: dict) -> dict:
        active_words = [item for item in section.get("active_words", []) if isinstance(item, dict)]
        return {
            **payload,
            "vocabulary": active_words,
            "quiz_questions": [],
            "reinforcement_tasks": [],
        }

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
            "prompt": prompt,
            "dialog": [
                {"speaker": "A", "text": "你去哪儿？"},
                {"speaker": "B", "text": f"我去{target['zh']}。"},
            ],
            "options": options,
            "correct_index": correct,
            "explanation": f"{target['zh']} = {target.get('meaning') or ''}",
            "required": True,
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

        access = CourseMiniAppAccessService(self.session)
        trial = CourseTrialService(self.session)
        paid = access.is_paid_user(user)
        entitlements = await access.get_entitlements(user)
        if not paid:
            if not entitlements.get("lesson", {}).get("allowed"):
                return user, None, lesson, "free_feature_limit_reached"
            if not await trial.ensure_trial_lesson(user, lesson.id):
                return user, None, lesson, "free_feature_limit_reached"

        progress = await self.progress_repo.get_by_user_id(user.id, for_update=True)
        if not progress:
            progress = await self.progress_repo.create(
                user_id=user.id,
                level=str(lesson.level),
                current_lesson_id=lesson.id,
                current_step="intro",
                waiting_for="none",
            )
        elif int(getattr(progress, "current_lesson_id", 0) or 0) != int(lesson.id):
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
        return {
            "id": card_id,
            "type": card_type,
            "title": title,
            "prompt": str(question.get("q") or question.get("prompt") or title),
            "sentence": str(question.get("sentence") or question.get("source") or ""),
            "audio_text": str(question.get("audioText") or ""),
            "options": [str(option) for option in options],
            "correct_index": correct_index,
            "explanation": str(question.get("expl") or question.get("explanation") or ""),
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
            "required": True,
        }

    def _build_cards(self, payload: dict, *, lang: str, lesson_order: int) -> list[dict]:
        vocab = [item for item in payload.get("vocabulary", []) if isinstance(item, dict)]
        active_words = vocab[: 3 + (int(lesson_order) % 2)]
        words = []
        for index, word in enumerate(active_words, 1):
            words.append(
                {
                    "id": f"word:{index}",
                    "type": "active_word",
                    "title": self._copy(lang, "active_word"),
                    "word": {
                        "zh": str(word.get("zh") or ""),
                        "pinyin": str(word.get("pinyin") or ""),
                        "meaning": str(word.get("meaning") or ""),
                        "pos": str(word.get("pos") or ""),
                    },
                    "required": True,
                }
            )

        questions = [item for item in payload.get("quiz_questions", []) if isinstance(item, dict)]
        tasks = [item for item in payload.get("reinforcement_tasks", []) if isinstance(item, dict)]
        choices = [item for item in questions if isinstance(item.get("opts") or item.get("options"), list)]
        if len(choices) < 3 and len(active_words) >= 2:
            meaning_options = [str(item.get("meaning") or "") for item in active_words]
            for index, word in enumerate(active_words):
                if not word.get("zh") or not meaning_options[index]:
                    continue
                choices.append(
                    {
                        "type": "multiple_choice",
                        "subtype": "hanzi_to_meaning",
                        "q": f"{word['zh']} — ?",
                        "opts": meaning_options,
                        "ans": index,
                        "expl": f"{word['zh']} = {meaning_options[index]}",
                    }
                )
                if len(choices) >= 3:
                    break
        listening = next(
            (item for item in [*questions, *tasks] if str(item.get("type") or "") in {"listening_choice", "listen_and_fill"}),
            None,
        )
        if not listening and len(active_words) >= 2:
            options = [str(item.get("zh") or "") for item in active_words if item.get("zh")]
            listening = {
                "type": "listening_choice",
                "q": self._copy(lang, "listening_choice"),
                "audioText": options[0],
                "opts": options,
                "ans": 0,
                "expl": f"{active_words[0].get('zh') or ''} = {active_words[0].get('meaning') or ''}",
            }
        order_tasks = [
            item
            for item in [*questions, *tasks]
            if str(item.get("type") or "")
            in {"word_order", "build_chinese_sentence", "build_sentence_chips"}
        ]
        grammar = [item for item in payload.get("grammar", []) if isinstance(item, dict)]
        for grammar_item in grammar:
            examples = grammar_item.get("examples") if isinstance(grammar_item.get("examples"), list) else []
            example = next((item for item in examples if isinstance(item, dict) and item.get("zh")), None)
            if not example:
                continue
            zh = str(example.get("zh") or "")
            zh_tokens = [char for char in zh if "\u4e00" <= char <= "\u9fff"]
            translation_tokens = [
                token.strip(".,!?;:")
                for token in str(example.get("translation") or "").split()
                if token.strip(".,!?;:")
            ]
            if len(zh_tokens) >= 2 and len(order_tasks) < 2:
                order_tasks.append(
                    {
                        "type": "build_chinese_sentence",
                        "prompt": self._copy(lang, "sentence_builder"),
                        "source": str(example.get("translation") or ""),
                        "tokens": [*zh_tokens[1:], zh_tokens[0]],
                        "answer": zh_tokens,
                        "explanation": zh,
                    }
                )
            if len(translation_tokens) >= 2 and len(order_tasks) < 2:
                order_tasks.append(
                    {
                        "type": "word_order",
                        "prompt": self._copy(lang, "word_order"),
                        "source": zh,
                        "tokens": [*translation_tokens[1:], translation_tokens[0]],
                        "answer": translation_tokens,
                        "explanation": str(example.get("translation") or ""),
                    }
                )
            if len(order_tasks) >= 2:
                break
        if len(order_tasks) < 2 and len(active_words) >= 2:
            fallback_tokens = [str(item.get("zh") or "") for item in active_words if item.get("zh")]
            while len(order_tasks) < 2:
                order_tasks.append(
                    {
                        "type": "build_chinese_sentence",
                        "prompt": self._copy(lang, "sentence_builder"),
                        "tokens": [*fallback_tokens[1:], fallback_tokens[0]],
                        "answer": fallback_tokens,
                        "explanation": " · ".join(fallback_tokens),
                    }
                )

        activities: dict[str, dict] = {}
        meaning_source = next(
            (item for item in choices if str(item.get("subtype") or item.get("type") or "") in {"hanzi_to_meaning", "choose_meaning_in_context"}),
            choices[0] if choices else None,
        )
        if meaning_source:
            card = self._choice_card(
                meaning_source,
                card_id="activity:meaning",
                card_type="meaning_guess",
                title=self._copy(lang, "meaning_guess"),
            )
            if card:
                activities["meaning"] = card

        if listening:
            card = self._choice_card(
                listening,
                card_id="activity:listening",
                card_type="listening_choice",
                title=self._copy(lang, "listening_choice"),
            )
            if card:
                activities["listening"] = card

        if order_tasks:
            card = self._order_card(
                order_tasks[0],
                card_id="activity:builder",
                card_type="sentence_builder",
                title=self._copy(lang, "sentence_builder"),
            )
            if card:
                activities["builder"] = card
            card = self._order_card(
                order_tasks[1] if len(order_tasks) > 1 else order_tasks[0],
                card_id="activity:order",
                card_type="word_order",
                title=self._copy(lang, "word_order"),
            )
            if card:
                activities["order"] = card

        used_choice_ids = {id(meaning_source), id(listening)}
        remaining_choices = [item for item in choices if id(item) not in used_choice_ids]
        if remaining_choices:
            card = self._choice_card(
                remaining_choices[0],
                card_id="activity:translation",
                card_type="translation_choice",
                title=self._copy(lang, "translation_choice"),
            )
            if card:
                activities["translation"] = card
        if len(remaining_choices) > 1:
            card = self._choice_card(
                remaining_choices[-1],
                card_id="activity:quiz",
                card_type="quick_quiz",
                title=self._copy(lang, "quick_quiz"),
            )
            if card:
                activities["quiz"] = card

        pronunciation_word = active_words[0] if active_words else {}
        if pronunciation_word.get("zh"):
            activities["pronunciation"] = {
                "id": "activity:pronunciation",
                "type": "pronunciation",
                "title": self._copy(lang, "pronunciation"),
                "phrase": str(pronunciation_word.get("zh") or ""),
                "pinyin": str(pronunciation_word.get("pinyin") or ""),
                "translation": str(pronunciation_word.get("meaning") or ""),
                "required": True,
            }
        dialog_card = self._short_dialog_card(active_words, lang=lang)
        if dialog_card:
            activities["dialog"] = dialog_card

        patterns = (
            ["word:1", "word:2", "meaning", "dialog", "word:3", "listening", "word:4", "builder", "pronunciation", "order", "translation", "quiz"],
            ["word:1", "listening", "word:2", "dialog", "meaning", "word:3", "order", "word:4", "translation", "builder", "pronunciation", "quiz"],
            ["word:1", "meaning", "word:2", "builder", "dialog", "word:3", "listening", "word:4", "pronunciation", "quiz", "order", "translation"],
        )
        pattern = patterns[(int(lesson_order) - 1) % len(patterns)]
        word_map = {card["id"]: card for card in words}
        cards = []
        for key in pattern:
            card = word_map.get(key) or activities.get(key)
            if card and card not in cards:
                cards.append(card)
        for card in [*words, *activities.values()]:
            if card not in cards:
                cards.append(card)
        return cards

    async def get_flow(
        self,
        telegram_id: int,
        *,
        level: str,
        lesson_order: int,
        lang: str,
        section_key: str | int | None = None,
    ) -> dict:
        user, _, lesson, error = await self._context(
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
        sections = self._section_plan(payload, level=str(lesson.level), lesson_order=int(lesson.lesson_order))
        section = self._section_by_key(sections, section_key, lesson_order=int(lesson.lesson_order))
        completed_sections = await self._completed_section_keys(telegram_id=telegram_id, lesson_id=lesson.id)
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
        if card_type in {"active_word", "pronunciation"}:
            return bool(response.get("completed")), False
        if card_type in {"meaning_guess", "listening_choice", "translation_choice", "quick_quiz", "dialog_context"}:
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
    ) -> dict:
        user, _, lesson, error = await self._context(
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
        sections = self._section_plan(payload or {}, level=str(lesson.level), lesson_order=int(lesson.lesson_order))
        section = self._section_by_key(sections, section_key, lesson_order=int(lesson.lesson_order))
        completed_sections = await self._completed_section_keys(telegram_id=telegram_id, lesson_id=lesson.id)
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
        await self.session.commit()
        next_section = next(
            (item for item in sections if int(item["section_no"]) == int(section["section_no"]) + 1),
            None,
        )
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
            "chapter_key": section["chapter_key"],
            "chapter_label": section["chapter_label"],
            "chapter_completed": chapter_completed,
            "book_lesson_completed": book_lesson_completed,
            "next_section": next_section["section_key"] if next_section else None,
        }
