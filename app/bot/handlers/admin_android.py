"""Admin panel: publishing the Android APK the bot hands out.

One upload, one stored `file_id`, and every learner afterwards gets that exact
file. The panel is deliberately small — upload, check it against the admin's
own chat, withdraw — because the risky part is not the flow but the file: a
`play` or `debug` build installs perfectly and then strands whoever installs
it, so that check is the one thing this panel refuses to skip.
"""

import html
import logging

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.bot.fsm.admin_android import AdminAndroidStates
from app.bot.handlers.android_app import reply_chat_id, send_android_app
from app.config import settings
from app.services.android_release_service import (
    AndroidRelease,
    AndroidReleaseError,
    AndroidReleaseService,
    format_size,
    parse_artifact_name,
    parse_version_text,
)


logger = logging.getLogger(__name__)
router = Router()

PANEL_CALLBACK = "adm:android_panel"


def _is_admin(user_id: int) -> bool:
    admin_ids = [int(x.strip()) for x in settings.ADMIN_IDS.split(",") if x.strip()]
    return user_id in admin_ids


def _panel_keyboard(release: AndroidRelease | None) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="⬆️ Yangi APK yuklash", callback_data="adm_android:upload")]]
    if release:
        rows.append(
            [InlineKeyboardButton(text="📤 O'zimga yuborib ko'rish", callback_data="adm_android:preview")]
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text=(
                        "🔗 Yangilanish havolasini almashtirish"
                        if release.update_url
                        else "🔗 Yangilanish havolasini qo'shish"
                    ),
                    callback_data="adm_android:set_update_url",
                )
            ]
        )
        if release.update_url:
            rows.append(
                [
                    InlineKeyboardButton(
                        text="🔕 Ichki yangilanishni o'chirish",
                        callback_data="adm_android:clear_update_url",
                    )
                ]
            )
        rows.append(
            [InlineKeyboardButton(text="🚫 Tarqatishni to'xtatish", callback_data="adm_android:withdraw")]
        )
    rows.append([InlineKeyboardButton(text="⬅️ Admin panel", callback_data="adm:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor qilish", callback_data=PANEL_CALLBACK)]]
    )


def _back_keyboard() -> InlineKeyboardMarkup:
    """After a refusal. It reopens the panel rather than drawing one from
    memory, so a refused upload can never make a published release look gone."""

    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Android paneli", callback_data=PANEL_CALLBACK)]]
    )


def _confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Chiqarish", callback_data="adm_android:publish")],
            [InlineKeyboardButton(text="✍️ Versiyani o'zim yozaman", callback_data="adm_android:retype")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=PANEL_CALLBACK)],
        ]
    )


async def _panel_state(session):
    """The stored row and what is actually being handed out right now.

    They differ whenever a release manifest is configured, and the admin needs
    to see that before wondering why a link they pasted changed nothing.
    """

    service = AndroidReleaseService(session)
    return await service.current(), await service.serve()


def _served_line(served) -> str:
    if served is None:
        return ""
    if served.source != "manifest":
        return ""
    return (
        "\n\n🤖 <b>Avtomat rejim yoqilgan</b>\n"
        f"Hozir tarqatilayotgani: <b>{html.escape(served.version_text)}</b> "
        f"({served.size_text})\n"
        "Buni GitHub workflow o'zi chiqargan. Qo'lda qo'yilgan havola "
        "e'tiborga olinmaydi."
    )


def _panel_text(release: AndroidRelease | None, served=None) -> str:
    if not release:
        return (
            "📱 <b>Android ilova</b>\n\n"
            "<blockquote>Hozircha hech narsa chiqarilmagan — "
            "<code>/android</code> so'ragan odam «tayyor emas» xabarini oladi.</blockquote>\n\n"
            "Signed <b>direct release</b> APK yuklang."
            + _served_line(served)
        )
    published = release.published_at.strftime("%Y-%m-%d %H:%M UTC")
    if release.can_self_update:
        update_line = (
            "\n\n🔗 <b>Ichki yangilanish yoqilgan</b>\n"
            f"<code>{html.escape(release.update_url)}</code>\n"
            "O'rnatilgan ilovalar profilda «yangi versiya bor» kartasini ko'radi."
        )
    elif release.version_code is None:
        update_line = (
            "\n\n🔕 Ichki yangilanish yo'q — bu release'da versiya kodi yo'q, "
            "ya'ni ilova nimani solishtirishni bilmaydi."
        )
    else:
        update_line = (
            "\n\n🔕 Ichki yangilanish yo'q — o'rnatilgan ilovalar yangi versiyadan "
            "xabar topmaydi. Havola qo'shsangiz, profilda karta chiqadi."
        )
    return (
        "📱 <b>Android ilova</b>\n\n"
        "<blockquote>"
        f"Versiya: <b>{html.escape(release.version_text)}</b>\n"
        f"Hajmi: {release.size_text}\n"
        f"Fayl: <code>{html.escape(release.file_name)}</code>\n"
        f"Chiqarilgan: {published}"
        "</blockquote>\n\n"
        "Shu fayl <code>/android</code> so'raganlarning hammasiga yuboriladi."
        + update_line
        + _served_line(served)
    )


async def _show_panel(callback: CallbackQuery, session, state: FSMContext) -> None:
    await state.clear()
    release, served = await _panel_state(session)
    await callback.message.edit_text(
        _panel_text(release, served),
        reply_markup=_panel_keyboard(release),
        parse_mode="HTML",
    )


@router.message(Command("admin_android"))
async def android_panel_command(message: Message, session, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    await state.clear()
    release, served = await _panel_state(session)
    await message.answer(
        _panel_text(release, served),
        reply_markup=_panel_keyboard(release),
        parse_mode="HTML",
    )


@router.callback_query(F.data == PANEL_CALLBACK)
async def android_panel(callback: CallbackQuery, session, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await callback.answer()
    await _show_panel(callback, session, state)


@router.callback_query(F.data == "adm_android:upload")
async def ask_for_apk(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await callback.answer()
    await state.set_state(AdminAndroidStates.waiting_for_apk)
    await callback.message.edit_text(
        "⬆️ <b>APK faylini yuboring</b>\n\n"
        "<blockquote>Faylni <b>hujjat</b> sifatida yuboring (siqmasdan).\n\n"
        "Kerak bo'lgani: <code>direct</code> flavour, <code>release</code> build, imzolangan.\n"
        "<code>cd android && ./gradlew assembleDirectRelease</code></blockquote>",
        reply_markup=_cancel_keyboard(),
        parse_mode="HTML",
    )


@router.message(StateFilter(AdminAndroidStates.waiting_for_apk), F.document)
async def receive_apk(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return

    document = message.document
    file_name = (document.file_name or "").strip()
    if not file_name.lower().endswith(".apk"):
        await message.answer(
            "❌ Bu APK emas. <code>.apk</code> fayl yuboring.",
            reply_markup=_cancel_keyboard(),
            parse_mode="HTML",
        )
        return

    artifact = parse_artifact_name(file_name)
    if artifact and not artifact.is_distributable:
        # Refused rather than warned: both of these install cleanly and only
        # fail later, in the learner's hands — `play` has no way to pay,
        # `debug` has an application id no release can ever update.
        await state.clear()
        await message.answer(
            f"🚫 <b>Bu build tarqatilmaydi</b>\n\n"
            f"<blockquote>Fayl: <code>{html.escape(file_name)}</code>\n"
            f"Flavour: <b>{artifact.flavor}</b>, build: <b>{artifact.build_type}</b></blockquote>\n\n"
            "<code>direct</code> + <code>release</code> kerak. <code>play</code> buildda "
            "to'lov yo'li yo'q, <code>debug</code> esa boshqa package nomi bilan o'rnatiladi "
            "va keyin release'ga yangilanmaydi.",
            reply_markup=_back_keyboard(),
            parse_mode="HTML",
        )
        return

    await state.update_data(
        apk_file_id=document.file_id,
        apk_file_unique_id=document.file_unique_id,
        apk_file_name=file_name,
        apk_file_size=int(document.file_size or 0),
        apk_version_name=artifact.version_name if artifact else None,
        apk_version_code=artifact.version_code if artifact else None,
    )

    if not artifact:
        await state.set_state(AdminAndroidStates.waiting_for_version)
        await message.answer(
            f"✅ Fayl qabul qilindi — <code>{html.escape(file_name)}</code> "
            f"({format_size(document.file_size or 0)}).\n\n"
            "Fayl nomidan versiyani o'qib bo'lmadi. Versiyani yozing: "
            "<code>1.2.0</code> yoki <code>1.2.0 (3)</code>.",
            reply_markup=_cancel_keyboard(),
            parse_mode="HTML",
        )
        return

    await state.set_state(None)
    await message.answer(
        _confirm_text(file_name, document.file_size or 0, artifact.version_name, artifact.version_code),
        reply_markup=_confirm_keyboard(),
        parse_mode="HTML",
    )


@router.message(
    StateFilter(AdminAndroidStates.waiting_for_apk),
    F.photo | F.video | F.audio | F.voice | F.animation,
)
async def not_a_document(message: Message):
    """A file was sent, but not as a document.

    Deliberately narrow: a catch-all here would swallow the admin's own menu
    presses and commands and leave them stuck in the upload step with no way
    out but the cancel button. Text falls through to the normal handlers.
    """

    if not _is_admin(message.from_user.id):
        return
    await message.answer(
        "❌ APK'ni <b>hujjat</b> sifatida yuboring (skrepka → «Файл»).",
        reply_markup=_cancel_keyboard(),
        parse_mode="HTML",
    )


@router.message(StateFilter(AdminAndroidStates.waiting_for_version), F.text)
async def receive_version(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    try:
        version_name, version_code = parse_version_text(message.text)
    except AndroidReleaseError as error:
        await message.answer(f"❌ {error}", reply_markup=_cancel_keyboard(), parse_mode="HTML")
        return

    data = await state.get_data()
    await state.update_data(apk_version_name=version_name, apk_version_code=version_code)
    await state.set_state(None)
    await message.answer(
        _confirm_text(
            str(data.get("apk_file_name") or ""),
            int(data.get("apk_file_size") or 0),
            version_name,
            version_code,
        ),
        reply_markup=_confirm_keyboard(),
        parse_mode="HTML",
    )


def _confirm_text(file_name: str, file_size: int, version_name: str, version_code: int | None) -> str:
    version = version_name if version_code is None else f"{version_name} ({version_code})"
    return (
        "🔍 <b>Tekshiring</b>\n\n"
        "<blockquote>"
        f"Versiya: <b>{html.escape(version)}</b>\n"
        f"Hajmi: {format_size(file_size)}\n"
        f"Fayl: <code>{html.escape(file_name)}</code>"
        "</blockquote>\n\n"
        "«Chiqarish» bosilgach shu fayl <code>/android</code> so'raganlarning hammasiga ketadi."
    )


@router.callback_query(F.data == "adm_android:retype")
async def retype_version(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await callback.answer()
    await state.set_state(AdminAndroidStates.waiting_for_version)
    await callback.message.edit_text(
        "✍️ Versiyani yozing: <code>1.2.0</code> yoki <code>1.2.0 (3)</code>.",
        reply_markup=_cancel_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "adm_android:publish")
async def publish_apk(callback: CallbackQuery, session, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return

    data = await state.get_data()
    try:
        release = await AndroidReleaseService(session).publish(
            file_id=data.get("apk_file_id"),
            file_unique_id=data.get("apk_file_unique_id"),
            file_name=data.get("apk_file_name"),
            file_size=data.get("apk_file_size"),
            version_name=data.get("apk_version_name"),
            version_code=data.get("apk_version_code"),
            published_by=callback.from_user.id,
        )
    except AndroidReleaseError as error:
        await callback.answer()
        await callback.message.edit_text(
            f"❌ {error}",
            reply_markup=_back_keyboard(),
            parse_mode="HTML",
        )
        return

    await state.clear()
    await callback.answer("Chiqarildi")
    await callback.message.edit_text(
        f"✅ <b>Chiqarildi</b>\n\n{_panel_text(release)}",
        reply_markup=_panel_keyboard(release),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "adm_android:preview")
async def preview_apk(callback: CallbackQuery, session):
    """Send the published file to the admin exactly as a learner receives it."""

    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await callback.answer()
    await send_android_app(
        callback.bot,
        reply_chat_id(callback),
        callback.from_user.id,
        session,
        source="admin_preview",
        track=False,
    )


@router.callback_query(F.data == "adm_android:set_update_url")
async def ask_for_update_url(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await callback.answer()
    await state.set_state(AdminAndroidStates.waiting_for_update_url)
    await callback.message.edit_text(
        "🔗 <b>Yangilanish havolasini yuboring</b>\n\n"
        "<blockquote>Bu — APK turgan to'g'ridan-to'g'ri <code>https://</code> havola "
        "(desktop o'rnatuvchilari turgan R2 bucket'ining o'zi bo'lishi mumkin).\n\n"
        "Aynan shu yerga yuklagan fayl bo'lishi shart — ilova solishtiradigan "
        "versiya shu release'dan olinadi.</blockquote>",
        reply_markup=_cancel_keyboard(),
        parse_mode="HTML",
    )


@router.message(StateFilter(AdminAndroidStates.waiting_for_update_url), F.text)
async def receive_update_url(message: Message, session, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    try:
        release = await AndroidReleaseService(session).set_update_url(message.text)
    except AndroidReleaseError as error:
        await message.answer(f"❌ {error}", reply_markup=_cancel_keyboard(), parse_mode="HTML")
        return
    await state.clear()
    await message.answer(
        "✅ <b>Havola saqlandi</b>\n\n" + _panel_text(release),
        reply_markup=_panel_keyboard(release),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "adm_android:clear_update_url")
async def clear_update_url(callback: CallbackQuery, session, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    release = await AndroidReleaseService(session).clear_update_url()
    await callback.answer("O'chirildi")
    await state.clear()
    await callback.message.edit_text(
        "🔕 <b>Ichki yangilanish o'chirildi</b>\n\n" + _panel_text(release),
        reply_markup=_panel_keyboard(release),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "adm_android:withdraw")
async def withdraw_apk(callback: CallbackQuery, session, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await AndroidReleaseService(session).withdraw()
    await callback.answer("To'xtatildi")
    await state.clear()
    await callback.message.edit_text(
        "🚫 <b>Tarqatish to'xtatildi</b>\n\n" + _panel_text(None),
        reply_markup=_panel_keyboard(None),
        parse_mode="HTML",
    )
