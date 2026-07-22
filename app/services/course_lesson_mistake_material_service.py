"""Server-authoritative material for Course v3 lesson mistakes.

The lesson UI reports only a stable card reference plus the learner's selected
option/tokens. This service resolves that reference against the checked-in
lesson JSON and derives the prompt and answer key on the server.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


LESSON_MISTAKE_MATERIAL_VERSION = 2
LESSON_MATERIAL_LANGUAGES = {"uz", "ru", "tj"}
LESSON_MATERIAL_LEVELS = {"hsk1", "hsk2", "hsk3", "hsk4"}
LESSON_STATIC_DIR = Path(__file__).resolve().parents[1] / "static" / "course_v3_data"
_MATERIAL_REF_RE = re.compile(
    r"^lesson:(hsk[1-4]):(\d+):section:(\d+):card:(\d+)$"
)


class CourseLessonMistakeMaterialError(ValueError):
    """Raised when the canonical lesson source itself cannot be loaded."""


class CourseLessonMistakeMaterialService:
    @staticmethod
    def normalize_level(value: str) -> str:
        level = str(value or "").strip().lower()
        if level in {"hsk4a", "hsk4b"}:
            level = "hsk4"
        if level not in LESSON_MATERIAL_LEVELS:
            raise CourseLessonMistakeMaterialError("Unsupported lesson level")
        return level

    @staticmethod
    def normalize_language(value: str) -> str:
        lang = str(value or "").strip().lower()
        if lang not in LESSON_MATERIAL_LANGUAGES:
            raise CourseLessonMistakeMaterialError("Unsupported lesson language")
        return lang

    @staticmethod
    def material_ref(level: str, lesson_order: int, section_no: int, card_no: int) -> str:
        return (
            f"lesson:{level}:{int(lesson_order)}:"
            f"section:{int(section_no)}:card:{int(card_no)}"
        )

    @staticmethod
    def _text(value: Any, limit: int = 4000) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]

    @classmethod
    def _localized(cls, value: Any, lang: str, limit: int = 4000) -> str:
        if isinstance(value, dict):
            value = value.get(lang)
        return cls._text(value, limit)

    @classmethod
    def _localized_list(cls, value: Any, lang: str) -> list[str]:
        if isinstance(value, dict):
            value = value.get(lang)
        if not isinstance(value, list):
            return []
        result = []
        for raw in value:
            item = cls._localized(raw, lang)
            if item:
                result.append(item)
        return result

    @classmethod
    def _load_lesson(cls, level: str, lesson_order: int) -> dict:
        path = LESSON_STATIC_DIR / level / f"lesson_{int(lesson_order):02d}.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise CourseLessonMistakeMaterialError("Lesson material is unavailable") from error
        if not isinstance(data, dict):
            raise CourseLessonMistakeMaterialError("Lesson material is invalid")
        if cls.normalize_level(data.get("level")) != level:
            raise CourseLessonMistakeMaterialError("Lesson material level mismatch")
        try:
            source_order = int(data.get("lesson_id") or 0)
        except (TypeError, ValueError) as error:
            raise CourseLessonMistakeMaterialError("Lesson material id is invalid") from error
        if source_order != int(lesson_order):
            raise CourseLessonMistakeMaterialError("Lesson material id mismatch")
        return data

    @classmethod
    def _card_lookup(cls, data: dict, level: str, lesson_order: int) -> dict[str, dict]:
        lookup: dict[str, dict] = {}
        sections = data.get("sections")
        if not isinstance(sections, list):
            raise CourseLessonMistakeMaterialError("Lesson sections are invalid")
        for section_position, section in enumerate(sections, 1):
            if not isinstance(section, dict):
                continue
            try:
                section_no = int(section.get("section_no") or section_position)
            except (TypeError, ValueError):
                continue
            cards = section.get("cards")
            if not isinstance(cards, list):
                continue
            for card_no, card in enumerate(cards, 1):
                if not isinstance(card, dict):
                    continue
                ref = cls.material_ref(level, lesson_order, section_no, card_no)
                lookup[ref] = {
                    "card": card,
                    "section": section,
                    "section_no": section_no,
                    "card_no": card_no,
                }
        return lookup

    @classmethod
    def _category(cls, card: dict, section: dict) -> str:
        card_type = cls._text(card.get("type"), 64).lower()
        purpose = cls._text(section.get("section_purpose"), 64).lower()
        if card_type in {"listening_choice", "pronunciation"}:
            return "pronunciation"
        if card_type in {"hanzi_choice", "pinyin_choice"}:
            return "character"
        if purpose == "grammar" or card_type in {
            "sentence_builder",
            "reverse_builder",
            "gap_fill",
            "dialog_cloze",
            "dialog_context",
        }:
            return "grammar"
        return "word"

    @classmethod
    def _source(
        cls,
        *,
        level: str,
        lesson_order: int,
        section_no: int,
        card_no: int,
        material_ref: str,
        source_schema_version: int,
    ) -> dict:
        return {
            "kind": "lesson",
            "trusted": False,
            "level": level,
            "lesson": int(lesson_order),
            "section": int(section_no),
            "card": int(card_no),
            "material_ref": material_ref,
            "source_schema_version": int(source_schema_version or 1),
        }

    @classmethod
    def _base_material(
        cls,
        *,
        card: dict,
        section: dict,
        level: str,
        lesson_order: int,
        lang: str,
        section_no: int,
        card_no: int,
        material_ref: str,
        source_schema_version: int,
    ) -> dict:
        card_type = cls._text(card.get("type"), 64).lower()
        return {
            "material_version": LESSON_MISTAKE_MATERIAL_VERSION,
            "material_ref": material_ref,
            "format": card_type,
            "category": cls._category(card, section),
            "language": lang,
            "prompt": cls._localized(card.get("prompt"), lang)
            or cls._localized(card.get("title"), lang),
            "sentence": cls._localized(card.get("sentence"), lang),
            "audio_text": cls._text(card.get("audio_text")),
            "pinyin": cls._text(card.get("pinyin")),
            "explanation": cls._localized(card.get("explanation"), lang),
            "source": cls._source(
                level=level,
                lesson_order=lesson_order,
                section_no=section_no,
                card_no=card_no,
                material_ref=material_ref,
                source_schema_version=source_schema_version,
            ),
        }

    @classmethod
    def _selected_choice(cls, raw: dict, options: list[str]) -> str | None:
        selected_by_index = None
        if "selected_index" in raw:
            value = raw.get("selected_index")
            if isinstance(value, bool):
                return None
            try:
                selected_index = int(value)
            except (TypeError, ValueError):
                return None
            if not 0 <= selected_index < len(options):
                return None
            selected_by_index = options[selected_index]

        selected_by_text = None
        if raw.get("selected_answer") is not None:
            selected_by_text = cls._text(raw.get("selected_answer"))
            if selected_by_text not in options:
                return None
        if selected_by_index is not None and selected_by_text is not None:
            return selected_by_index if selected_by_index == selected_by_text else None
        return selected_by_index if selected_by_index is not None else selected_by_text

    @classmethod
    def _choice_item(cls, raw: dict, card: dict, material: dict, lang: str) -> dict | None:
        options = cls._localized_list(card.get("options"), lang)
        try:
            answer_index = int(card.get("correct_index"))
        except (TypeError, ValueError):
            return None
        if len(options) < 2 or not 0 <= answer_index < len(options):
            return None
        selected_answer = cls._selected_choice(raw, options)
        if selected_answer is None:
            return None
        correct_answer = options[answer_index]
        if selected_answer == correct_answer:
            return None
        material.update(
            {
                "options": options,
                "correct_answer": correct_answer,
                "answer_index": answer_index,
            }
        )
        return {
            "question_id": material["material_ref"],
            "question": material["prompt"] or material["sentence"] or material["format"],
            "selected_answer": selected_answer,
            "correct_answer": correct_answer,
            "explanation": material["explanation"],
            "category": material["category"],
            "format": material["format"],
            "language": material["language"],
            "sentence": material["sentence"],
            "audio_text": material["audio_text"],
            "pinyin": material["pinyin"],
            "material_ref": material["material_ref"],
            "material": material,
        }

    @classmethod
    def _builder_item(cls, raw: dict, card: dict, material: dict, lang: str) -> dict | None:
        tokens = cls._localized_list(card.get("tokens"), lang)
        answer_tokens = cls._localized_list(card.get("answer_tokens"), lang)
        raw_selected = raw.get("selected_tokens")
        if not isinstance(raw_selected, list):
            return None
        selected_tokens = [cls._text(value, 200) for value in raw_selected]
        if (
            not tokens
            or not answer_tokens
            or not selected_tokens
            or any(not value for value in selected_tokens)
            or len(selected_tokens) != len(answer_tokens)
        ):
            return None
        bank = Counter(tokens)
        selected = Counter(selected_tokens)
        if any(count > bank.get(token, 0) for token, count in selected.items()):
            return None
        if selected_tokens == answer_tokens:
            return None

        correct_answer = " ".join(answer_tokens)
        selected_answer = " ".join(selected_tokens)
        if material["format"] == "sentence_builder":
            # The source's localized sentence is the translation; the built
            # answer is the Chinese sentence users should review.
            translation = material["sentence"]
            material["sentence"] = "".join(answer_tokens)
            material["translation"] = translation
            material["prompt"] = material["prompt"] or translation
        else:
            material["sentence"] = cls._text(card.get("zh")) or material["sentence"]
            material["prompt"] = material["prompt"] or cls._localized(card.get("translation"), lang)
        material.update(
            {
                "tokens": tokens,
                "answer_tokens": answer_tokens,
                "correct_answer": correct_answer,
            }
        )
        return {
            "question_id": material["material_ref"],
            "question": material["prompt"] or material["sentence"] or material["format"],
            "selected_answer": selected_answer,
            "correct_answer": correct_answer,
            "explanation": material["explanation"],
            "category": material["category"],
            "format": material["format"],
            "language": material["language"],
            "sentence": material["sentence"],
            "audio_text": material["audio_text"],
            "pinyin": material["pinyin"],
            "material_ref": material["material_ref"],
            "material": material,
        }

    @classmethod
    def canonicalize_items(
        cls,
        *,
        level: str,
        lesson_order: int,
        lang: str,
        items: list,
    ) -> list[dict]:
        """Return only verified wrong answers from the canonical lesson JSON.

        Invalid/forged individual submissions are ignored so optional mistake
        telemetry can never block lesson completion.
        """

        level = cls.normalize_level(level)
        lang = cls.normalize_language(lang)
        try:
            lesson_order = int(lesson_order)
        except (TypeError, ValueError) as error:
            raise CourseLessonMistakeMaterialError("Invalid lesson order") from error
        if lesson_order <= 0:
            raise CourseLessonMistakeMaterialError("Invalid lesson order")
        data = cls._load_lesson(level, lesson_order)
        lookup = cls._card_lookup(data, level, lesson_order)
        source_schema_version = int(data.get("schema_version") or 1)

        canonical = []
        seen_refs = set()
        for raw in items[:50] if isinstance(items, list) else []:
            if not isinstance(raw, dict):
                continue
            material_ref = cls._text(raw.get("material_ref"), 160)
            if material_ref in seen_refs or not _MATERIAL_REF_RE.fullmatch(material_ref):
                continue
            entry = lookup.get(material_ref)
            if not entry:
                continue
            card = entry["card"]
            material = cls._base_material(
                card=card,
                section=entry["section"],
                level=level,
                lesson_order=lesson_order,
                lang=lang,
                section_no=entry["section_no"],
                card_no=entry["card_no"],
                material_ref=material_ref,
                source_schema_version=source_schema_version,
            )
            card_type = material["format"]
            if card_type in {"sentence_builder", "reverse_builder"}:
                item = cls._builder_item(raw, card, material, lang)
            else:
                item = cls._choice_item(raw, card, material, lang)
            if item:
                seen_refs.add(material_ref)
                canonical.append(item)
        return canonical
