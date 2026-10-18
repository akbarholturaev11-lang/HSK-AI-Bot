"""Explicit canonical admin targets with a compatible real-Telegram adapter."""

from app.repositories.user_repo import UserRepository


def parse_admin_user_target(payload) -> tuple[int | None, int | None]:
    if not isinstance(payload, dict):
        raise ValueError("invalid_user_target")
    targets = []
    for key, maximum in (("user_id", 2**31 - 1), ("telegram_id", 2**63 - 1)):
        if key not in payload:
            targets.append(None)
            continue
        value = payload[key]
        raw = str(value).strip()
        if isinstance(value, bool) or not raw.isascii() or not raw.isdigit() or len(raw) > 19:
            raise ValueError("invalid_user_target")
        number = int(raw)
        if not 0 < number <= maximum:
            raise ValueError("invalid_user_target")
        targets.append(number)
    if targets == [None, None]:
        raise ValueError("invalid_user_target")
    return tuple(targets)


async def resolve_admin_user_target(session, target, *, lock=False):
    user_id, telegram_id = target
    repo = UserRepository(session)
    if user_id is not None:
        user = await repo.get_by_user_id(user_id, lock=lock)
        if user is not None and telegram_id is not None and user.telegram_id != telegram_id:
            raise ValueError("user_target_mismatch")
        return user
    if lock:
        return await repo.get_by_telegram_id_for_update(telegram_id)
    return await repo.get_by_telegram_id(telegram_id)
