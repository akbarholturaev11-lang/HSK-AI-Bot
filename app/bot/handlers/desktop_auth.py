from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from app.bot.fsm.android_auth import AndroidLinkStates
from app.bot.fsm.desktop_auth import DesktopLinkStates
from app.config import settings
from app.repositories.user_repo import UserRepository
from app.services.onboarding_service import (
    ONBOARDING_MODE_CHOICE_MODE,
    OnboardingService,
    onboarding_stage,
)
from app.services.desktop_auth_service import (
    ANDROID_LINK_PREFIX,
    MOBILE_PLATFORMS,
    DesktopAuthError,
    DesktopAuthService,
)


router = Router()

DISPLAY_CODE_ALPHABET = frozenset("23456789ABCDEFGHJKLMNPQRSTUVWXYZ")
MAX_INVALID_CODE_ATTEMPTS = 5


_COPY = {
    "uz": {
        "confirm_desktop": (
            "🖥 <b>Kompyuter ilovasini ulash</b>\n\n"
            "Qurilma: <b>{platform}</b>\n"
            "Versiya: <b>{version}</b>\n"
            "Kod: <code>{code}</code>\n\n"
            "Bu kodni HSK AI ilovasida o‘zingiz ochgan bo‘lsangizgina "
            "tasdiqlang. Aks holda bekor qiling."
        ),
        "confirm_mobile": (
            "📱 <b>Android ilovasini ulash</b>\n\n"
            "Qurilma: <b>{platform}</b>\n"
            "Versiya: <b>{version}</b>\n"
            "Kod: <code>{code}</code>\n\n"
            "Bu kodni HSK AI ilovasida o‘zingiz ochgan bo‘lsangizgina "
            "tasdiqlang. Aks holda bekor qiling."
        ),
        "approve": "✅ Tasdiqlash",
        "cancel": "Bekor qilish",
        "enter_code": (
            "🔐 <b>Ulash kodini kiriting</b>\n\n"
            "HSK AI ilovasida ko‘rsatilgan 8 belgili kodni "
            "shu chatga <b>qo‘lda yuboring</b>.\n\n"
            "Kodni boshqa odamga yubormang."
        ),
        "invalid_code": (
            "Kod noto‘g‘ri, eskirgan yoki ishlatilgan. "
            "Ilovadagi 8 belgili kodni qayta kiriting. Qolgan urinish: {remaining}."
        ),
        "attempts_exhausted": (
            "Juda ko‘p noto‘g‘ri urinish bo‘ldi. "
            "Ilovada yangi kod oling va Telegramni qayta oching."
        ),
        "ok_desktop": (
            "✅ <b>Kompyuter ilovasi ulandi</b>\n\n"
            "HSK AI Desktop’ga qayting — hisobingiz avtomatik ochiladi."
        ),
        "ok_mobile": (
            "✅ <b>Android ilovasi ulandi</b>\n\n"
            "HSK AI ilovasiga qayting — hisobingiz avtomatik ochiladi."
        ),
        "cancelled": "Ulash bekor qilindi. Bu kod endi ishlamaydi.",
        "invalid": (
            "Bu ulash kodi eskirgan yoki ishlatilgan. "
            "Ilovada yangi kod yarating."
        ),
    },
    "ru": {
        "confirm_desktop": (
            "🖥 <b>Подключение приложения на компьютере</b>\n\n"
            "Устройство: <b>{platform}</b>\n"
            "Версия: <b>{version}</b>\n"
            "Код: <code>{code}</code>\n\n"
            "Подтверждайте, только если вы сами открыли этот код в HSK AI. "
            "Иначе отмените подключение."
        ),
        "confirm_mobile": (
            "📱 <b>Подключение приложения на Android</b>\n\n"
            "Устройство: <b>{platform}</b>\n"
            "Версия: <b>{version}</b>\n"
            "Код: <code>{code}</code>\n\n"
            "Подтверждайте, только если вы сами открыли этот код в HSK AI. "
            "Иначе отмените подключение."
        ),
        "approve": "✅ Подтвердить",
        "cancel": "Отменить",
        "enter_code": (
            "🔐 <b>Введите код подключения</b>\n\n"
            "Вручную отправьте в этот чат 8-символьный код, показанный в "
            "приложении HSK AI.\n\n"
            "Никому не передавайте код."
        ),
        "invalid_code": (
            "Код неверный, истёк или уже использован. "
            "Снова введите 8-значный код из приложения. Осталось попыток: {remaining}."
        ),
        "attempts_exhausted": (
            "Слишком много неверных попыток. Получите новый код в приложении "
            "и снова откройте Telegram."
        ),
        "ok_desktop": (
            "✅ <b>Приложение на компьютере подключено</b>\n\n"
            "Вернитесь в HSK AI Desktop — аккаунт откроется автоматически."
        ),
        "ok_mobile": (
            "✅ <b>Приложение на Android подключено</b>\n\n"
            "Вернитесь в приложение HSK AI — аккаунт откроется автоматически."
        ),
        "cancelled": "Подключение отменено. Этот код больше не работает.",
        "invalid": (
            "Код подключения истёк или уже использован. "
            "Создайте новый код в приложении."
        ),
    },
    "tj": {
        "confirm_desktop": (
            "🖥 <b>Пайваст кардани барномаи компютерӣ</b>\n\n"
            "Дастгоҳ: <b>{platform}</b>\n"
            "Версия: <b>{version}</b>\n"
            "Рамз: <code>{code}</code>\n\n"
            "Танҳо агар ин рамзро худатон дар HSK AI кушода бошед, "
            "тасдиқ кунед. Дар акси ҳол бекор кунед."
        ),
        "confirm_mobile": (
            "📱 <b>Пайваст кардани барномаи Android</b>\n\n"
            "Дастгоҳ: <b>{platform}</b>\n"
            "Версия: <b>{version}</b>\n"
            "Рамз: <code>{code}</code>\n\n"
            "Танҳо агар ин рамзро худатон дар HSK AI кушода бошед, "
            "тасдиқ кунед. Дар акси ҳол бекор кунед."
        ),
        "approve": "✅ Тасдиқ",
        "cancel": "Бекор кардан",
        "enter_code": (
            "🔐 <b>Рамзи пайвастшавиро ворид кунед</b>\n\n"
            "Рамзи 8-аломатии дар барномаи HSK AI "
            "нишондодашударо ба ин чат <b>дастӣ фиристед</b>.\n\n"
            "Рамзро ба каси дигар нафиристед."
        ),
        "invalid_code": (
            "Рамз нодуруст, муҳлаташ гузашта ё истифода шудааст. "
            "Рамзи 8-аломатиро аз барнома боз ворид кунед. Кӯшиши боқимонда: {remaining}."
        ),
        "attempts_exhausted": (
            "Кӯшишҳои нодуруст зиёд шуданд. Дар барнома рамзи нав "
            "гиред ва Telegram-ро аз нав кушоед."
        ),
        "ok_desktop": (
            "✅ <b>Барномаи компютерӣ пайваст шуд</b>\n\n"
            "Ба HSK AI Desktop баргардед — ҳисоб худкор кушода мешавад."
        ),
        "ok_mobile": (
            "✅ <b>Барномаи Android пайваст шуд</b>\n\n"
            "Ба барномаи HSK AI баргардед — ҳисоб худкор кушода мешавад."
        ),
        "cancelled": "Пайвастшавӣ бекор шуд. Ин рамз дигар кор намекунад.",
        "invalid": (
            "Муҳлати рамзи пайвастшавӣ гузашт ё он истифода шудааст. "
            "Дар барнома рамзи нав созед."
        ),
    },
}

_ANDROID_COPY = {
    "uz": {
        "choose_language": "📱 <b>HSK AI Android ilovasi</b>\n\nIlovadagi tilni tanlang:",
        "enter_code": (
            "🔐 <b>Android ilovasidagi 8 belgili kodni yuboring</b>\n\n"
            "Kod ilovada ko‘rsatilgan. Uni shu chatga qo‘lda yuboring."
        ),
        "invalid": "Bu ulash havolasi yoki kod eskirgan. Ilovadan qayta boshlang.",
    },
    "ru": {
        "choose_language": "📱 <b>Приложение HSK AI для Android</b>\n\nВыберите язык приложения:",
        "enter_code": (
            "🔐 <b>Отправьте 8-символьный код из Android-приложения</b>\n\n"
            "Код показан в приложении. Отправьте его в этот чат вручную."
        ),
        "invalid": "Ссылка или код подключения истекли. Начните заново в приложении.",
    },
    "tj": {
        "choose_language": "📱 <b>Барномаи HSK AI барои Android</b>\n\nЗабони барномаро интихоб кунед:",
        "enter_code": (
            "🔐 <b>Рамзи 8-аломатиро аз барномаи Android фиристед</b>\n\n"
            "Рамз дар барнома нишон дода шудааст. Онро ба ин чат дастӣ фиристед."
        ),
        "invalid": "Истинод ё рамзи пайвастшавӣ гузаштааст. Аз барнома аз нав оғоз кунед.",
    },
}


def _android_language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇹🇯 Тоҷикӣ", callback_data="android_link:lang:tj"),
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="android_link:lang:ru"),
                InlineKeyboardButton(text="🇺🇿 O‘zbek", callback_data="android_link:lang:uz"),
            ]
        ]
    )


# The Telegram confirmation must name the real device. The previous
# "Mac or else Windows" shortcut would have shown an Android phone as Windows.
_PLATFORM_LABELS = {
    "macos": "Mac",
    "windows": "Windows",
    "android": "Android",
}


def _platform_label(platform: str | None) -> str:
    return _PLATFORM_LABELS.get(
        str(platform or "").strip().lower(),
        "HSK AI",
    )


def _copy_key(base: str, platform: str | None) -> str:
    """Pick the desktop or mobile wording for a platform-aware message."""

    normalized = str(platform or "").strip().lower()
    suffix = "mobile" if normalized in MOBILE_PLATFORMS else "desktop"
    return f"{base}_{suffix}"


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


def _android_language(user) -> str:
    value = str(getattr(user, "language", None) or "ru")
    return value if value in _ANDROID_COPY else "ru"


async def _begin_android_code_entry(
    message: Message,
    state: FSMContext,
    request_id: str,
    language: str,
) -> None:
    await state.clear()
    await state.set_state(DesktopLinkStates.waiting_code)
    await state.update_data(
        android_link_request_id=request_id,
        desktop_link_invalid_attempts=0,
        desktop_link_prompted=True,
    )
    await message.answer(
        _ANDROID_COPY[language]["enter_code"],
        parse_mode="HTML",
    )


@router.message(
    CommandStart(deep_link=True),
    F.text.regexp(r"^/start(?:@\w+)?\s+android_link_[0-9a-fA-F-]{36}\s*$"),
)
async def begin_android_link(
    message: Message,
    state: FSMContext,
    session,
) -> None:
    """Start the native Android registration/link flow from Telegram."""

    raw = str(message.text or "").strip().split()[-1]
    request_id = raw[len(ANDROID_LINK_PREFIX):]
    try:
        _preview = await DesktopAuthService(session, settings).link_request_preview(
            link_request_id=request_id,
            platform="android",
        )
    except DesktopAuthError:
        await message.answer(_ANDROID_COPY["ru"]["invalid"], parse_mode="HTML")
        return

    onboarding = OnboardingService(session)
    user, created = await onboarding.get_or_create_user(
        telegram_id=message.from_user.id,
        full_name=message.from_user.full_name if message.from_user else None,
        username=message.from_user.username if message.from_user else None,
        bot=message.bot,
    )

    await state.clear()
    if created or onboarding_stage(user) == "language":
        await state.update_data(android_link_request_id=request_id)
        await state.set_state(AndroidLinkStates.choosing_language)
        await message.answer(
            _ANDROID_COPY["tj"]["choose_language"],
            reply_markup=_android_language_keyboard(),
            parse_mode="HTML",
        )
        return

    await _begin_android_code_entry(message, state, request_id, _android_language(user))


@router.callback_query(
    AndroidLinkStates.choosing_language,
    F.data.regexp(r"^android_link:lang:(?:uz|ru|tj)$"),
)
async def choose_android_link_language(
    callback: CallbackQuery,
    state: FSMContext,
    session,
) -> None:
    data = await state.get_data()
    request_id = str(data.get("android_link_request_id") or "").strip()
    language = str(callback.data or "").rsplit(":", 1)[-1]
    user, _ = await OnboardingService(session).get_or_create_user(
        telegram_id=callback.from_user.id,
        full_name=callback.from_user.full_name if callback.from_user else None,
        username=callback.from_user.username if callback.from_user else None,
        bot=callback.bot,
    )
    if not request_id or not user or language not in _ANDROID_COPY:
        await callback.answer(_ANDROID_COPY["ru"]["invalid"], show_alert=True)
        return
    user.language = language
    # Keep the normal bot onboarding state consistent. Native Android owns the
    # remaining course questions after the account is linked.
    user.learning_mode = ONBOARDING_MODE_CHOICE_MODE
    await session.commit()
    try:
        await DesktopAuthService(session, settings).link_request_preview(
            link_request_id=request_id,
            platform="android",
        )
    except DesktopAuthError:
        await state.clear()
        await callback.answer(_ANDROID_COPY[language]["invalid"], show_alert=True)
        return

    await callback.answer()
    await _begin_android_code_entry(callback.message, state, request_id, language)


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
    state_data = await state.get_data()
    android_request_id = str(
        state_data.get("android_link_request_id") or ""
    ).strip()
    try:
        service = DesktopAuthService(session, settings)
        if android_request_id:
            preview = await service.link_request_preview_for_code(
                link_request_id=android_request_id,
                display_code=display_code,
                telegram_id=message.from_user.id,
            )
            preview["display_code"] = display_code
        else:
            preview = await service.link_preview(
                display_code=display_code,
                telegram_id=message.from_user.id,
            )
    except DesktopAuthError:
        await _register_invalid_attempt(message, state, language)
        return
    await state.clear()
    platform = preview["platform"]
    await message.answer(
        _COPY[language][_copy_key("confirm", platform)].format(
            platform=_platform_label(platform),
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
        result = await DesktopAuthService(session, settings).approve_link(
            display_code=display_code,
            telegram_id=callback.from_user.id,
        )
    except DesktopAuthError:
        await callback.answer(_COPY[language]["invalid"], show_alert=True)
        return
    if callback.message:
        await callback.message.edit_text(
            _COPY[language][_copy_key("ok", result.get("platform"))],
            parse_mode="HTML",
        )
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
