"""Canonical Course question material helpers.

The Course frontends historically consumed several incompatible question shapes.
This module defines the small version-2 contract used by the server-side HSK exam
runner and keeps answer keys out of public projections.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any


COURSE_QUESTION_MATERIAL_VERSION = 2
COURSE_MATERIAL_LANGUAGES = ("uz", "ru", "tj")
COURSE_HSK_LEVELS = ("hsk1", "hsk2", "hsk3", "hsk4")
COURSE_HSK_EXAM_FORMATS = frozenset({"audio_truefalse", "audio_choice", "text_choice"})
COURSE_HSK_EXAM_SECTIONS = ("listening", "reading", "writing")


class CourseQuestionMaterialError(ValueError):
    """Raised when source material cannot satisfy the canonical contract."""


def normalize_material_language(value: str) -> str:
    lang = str(value or "").strip().lower()
    if lang not in COURSE_MATERIAL_LANGUAGES:
        raise CourseQuestionMaterialError("Unsupported material language")
    return lang


def normalize_hsk_level(value: str) -> str:
    level = str(value or "").strip().lower()
    if level in {"hsk4a", "hsk4b"}:
        level = "hsk4"
    if level not in COURSE_HSK_LEVELS:
        raise CourseQuestionMaterialError("Unsupported HSK level")
    return level


def _mapping(value: Any, field: str) -> dict:
    if not isinstance(value, dict):
        raise CourseQuestionMaterialError(f"{field} must be an object")
    return value


def _non_empty_text(value: Any, field: str, *, limit: int = 4000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CourseQuestionMaterialError(f"{field} must be a non-empty string")
    text = value.strip()
    if len(text) > limit:
        raise CourseQuestionMaterialError(f"{field} is too long")
    return text


def _optional_text(value: Any, field: str, *, limit: int = 4000) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise CourseQuestionMaterialError(f"{field} must be a string")
    text = value.strip()
    if len(text) > limit:
        raise CourseQuestionMaterialError(f"{field} is too long")
    return text


def _localized(value: Any, field: str, lang: str) -> tuple[str, dict[str, str]]:
    data = _mapping(value, field)
    translations = {
        code: _non_empty_text(data.get(code), f"{field}.{code}")
        for code in COURSE_MATERIAL_LANGUAGES
    }
    return translations[lang], translations


def _bounded_int(value: Any, field: str, low: int, high: int) -> int:
    if isinstance(value, bool):
        raise CourseQuestionMaterialError(f"{field} must be an integer")
    try:
        result = int(value)
    except (TypeError, ValueError) as error:
        raise CourseQuestionMaterialError(f"{field} must be an integer") from error
    if result < low or result > high:
        raise CourseQuestionMaterialError(f"{field} is outside the allowed range")
    return result


def _is_meaning_question(question: dict, localized_prompt: str) -> bool:
    sentence = str(question.get("stem_zh") or "")
    folded = localized_prompt.casefold()
    return (
        "意思" in sentence
        or "ma'nosi" in folded
        or "значит" in folded
        or "маъно" in folded
    )


def _true_false_options(lang: str) -> tuple[list[str], list[dict[str, Any]]]:
    labels = {
        "uz": ("To'g'ri", "Noto'g'ri"),
        "ru": ("Верно", "Неверно"),
        "tj": ("Дуруст", "Нодуруст"),
    }
    true_labels = {code: values[0] for code, values in labels.items()}
    false_labels = {code: values[1] for code, values in labels.items()}
    simple = [true_labels[lang], false_labels[lang]]
    rich = [
        {
            "id": "true",
            "zh": "",
            "pinyin": "",
            "translation": true_labels[lang],
            "translations": true_labels,
        },
        {
            "id": "false",
            "zh": "",
            "pinyin": "",
            "translation": false_labels[lang],
            "translations": false_labels,
        },
    ]
    return simple, rich


def _choice_options(
    question: dict,
    *,
    question_id: str,
    question_format: str,
    localized_prompt: str,
    lang: str,
) -> tuple[list[str], list[dict[str, Any]], int]:
    raw_options = question.get("options")
    if not isinstance(raw_options, list) or not 2 <= len(raw_options) <= 6:
        raise CourseQuestionMaterialError(f"{question_id}.options must contain 2-6 items")

    simple: list[str] = []
    rich: list[dict[str, Any]] = []
    correct_indexes: list[int] = []
    meaning_question = _is_meaning_question(question, localized_prompt)
    for index, raw in enumerate(raw_options):
        option = _mapping(raw, f"{question_id}.options[{index}]")
        zh = _non_empty_text(option.get("zh"), f"{question_id}.options[{index}].zh")
        pinyin = _non_empty_text(option.get("py"), f"{question_id}.options[{index}].py")
        translation, translations = _localized(
            option.get("label"), f"{question_id}.options[{index}].label", lang
        )
        display = translation if question_format == "audio_choice" or meaning_question else zh
        simple.append(display)
        rich.append(
            {
                "id": f"{question_id}:option:{index + 1}",
                "zh": zh,
                "pinyin": pinyin,
                "translation": translation,
                "translations": translations,
            }
        )
        if option.get("ok") is True or option.get("ok") == 1:
            correct_indexes.append(index)

    if len(correct_indexes) != 1:
        raise CourseQuestionMaterialError(f"{question_id} must have exactly one correct option")
    return simple, rich, correct_indexes[0]


def _canonical_question(
    question: dict,
    *,
    level: str,
    section: str,
    lang: str,
    source_path: str,
    source_schema_version: int,
) -> dict[str, Any]:
    number = _bounded_int(question.get("no"), "question.no", 1, 9999)
    question_id = f"{level}:exam:static-v{source_schema_version}:{section}:{number:03d}"
    question_format = _non_empty_text(question.get("type"), f"{question_id}.type", limit=64)
    if question_format not in COURSE_HSK_EXAM_FORMATS:
        raise CourseQuestionMaterialError(f"{question_id} has unsupported format")

    prompt, prompt_translations = _localized(question.get("stem"), f"{question_id}.stem", lang)
    sentence_field = "prompt_zh" if question_format == "audio_truefalse" else "stem_zh"
    sentence = _optional_text(question.get(sentence_field), f"{question_id}.{sentence_field}")
    audio_text = _optional_text(question.get("audio_text"), f"{question_id}.audio_text")

    if question_format.startswith("audio_") and not audio_text:
        raise CourseQuestionMaterialError(f"{question_id} requires audio_text")
    if question_format == "audio_truefalse":
        if not sentence:
            raise CourseQuestionMaterialError(f"{question_id} requires prompt_zh")
        if not isinstance(question.get("answer"), bool):
            raise CourseQuestionMaterialError(f"{question_id}.answer must be boolean")
        options, option_materials = _true_false_options(lang)
        answer_index = 0 if question["answer"] else 1
    else:
        if question_format == "text_choice" and not sentence:
            raise CourseQuestionMaterialError(f"{question_id} requires stem_zh")
        options, option_materials, answer_index = _choice_options(
            question,
            question_id=question_id,
            question_format=question_format,
            localized_prompt=prompt,
            lang=lang,
        )

    explanation_value = question.get("explanation")
    if isinstance(explanation_value, dict):
        explanation, _ = _localized(explanation_value, f"{question_id}.explanation", lang)
    elif isinstance(explanation_value, str) and explanation_value.strip():
        explanation = explanation_value.strip()
    else:
        explanation = options[answer_index]

    return {
        "material_version": COURSE_QUESTION_MATERIAL_VERSION,
        "id": question_id,
        "format": question_format,
        "category": section,
        "section": section,
        "prompt": prompt,
        "prompt_translations": prompt_translations,
        "sentence": sentence,
        "audio_text": audio_text,
        "audio": {"kind": "tts", "text": audio_text} if audio_text else None,
        "options": options,
        "option_materials": option_materials,
        "answer_index": answer_index,
        "explanation": explanation,
        "source": {
            "kind": "static_hsk_exam",
            "path": source_path,
            "schema_version": source_schema_version,
            "level": level,
            "section": section,
            "question_no": number,
        },
    }


def canonicalize_hsk_exam_material(
    raw: dict,
    *,
    level: str,
    lang: str,
    source_path: str,
) -> dict[str, Any]:
    """Strictly validate legacy HSK JSON and return canonical v2 material."""

    level = normalize_hsk_level(level)
    lang = normalize_material_language(lang)
    raw = _mapping(raw, "exam")
    source_schema_version = _bounded_int(raw.get("schema_version"), "schema_version", 1, 1)
    if normalize_hsk_level(raw.get("level")) != level:
        raise CourseQuestionMaterialError("Exam level does not match requested level")
    duration_min = _bounded_int(raw.get("duration_min"), "duration_min", 1, 240)
    pass_score = _bounded_int(raw.get("pass_score"), "pass_score", 1, 100)
    source_path = _non_empty_text(source_path, "source_path", limit=500)

    raw_sections = raw.get("sections")
    if not isinstance(raw_sections, list) or not raw_sections:
        raise CourseQuestionMaterialError("sections must be a non-empty list")

    sections = []
    questions = []
    seen_sections: set[str] = set()
    seen_numbers: set[int] = set()
    seen_ids: set[str] = set()
    for section_index, raw_section in enumerate(raw_sections):
        section_data = _mapping(raw_section, f"sections[{section_index}]")
        section = _non_empty_text(section_data.get("key"), f"sections[{section_index}].key", limit=32)
        if section not in COURSE_HSK_EXAM_SECTIONS or section in seen_sections:
            raise CourseQuestionMaterialError("Exam sections must be unique canonical sections")
        seen_sections.add(section)
        section_title, section_translations = _localized(
            section_data.get("title"), f"sections[{section_index}].title", lang
        )
        title_zh = _non_empty_text(section_data.get("title_zh"), f"sections[{section_index}].title_zh")
        raw_questions = section_data.get("questions")
        if not isinstance(raw_questions, list) or not raw_questions:
            raise CourseQuestionMaterialError(f"Section {section} has no questions")

        section_question_ids = []
        for raw_question in raw_questions:
            question_data = _mapping(raw_question, f"section {section} question")
            question = _canonical_question(
                question_data,
                level=level,
                section=section,
                lang=lang,
                source_path=source_path,
                source_schema_version=source_schema_version,
            )
            number = int(question["source"]["question_no"])
            if number in seen_numbers or question["id"] in seen_ids:
                raise CourseQuestionMaterialError("Question numbers and ids must be unique")
            seen_numbers.add(number)
            seen_ids.add(question["id"])
            questions.append(question)
            section_question_ids.append(question["id"])
        sections.append(
            {
                "key": section,
                "title": section_title,
                "title_zh": title_zh,
                "translations": section_translations,
                "question_ids": section_question_ids,
            }
        )

    expected_numbers = list(range(1, len(questions) + 1))
    if sorted(seen_numbers) != expected_numbers:
        raise CourseQuestionMaterialError("Question numbers must be contiguous from 1")

    material_id = f"{level}:exam:static-v{source_schema_version}"
    return {
        "material_version": COURSE_QUESTION_MATERIAL_VERSION,
        "id": material_id,
        "level": level,
        "lang": lang,
        "duration_min": duration_min,
        "pass_score": pass_score,
        "sections": sections,
        "questions": questions,
        "source": {
            "kind": "static_hsk_exam",
            "path": source_path,
            "schema_version": source_schema_version,
            "level": level,
        },
    }


def shuffle_question_options(question: dict, seed: str) -> dict[str, Any]:
    """Deterministically shuffle paired option fields and remap the answer."""

    shuffled = deepcopy(_mapping(question, "question"))
    options = shuffled.get("options")
    materials = shuffled.get("option_materials")
    if not isinstance(options, list) or len(options) < 2:
        raise CourseQuestionMaterialError("Canonical question requires at least two options")
    if not isinstance(materials, list) or len(materials) != len(options):
        raise CourseQuestionMaterialError("option_materials must align with options")
    answer_index = _bounded_int(shuffled.get("answer_index"), "answer_index", 0, len(options) - 1)
    question_id = _non_empty_text(shuffled.get("id"), "question.id", limit=200)
    seed = _non_empty_text(seed, "shuffle seed", limit=500)

    order = sorted(
        range(len(options)),
        key=lambda index: hashlib.sha256(
            f"{seed}|{question_id}|{index}".encode("utf-8")
        ).digest(),
    )
    shuffled["options"] = [options[index] for index in order]
    shuffled["option_materials"] = [materials[index] for index in order]
    shuffled["answer_index"] = order.index(answer_index)
    return shuffled


def shuffle_exam_questions(questions: list[dict], seed: str) -> list[dict[str, Any]]:
    if not isinstance(questions, list) or not questions:
        raise CourseQuestionMaterialError("Exam questions must be a non-empty list")
    return [shuffle_question_options(question, seed) for question in questions]


def public_question_projection(question: dict) -> dict[str, Any]:
    """Return render material without the server-only grading fields."""

    public = deepcopy(_mapping(question, "question"))
    public.pop("answer_index", None)
    public.pop("explanation", None)
    # Rich materials deliberately keep hanzi/pinyin/all translations for server
    # review and mistake explanations. In meaning/listening questions that data
    # can reveal which localized option matches the source, so it is private too.
    public.pop("option_materials", None)
    return public


def public_questions_projection(questions: list[dict]) -> list[dict[str, Any]]:
    return [public_question_projection(question) for question in questions]


def canonical_material_digest(material: dict) -> str:
    """Fingerprint the immutable grading-relevant portion of an exam."""

    material = _mapping(material, "material")
    questions = material.get("questions")
    if not isinstance(questions, list) or not questions:
        raise CourseQuestionMaterialError("Material requires questions")
    payload = {
        "material_version": material.get("material_version"),
        "id": material.get("id"),
        "level": material.get("level"),
        "pass_score": material.get("pass_score"),
        "questions": [
            {
                "id": question.get("id"),
                "format": question.get("format"),
                "section": question.get("section"),
                "options": question.get("options"),
                "answer_index": question.get("answer_index"),
            }
            for question in questions
        ],
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
