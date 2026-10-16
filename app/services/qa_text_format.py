"""Remove presentation-only Markdown from AI tutor replies sent as Telegram plain text.

Only the QA/photo tutor pipelines use this helper. Other bot messages deliberately
use HTML and must not have their existing formatting changed.
"""

import re


_HEADING = re.compile(r"(?m)^[ \t]{0,3}#{1,6}[ \t]+")
_BULLET = re.compile(r"(?m)^([ \t]*)[*-][ \t]+")
_BOLD = re.compile(r"(?<!\*)\*\*(?=\S)([^\n]*?\S)\*\*(?!\*)")
_ITALIC = re.compile(r"(?<![\w*])\*(?=\S)([^*\n]*?\S)\*(?![\w*])")


def clean_ai_qa_markup(text: str | None) -> str:
    """Keep the Chinese/pinyin/translation intact without visible Markdown stars.

    Do not globally remove '*' — it is meaningful in multiplication and code.
    Only remove well-formed emphasis markers; leave arbitrary text untouched.
    """
    result = (text or "").strip()
    if not result:
        return ""
    result = _HEADING.sub("", result)
    result = _BULLET.sub(r"\1• ", result)
    result = _BOLD.sub(r"\1", result)
    result = _ITALIC.sub(r"\1", result)
    return result
