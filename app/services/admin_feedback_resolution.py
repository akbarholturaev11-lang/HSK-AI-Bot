"""Server-owned Android report fix receipts; never trust a browser-supplied recipient.

The admin's resolved transition and the delivery outbox are written in the
same transaction, so a retry, process restart or double tap cannot silently
create multiple notifications.
"""
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.models.account_notice_delivery import AccountNoticeDelivery
from app.db.models.user import User
from app.services.notification_delivery_service import TelegramNotice


_FIX_COPY = {
    "uz": (
        ("Xatolik tuzatildi ✅", "Muammo hal qilindi. Darsni davom ettiramiz! 🔥"),
        ("Xatolik tuzatildi ✅", "Yangi versiya tayyor. Ilovani yangilab, darsni davom ettiring! 🔥"),
    ),
    "ru": (
        ("Ошибка исправлена ✅", "Проблема решена. Продолжайте обучение! 🔥"),
        ("Ошибка исправлена ✅", "Доступна новая версия. Обновите приложение и продолжайте обучение! 🔥"),
    ),
    "tj": (
        ("Хатогӣ ислоҳ шуд ✅", "Мушкил ҳал шуд. Дарсро давом диҳед! 🔥"),
        ("Хатогӣ ислоҳ шуд ✅", "Версияи нав омода аст. Барномаро нав кунед ва дарсро давом диҳед! 🔥"),
    ),
}


def fixed_notice_copy(lang: str, mode: str) -> tuple[str, str]:
    """Localized, content-free message: never include a private report."""
    if mode not in ("server", "app_update"):
        raise ValueError("invalid_fix_kind")
    choices = _FIX_COPY.get(lang, _FIX_COPY["uz"])
    return choices[0 if mode == "server" else 1]


async def enqueue_android_fix_notice(
    db, *, user_id: int, source_id: int, revision: int,
    mode: str, now: datetime,
) -> int:
    """Call while holding the source + triage row locks inside the resolve tx."""
    if not isinstance(source_id, int) or source_id < 1 or revision < 1:
        raise ValueError("invalid_report_revision")
    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise ValueError("missing_report_owner")
    lang = user.language if user.language in _FIX_COPY else "uz"
    title, body = fixed_notice_copy(lang, mode)
    row = AccountNoticeDelivery(
        user_id=user.id,
        telegram_id=user.telegram_id,
        key="feedback_fixed" if mode == "server" else "feedback_update",
        language=lang,
        title=title,
        body=body,
        action="course",
        status="fix_queued",
        android_targets=0,
        android_blocked=0,
        telegram_payload=TelegramNotice(text=f"{title}\n{body}").to_payload(),
        reason=f"android_fix_{source_id}_{revision}"[:40],
        created_at=now,
        fallback_due_at=None,
    )
    db.add(row)
    await db.flush()
    return row.id
