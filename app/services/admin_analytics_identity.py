"""Read-only account identities for mixed native and legacy admin analytics."""

from sqlalchemy import String, and_, case, cast, func, literal, or_, select

from app.db.models.user import User


def analytics_user_join(model, *, telegram_column="telegram_id"):
    """Canonical ownership wins; resolve only unowned legacy Telegram rows."""
    telegram_id = getattr(model, telegram_column)
    return or_(
        model.user_id == User.id,
        and_(model.user_id.is_(None), telegram_id == User.telegram_id),
    )


def analytics_account_key(model, *, telegram_column="telegram_id"):
    """Stable SQL key without collisions between internal and Telegram IDs.

    A native account keeps one key before/after attaching Telegram. Unowned
    legacy rows resolve its real Telegram owner; orphaned/retained histories
    keep their own Telegram namespace. NULL/NULL rows have no measured user.
    This expression never grants access or changes attribution/event policy.
    """
    telegram_id = getattr(model, telegram_column)
    legacy_owner = (
        select(User.id)
        .where(User.telegram_id == telegram_id)
        .correlate(model)
        .scalar_subquery()
    )
    user_id = func.coalesce(model.user_id, legacy_owner)
    return case(
        (user_id.is_not(None), literal("user:") + cast(user_id, String)),
        (telegram_id.is_not(None), literal("telegram:") + cast(telegram_id, String)),
        else_=None,
    )


def analytics_identity(value):
    """Keep namespaced SQL keys and support legacy integer fixture callers."""
    if value is None or isinstance(value, bool):
        return None
    try:
        if isinstance(value, str) and value.startswith(("user:", "telegram:")):
            namespace, number = value.split(":", 1)
            return f"{namespace}:{int(number)}"
        return int(value)
    except (TypeError, ValueError):
        return None


def analytics_row_key(row):
    key = getattr(row, "account_key", None)
    if key is not None:
        return key
    user_id = getattr(row, "user_id", None)
    if user_id is not None:
        return f"user:{int(user_id)}"
    telegram_id = getattr(row, "telegram_id", None)
    return f"telegram:{int(telegram_id)}" if telegram_id is not None else None
