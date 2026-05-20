import json
from html import escape
from urllib.parse import urlencode

from app.bot.utils.i18n import t
from app.config import settings


MINIAPP_SUPPORTED_LEVEL = "hsk3"
MINIAPP_MIN_LESSON = 1
MINIAPP_MAX_LESSON = 20


def course_miniapp_lesson_id(lesson) -> int:
    return int(getattr(lesson, "lesson_order", None) or getattr(lesson, "id", 0) or 0)


def is_course_miniapp_supported(lesson) -> bool:
    if lesson is None:
        return False

    level = (getattr(lesson, "level", "") or "").strip().lower()
    lesson_id = course_miniapp_lesson_id(lesson)
    return (
        level == MINIAPP_SUPPORTED_LEVEL
        and MINIAPP_MIN_LESSON <= lesson_id <= MINIAPP_MAX_LESSON
    )


def course_miniapp_url(lesson, mode: str, lang: str | None = None) -> str:
    base_url = (settings.MINI_APP_BASE_URL or "").strip() or "https://YOURDOMAIN.com/hsk3.html"
    separator = "&" if "?" in base_url else "?"
    query = urlencode(
        {
            "lesson": course_miniapp_lesson_id(lesson),
            "mode": mode,
            "lang": lang or "uz",
        }
    )
    return f"{base_url}{separator}{query}"


def format_miniapp_quiz_intro(lang: str, lesson) -> str:
    return t("course_miniapp_quiz_intro", lang, lesson_id=course_miniapp_lesson_id(lesson))


def format_miniapp_homework_intro(lang: str, lesson) -> str:
    return t("course_miniapp_homework_intro", lang, lesson_id=course_miniapp_lesson_id(lesson))


def normalize_result_items(value) -> list[str]:
    if value is None:
        return []

    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
        except Exception:
            return [line.strip() for line in raw.splitlines() if line.strip()]
        return normalize_result_items(parsed)

    if not isinstance(value, list):
        return [str(value)]

    items = []
    for item in value:
        if isinstance(item, dict):
            question = item.get("question") or item.get("title") or item.get("text") or ""
            answer = item.get("correct_answer") or item.get("answer") or ""
            explanation = item.get("explanation") or item.get("feedback") or ""
            parts = [str(part).strip() for part in (question, answer, explanation) if str(part).strip()]
            if parts:
                items.append(" — ".join(parts[:2]) if len(parts) > 1 else parts[0])
            continue

        text = str(item).strip()
        if text:
            items.append(text)

    return items


def _append_items(lines: list[str], title: str, items: list[str], limit: int = 10) -> None:
    if not items:
        return

    lines.append("")
    lines.append(title)
    for item in items[:limit]:
        lines.append(f"— {escape(str(item))}")


def format_miniapp_quiz_result(lang: str, result: dict) -> str:
    lesson_id = int(result.get("lesson_id") or 0)
    score = int(result.get("score") or 0)
    total = int(result.get("total") or 0)
    percent = int(result.get("percent") or 0)
    wrong_items = normalize_result_items(result.get("wrong_items"))

    lines = [
        t("course_miniapp_quiz_done", lang),
        "",
        t("course_miniapp_lesson_line", lang, lesson_id=lesson_id),
        t("course_miniapp_score_line", lang, score=score, total=total, percent=percent),
    ]
    _append_items(lines, t("course_miniapp_wrong_items", lang), wrong_items)
    lines.extend(["", t("course_miniapp_understood_question", lang)])
    return "\n".join(lines)


def format_miniapp_homework_result(lang: str, result: dict) -> str:
    lesson_id = int(result.get("lesson_id") or 0)
    homework_score = result.get("homework_score")
    feedback_items = normalize_result_items(result.get("feedback"))

    lines = [
        t("course_miniapp_homework_done", lang),
        "",
        t("course_miniapp_lesson_line", lang, lesson_id=lesson_id),
    ]

    if homework_score is not None:
        try:
            score_text = str(int(homework_score))
        except (TypeError, ValueError):
            score_text = escape(str(homework_score))
        lines.extend(["", t("course_miniapp_homework_score_line", lang, score=score_text)])

    _append_items(lines, t("course_miniapp_feedback_items", lang), feedback_items)
    return "\n".join(lines)
