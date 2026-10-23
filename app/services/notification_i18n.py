"""Pure local fixed notification copy with the caller's existing fallback."""
from __future__ import annotations

import re

from app.services.generated.notification_i18n import NOTIFICATION_MESSAGES

_VARIABLE = re.compile(r"\{([a-zA-Z0-9_]+)\}")


def notification_message(
    key: str,
    locale: str,
    fallback: str = "",
    *,
    fallback_locale: str = "ru",
    **variables,
) -> str:
    selected = locale if locale in ("uz", "ru", "tj") else fallback_locale
    template = NOTIFICATION_MESSAGES.get(selected, {}).get(key) or fallback
    return _VARIABLE.sub(
        lambda match: str(variables[match.group(1)])
        if match.group(1) in variables else match.group(0),
        template,
    )
