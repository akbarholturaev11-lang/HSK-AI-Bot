"""Canonical ownership for native accounts; legacy Telegram callers stay valid."""
from sqlalchemy import and_, false, or_


def account_user_id(actor):
    if hasattr(actor, "id") and hasattr(actor, "telegram_id"):
        return int(actor.id)
    return None


def actual_telegram_id(actor):
    value = getattr(actor, "telegram_id", actor)
    if value is None:
        return None
    value = int(value)
    return value if value > 0 else None


def owner_clause(model, actor, *, telegram_column="user_telegram_id", user_id=None):
    """Never let a missing provider identity turn into `telegram_id IS NULL`.

    Real-Telegram legacy rows may predate their canonical backfill. Native
    ownership uses users.id, with a narrowly scoped real-ID fallback for those
    rows only. A numeric legacy argument is always an actual Telegram ID.
    """
    uid = user_id if user_id is not None else account_user_id(actor)
    tid = actual_telegram_id(actor)
    telegram_field = getattr(model, telegram_column)
    if uid is not None:
        canonical = model.user_id == int(uid)
        return or_(canonical, and_(model.user_id.is_(None), telegram_field == tid)) if tid else canonical
    return telegram_field == tid if tid else false()
