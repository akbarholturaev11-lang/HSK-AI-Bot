from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.services.course_challenge_service import CourseChallengeService

router = Router()


def _lang(callback: CallbackQuery, result: dict | None = None) -> str:
    value = str(result.get("challenge", {}).get("lang") if isinstance(result, dict) else "")
    if value in {"uz", "ru", "tj"}:
        return value
    code = str(getattr(callback.from_user, "language_code", "") or "").lower()
    if code.startswith("ru"):
        return "ru"
    if code.startswith("tg") or code.startswith("tj"):
        return "tj"
    return "uz"


def _text(lang: str, key: str) -> str:
    messages = {
        "uz": {
            "bad_button": "Noto'g'ri belashuv tugmasi",
            "not_found": "Belashuv topilmadi",
            "bad_action": "Noto'g'ri amal",
            "closed": "Belashuv allaqachon yopilgan yoki topilmadi",
            "accepted": "Belashuv qabul qilindi. Musobaqani oching.",
            "rejected": "Belashuv rad qilindi.",
        },
        "ru": {
            "bad_button": "Неверная кнопка поединка",
            "not_found": "Поединок не найден",
            "bad_action": "Неверное действие",
            "closed": "Поединок уже закрыт или не найден",
            "accepted": "Дуэль принята. Откройте раунд.",
            "rejected": "Дуэль отклонена.",
        },
        "tj": {
            "bad_button": "Тугмаи рақобат нодуруст аст",
            "not_found": "Рақобат ёфт нашуд",
            "bad_action": "Амал нодуруст аст",
            "closed": "Рақобат аллакай баста шуд ё ёфт нашуд",
            "accepted": "Рақобат қабул шуд. Раундро кушоед.",
            "rejected": "Рақобат рад шуд.",
        },
    }
    return messages.get(lang, messages["uz"]).get(key, key)


@router.callback_query(F.data.startswith("challenge:"))
async def challenge_callback(callback: CallbackQuery, session):
    lang = _lang(callback)
    parts = str(callback.data or "").split(":")
    if len(parts) != 3:
        await callback.answer(_text(lang, "bad_button"), show_alert=True)
        return
    _, action, raw_id = parts
    try:
        challenge_id = int(raw_id)
    except ValueError:
        await callback.answer(_text(lang, "not_found"), show_alert=True)
        return
    if action not in {"accept", "reject"}:
        await callback.answer(_text(lang, "bad_action"), show_alert=True)
        return

    result = await CourseChallengeService(session).respond(
        int(callback.from_user.id),
        challenge_id,
        action,
        bot=callback.bot,
    )
    await session.commit()
    lang = _lang(callback, result)
    if not result.get("ok"):
        await callback.answer(_text(lang, "closed"), show_alert=True)
        return
    text = _text(lang, "accepted" if action == "accept" else "rejected")
    challenge = result.get("challenge") or {}
    try:
        if callback.message:
            await callback.message.edit_text(
                CourseChallengeService.resolved_invite_text(
                    challenge,
                    accepted=action == "accept",
                    lang=lang,
                ),
                reply_markup=(
                    CourseChallengeService._open_keyboard(
                        lang,
                        int(challenge.get("id") or challenge_id),
                        str(challenge.get("level") or ""),
                    )
                    if action == "accept"
                    else None
                ),
            )
    except Exception:
        pass
    await callback.answer(text, show_alert=True)
