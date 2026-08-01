from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from app.bot.fsm.desktop_auth import DesktopLinkStates
from app.config import settings
from app.repositories.user_repo import UserRepository
from app.services.desktop_auth_service import DesktopAuthError, DesktopAuthService


router = Router()

DISPLAY_CODE_ALPHABET = frozenset("23456789ABCDEFGHJKLMNPQRSTUVWXYZ")
MAX_INVALID_CODE_ATTEMPTS = 5


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
        "enter_code": (
            "🔐 <b>Ulash kodini kiriting</b>\n\n"
            "Pomp HSK AI kompyuter ilovasida ko‘rsatilgan 8 belgili kodni "
            "shu chatga <b>qo‘lda yuboring</b>.\n\n"
            "Kodni boshqa odamga yubormang."
        ),
        "invalid_code": (
            "Kod noto‘g‘ri, eskirgan yoki ishlatilgan. "
            "Ilovadagi 8 belgili kodni qayta kiriting. Qolgan urinish: {remaining}."
        ),
        "attempts_exhausted": (
            "Juda ko‘p noto‘g‘ri urinish bo‘ldi. "
            "Kompyuter ilovasida yangi kod oling va Telegramni qayta oching."
        ),
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
        "enter_code": (
            "🔐 <b>Введите код подключения</b>\n\n"
            "Вручную отправьте в этот чат 8-символьный код, показанный в "
            "приложении Pomp HSK AI на компьютере.\n\n"
            "Никому не передавайте код."
        ),
        "invalid_code": (
            "Код неверный, истёк или уже использован. "
            "Снова введите 8-значный код из приложения. Осталось попыток: {remaining}."
        ),
        "attempts_exhausted": (
            "Слишком много неверных попыток. Получите новый код в приложении "
            "на компьютере и снова откройте Telegram."
        ),
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
        "enter_code": (
            "🔐 <b>Рамзи пайвастшавиро ворид кунед</b>\n\n"
            "Рамзи 8-аломатии дар барномаи компютерии Pomp HSK AI "
            "нишондодашударо ба ин чат <b>дастӣ фиристед</b>.\n\n"
            "Рамзро ба каси дигар нафиристед."
        ),
        "invalid_code": (
            "Рамз нодуруст, муҳлаташ гузашта ё истифода шудааст. "
            "Рамзи 8-аломатиро аз барнома боз ворид кунед. Кӯшиши боқимонда: {remaining}."
        ),
        "attempts_exhausted": (
            "Кӯшишҳои нодуруст зиёд шуданд. Дар барномаи компютерӣ рамзи нав "
            "гиред ва Telegram-ро аз нав кушоед."
        ),
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


def _normalize_display_code(value: str | None) -> str | None:
    code = str(value or "").strip().upper()
    if len(code) != 8 or any(char not in DISPLAY_CODE_ALPHABET for char in code):
        return None
    return code


async def _register_invalid_attempt(
    message: Message,
    state: FSMContext,
    language: str,
) -> None:
    data = await state.get_data()
    attempts = min(
        MAX_INVALID_CODE_ATTEMPTS,
        int(data.get("desktop_link_invalid_attempts") or 0) + 1,
    )
    if attempts >= MAX_INVALID_CODE_ATTEMPTS:
        await state.clear()
        await message.answer(
            _COPY[language]["attempts_exhausted"],
            parse_mode="HTML",
        )
        return
    await state.update_data(desktop_link_invalid_attempts=attempts)
    await message.answer(
        _COPY[language]["invalid_code"].format(
            remaining=MAX_INVALID_CODE_ATTEMPTS - attempts,
        ),
        parse_mode="HTML",
    )


async def _begin_manual_code_entry(
    message: Message,
    state: FSMContext,
    session,
) -> None:
    current_state = await state.get_state()
    data = await state.get_data()
    if (
        current_state == DesktopLinkStates.waiting_code.state
        and data.get("desktop_link_prompted") is True
    ):
        # Telegram may deliver the same deep-link repeatedly when the desktop
        # button is clicked more than once. Keep one prompt in the chat.
        return

    language = await _language(session, message.from_user.id)
    await state.clear()
    await state.set_state(DesktopLinkStates.waiting_code)
    await state.update_data(
        desktop_link_invalid_attempts=0,
        desktop_link_prompted=True,
    )
    await message.answer(_COPY[language]["enter_code"], parse_mode="HTML")


@router.message(
    CommandStart(deep_link=True),
    F.text.regexp(r"^/start(?:@\w+)?\s+desktop_link\s*$"),
)
@router.message(
    CommandStart(deep_link=True),
    F.text.regexp(r"^/start(?:@\w+)?\s+desktop_[A-Za-z0-9-]{8,16}\s*$"),
)
async def begin_desktop_link(
    message: Message,
    state: FSMContext,
    session,
) -> None:
    # Legacy code-bearing links are deliberately ignored. They only open the
    # manual-entry state, so possession of a URL can never reserve a code.
    await _begin_manual_code_entry(message, state, session)


@router.message(DesktopLinkStates.waiting_code, F.text)
async def receive_desktop_link_code(
    message: Message,
    state: FSMContext,
    session,
) -> None:
    language = await _language(session, message.from_user.id)
    display_code = _normalize_display_code(message.text)
    if display_code is None:
        await _register_invalid_attempt(message, state, language)
        return
    try:
        preview = await DesktopAuthService(session, settings).link_preview(
            display_code=display_code,
            telegram_id=message.from_user.id,
        )
    except DesktopAuthError:
        await _register_invalid_attempt(message, state, language)
        return
    await state.clear()
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


@router.message(DesktopLinkStates.waiting_code)
async def receive_desktop_link_non_text(
    message: Message,
    state: FSMContext,
    session,
) -> None:
    language = await _language(session, message.from_user.id)
    await _register_invalid_attempt(message, state, language)


@router.callback_query(F.data.regexp(r"^desktop_link:approve:[23456789A-HJ-NP-Z]{8}$"))
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


@router.callback_query(F.data.regexp(r"^desktop_link:cancel:[23456789A-HJ-NP-Z]{8}$"))
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
