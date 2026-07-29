from aiogram import F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from app.config import settings
from app.repositories.user_repo import UserRepository
from app.services.desktop_auth_service import DesktopAuthError, DesktopAuthService


router = Router()


_COPY = {
    "uz": {
        "confirm": (
            "🖥 <b>Kompyuter ilovasini ulash</b>\n\n"
            "Qurilma: <b>{platform}</b>\n"
            "Versiya: <b>{version}</b>\n"
            "Kod: <code>{code}</code>\n\n"
            "Bu kodni Pomp HSK AI ilovasida o‘zingiz ochgan bo‘lsangizgina "
            "tasdiqlang. Aks holda bekor qiling."
        ),
        "approve": "✅ Tasdiqlash",
        "cancel": "Bekor qilish",
        "ok": (
            "✅ <b>Kompyuter ilovasi ulandi</b>\n\n"
            "Pomp Desktop’ga qayting — hisobingiz avtomatik ochiladi."
        ),
        "cancelled": "Ulash bekor qilindi. Bu kod endi ishlamaydi.",
        "invalid": (
            "Bu ulash kodi eskirgan yoki ishlatilgan. "
            "Kompyuter ilovasida yangi kod yarating."
        ),
    },
    "ru": {
        "confirm": (
            "🖥 <b>Подключение приложения на компьютере</b>\n\n"
            "Устройство: <b>{platform}</b>\n"
            "Версия: <b>{version}</b>\n"
            "Код: <code>{code}</code>\n\n"
            "Подтверждайте, только если вы сами открыли этот код в Pomp HSK AI. "
            "Иначе отмените подключение."
        ),
        "approve": "✅ Подтвердить",
        "cancel": "Отменить",
        "ok": (
            "✅ <b>Приложение на компьютере подключено</b>\n\n"
            "Вернитесь в Pomp Desktop — аккаунт откроется автоматически."
        ),
        "cancelled": "Подключение отменено. Этот код больше не работает.",
        "invalid": (
            "Код подключения истёк или уже использован. "
            "Создайте новый код в приложении на компьютере."
        ),
    },
    "tj": {
        "confirm": (
            "🖥 <b>Пайваст кардани барномаи компютерӣ</b>\n\n"
            "Дастгоҳ: <b>{platform}</b>\n"
            "Версия: <b>{version}</b>\n"
            "Рамз: <code>{code}</code>\n\n"
            "Танҳо агар ин рамзро худатон дар Pomp HSK AI кушода бошед, "
            "тасдиқ кунед. Дар акси ҳол бекор кунед."
        ),
        "approve": "✅ Тасдиқ",
        "cancel": "Бекор кардан",
        "ok": (
            "✅ <b>Барномаи компютерӣ пайваст шуд</b>\n\n"
            "Ба Pomp Desktop баргардед — ҳисоб худкор кушода мешавад."
        ),
        "cancelled": "Пайвастшавӣ бекор шуд. Ин рамз дигар кор намекунад.",
        "invalid": (
            "Муҳлати рамзи пайвастшавӣ гузашт ё он истифода шудааст. "
            "Дар барномаи компютерӣ рамзи нав созед."
        ),
    },
}


async def _language(session, telegram_id: int) -> str:
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    language = str(getattr(user, "language", None) or "ru")
    return language if language in _COPY else "ru"


def _confirmation_keyboard(language: str, display_code: str) -> InlineKeyboardMarkup:
    copy = _COPY[language]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=copy["approve"],
                    callback_data=f"desktop_link:approve:{display_code}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=copy["cancel"],
                    callback_data=f"desktop_link:cancel:{display_code}",
                )
            ],
        ]
    )


@router.message(
    CommandStart(deep_link=True),
    F.text.regexp(r"^/start(?:@\w+)?\s+desktop_[A-Za-z0-9-]{8,16}\s*$"),
)
async def approve_desktop_link(
    message: Message,
    command: CommandObject,
    session,
) -> None:
    language = await _language(session, message.from_user.id)
    argument = str(command.args or "")
    display_code = (
        argument[len("desktop_") :] if argument.startswith("desktop_") else ""
    )
    try:
        preview = await DesktopAuthService(session, settings).link_preview(
            display_code=display_code,
            telegram_id=message.from_user.id,
        )
    except DesktopAuthError:
        await message.answer(_COPY[language]["invalid"], parse_mode="HTML")
        return
    platform = "Mac" if preview["platform"] == "macos" else "Windows"
    await message.answer(
        _COPY[language]["confirm"].format(
            platform=platform,
            version=preview["app_version"],
            code=preview["display_code"],
        ),
        parse_mode="HTML",
        reply_markup=_confirmation_keyboard(language, preview["display_code"]),
    )


@router.callback_query(F.data.regexp(r"^desktop_link:approve:[A-Za-z0-9]{8}$"))
async def confirm_desktop_link(callback: CallbackQuery, session) -> None:
    language = await _language(session, callback.from_user.id)
    display_code = str(callback.data or "").rsplit(":", 1)[-1]
    try:
        await DesktopAuthService(session, settings).approve_link(
            display_code=display_code,
            telegram_id=callback.from_user.id,
        )
    except DesktopAuthError:
        await callback.answer(_COPY[language]["invalid"], show_alert=True)
        return
    if callback.message:
        await callback.message.edit_text(_COPY[language]["ok"], parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.regexp(r"^desktop_link:cancel:[A-Za-z0-9]{8}$"))
async def cancel_desktop_link(callback: CallbackQuery, session) -> None:
    language = await _language(session, callback.from_user.id)
    display_code = str(callback.data or "").rsplit(":", 1)[-1]
    try:
        await DesktopAuthService(session, settings).cancel_link(
            display_code=display_code,
            telegram_id=callback.from_user.id,
        )
    except DesktopAuthError:
        await callback.answer(_COPY[language]["invalid"], show_alert=True)
        return
    if callback.message:
        await callback.message.edit_text(
            _COPY[language]["cancelled"],
            parse_mode="HTML",
        )
    await callback.answer()
