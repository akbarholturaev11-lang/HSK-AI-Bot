"""Admin audio boshqaruv paneli.

Flow:
  /admin_audio
    → HSK level tanlash
      → Darslar ro'yxati (✅ to'liq / 🟡 qisman / ❌ yo'q)
        → Dars tanlash → Audio turi tanlash (vocab / dialogue_N — real dialog soniga qarab)
          → "Faylni yuboring" → Fayl → Saqlandi ✅ → Keyingi tur yoki keyingi dars
"""

import json
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from app.config import settings
from app.repositories.course_lesson_repo import CourseLessonRepository
from app.repositories.course_audio_repo import CourseAudioRepository
from app.bot.fsm.admin_audio import AdminAudioStates
from app.bot.utils.workflow_message import (
    delete_message_safely,
    edit_callback_workflow_message,
    edit_stored_workflow_message,
)

router = Router()

LEVELS = ["hsk1", "hsk2", "hsk3", "hsk4"]
_AUDIO_PANEL_CHAT_ID = "audio_panel_chat_id"
_AUDIO_PANEL_MSG_ID = "audio_panel_msg_id"


# ─── helpers ────────────────────────────────────────────────────────────────

def _is_admin(user_id: int) -> bool:
    admin_ids = [int(x.strip()) for x in settings.ADMIN_IDS.split(",") if x.strip()]
    return user_id in admin_ids


def _parse(value, default=None):
    if value is None or value == "":
        return default or []
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return default or []


def _audio_types_for_lesson(lesson) -> list[str]:
    """Darsning hozirgi materialiga mos audio turlarini qaytaradi."""
    types = ["vocab"]
    dialogues = _parse(lesson.dialogue_json, [])
    if not isinstance(dialogues, list):
        return types
    for index, block in enumerate(dialogues, 1):
        if isinstance(block, dict):
            lines = block.get("dialogue") or block.get("lines") or []
            if not lines:
                continue
            try:
                block_no = int(block.get("block_no") or index)
            except (TypeError, ValueError):
                block_no = index
        else:
            block_no = index
        if block_no > 0:
            types.append(f"dialogue_{block_no}")
    return types


def _audio_type_label(audio_type: str) -> str:
    if audio_type == "vocab":
        return "so'zlar"
    if audio_type.startswith("dialogue_"):
        try:
            n = int(audio_type.split("_", 1)[1])
        except (TypeError, ValueError, IndexError):
            return audio_type
        return f"{n}-dialog"
    return audio_type


def _audio_status_for_lesson(lesson, uploaded_types: set[str] | list[str]) -> dict:
    required = _audio_types_for_lesson(lesson)
    required_set = set(required)
    uploaded_set = set(uploaded_types)
    missing = [audio_type for audio_type in required if audio_type not in uploaded_set]
    uploaded_required = [audio_type for audio_type in required if audio_type in uploaded_set]
    obsolete = sorted(uploaded_set - required_set)
    if not uploaded_required:
        state = "missing"
    elif missing:
        state = "partial"
    else:
        state = "complete"
    return {
        "state": state,
        "required": required,
        "missing": missing,
        "uploaded_required": uploaded_required,
        "obsolete": obsolete,
    }


def _group_audio_by_lesson(rows) -> dict[int, set[str]]:
    grouped: dict[int, set[str]] = {}
    for row in rows:
        grouped.setdefault(int(row.lesson_order), set()).add(row.audio_type)
    return grouped


# ─── keyboards ───────────────────────────────────────────────────────────────

def _level_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="HSK 1", callback_data="adm_audio:level:hsk1"),
            InlineKeyboardButton(text="HSK 2", callback_data="adm_audio:level:hsk2"),
        ],
        [
            InlineKeyboardButton(text="HSK 3", callback_data="adm_audio:level:hsk3"),
            InlineKeyboardButton(text="HSK 4", callback_data="adm_audio:level:hsk4"),
        ],
        [InlineKeyboardButton(text="📊 Statistika", callback_data="adm_audio:stats")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _lessons_keyboard(lessons, status_by_order: dict[int, dict], page: int = 0) -> InlineKeyboardMarkup:
    """Darslar ro'yxati. Status current dars audio turlariga qarab hisoblanadi."""
    page_size = 8
    start = page * page_size
    end = start + page_size
    page_lessons = lessons[start:end]
    level = lessons[0].level if lessons else "hsk1"

    buttons = []
    for lesson in page_lessons:
        status = status_by_order.get(lesson.lesson_order, {})
        state = status.get("state")
        icon = "✅" if state == "complete" else "🟡" if state == "partial" else "❌"
        uploaded_count = len(status.get("uploaded_required") or [])
        required_count = len(status.get("required") or _audio_types_for_lesson(lesson))
        buttons.append([InlineKeyboardButton(
            text=f"{icon} {lesson.lesson_order}. {lesson.title} ({uploaded_count}/{required_count})",
            callback_data=f"adm_audio:lesson:{lesson.id}",
        )])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"adm_audio:page:{level}:{page-1}"))
    if end < len(lessons):
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"adm_audio:page:{level}:{page+1}"))
    if nav:
        buttons.append(nav)

    buttons.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="adm_audio:back_levels")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _audio_types_keyboard(lesson, uploaded_types: set) -> InlineKeyboardMarkup:
    """Audio turi tanlash. Yuklanganlari ✅, yo'qlari ❌."""
    types = _audio_types_for_lesson(lesson)
    buttons = []
    row = []
    for i, atype in enumerate(types):
        icon = "✅" if atype in uploaded_types else "❌"
        label = f"🔉 {_audio_type_label(atype)}"
        row.append(InlineKeyboardButton(
            text=f"{icon} {label}",
            callback_data=f"adm_audio:upload:{lesson.id}:{atype}",
        ))
        if len(row) == 2 or i == len(types) - 1:
            buttons.append(row)
            row = []

    buttons.append([
        InlineKeyboardButton(text="◀️ Darslar", callback_data=f"adm_audio:level:{lesson.level}"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _after_upload_keyboard(lesson, next_type: str | None) -> InlineKeyboardMarkup:
    """Yuklangandan keyin: keyingi tur yoki keyingi dars."""
    buttons = []
    if next_type:
        buttons.append([InlineKeyboardButton(
            text=f"➡️ Keyingi: {_audio_type_label(next_type)}",
            callback_data=f"adm_audio:upload:{lesson.id}:{next_type}",
        )])
    buttons.append([
        InlineKeyboardButton(text="📋 Dars turlari", callback_data=f"adm_audio:lesson:{lesson.id}"),
        InlineKeyboardButton(text="📚 Darslar", callback_data=f"adm_audio:level:{lesson.level}"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ─── /admin_audio entry ──────────────────────────────────────────────────────

@router.message(Command("admin_audio"))
async def admin_audio_entry(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer(
        "🎵 <b>Audio boshqaruv paneli</b>\n\nQaysi HSK darajasi?",
        reply_markup=_level_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "adm:audio_panel")
async def admin_audio_from_panel(callback: CallbackQuery, state: FSMContext):
    """Admin paneldagi '🎵 Audio boshqaruv' tugmasi."""
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        "🎵 <b>Audio boshqaruv paneli</b>\n\nQaysi HSK darajasi?",
        reply_markup=_level_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "adm_audio:back_levels")
async def back_to_levels(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.clear()
    await callback.message.edit_text(
        "🎵 <b>Audio boshqaruv paneli</b>\n\nQaysi HSK darajasi?",
        reply_markup=_level_keyboard(),
        parse_mode="HTML",
    )


# ─── statistika ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_audio:stats")
async def audio_stats(callback: CallbackQuery, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return

    lesson_repo = CourseLessonRepository(session)
    audio_repo = CourseAudioRepository(session)

    lines = ["📊 <b>Audio holati</b>\n"]
    for level in LEVELS:
        lessons = await lesson_repo.list_by_level(level)
        if not lessons:
            continue
        audio_by_order = _group_audio_by_lesson(await audio_repo.list_for_level(level))
        complete = 0
        partial = 0
        required_total = 0
        uploaded_required_total = 0
        for lesson in lessons:
            status = _audio_status_for_lesson(lesson, audio_by_order.get(lesson.lesson_order, set()))
            required_total += len(status["required"])
            uploaded_required_total += len(status["uploaded_required"])
            if status["state"] == "complete":
                complete += 1
            elif status["state"] == "partial":
                partial += 1
        total = len(lessons)
        bar = "▓" * complete + "▒" * partial + "░" * max(total - complete - partial, 0)
        lines.append(
            f"<b>{level.upper()}</b>: {complete}/{total} to'liq  {bar}\n"
            f"  Audio: {uploaded_required_total}/{required_total}"
        )

    await callback.answer()
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="adm_audio:back_levels")]
        ]),
        parse_mode="HTML",
    )


# ─── level → darslar ro'yxati ────────────────────────────────────────────────

async def _show_lessons(callback: CallbackQuery, session, level: str, page: int = 0):
    lesson_repo = CourseLessonRepository(session)
    audio_repo = CourseAudioRepository(session)

    lessons = await lesson_repo.list_by_level(level)
    if not lessons:
        await callback.answer("Bu darajada dars yo'q", show_alert=True)
        return

    audio_by_order = _group_audio_by_lesson(await audio_repo.list_for_level(level))
    status_by_order = {
        lesson.lesson_order: _audio_status_for_lesson(
            lesson,
            audio_by_order.get(lesson.lesson_order, set()),
        )
        for lesson in lessons
    }
    total = len(lessons)
    complete = sum(1 for status in status_by_order.values() if status["state"] == "complete")
    partial = sum(1 for status in status_by_order.values() if status["state"] == "partial")

    await callback.message.edit_text(
        f"📚 <b>{level.upper()}</b> — {total} dars\n"
        f"✅ To'liq audio: <b>{complete}</b> / {total}\n"
        f"🟡 Boshlangan: <b>{partial}</b>\n\n"
        f"Darsni tanlang:",
        reply_markup=_lessons_keyboard(lessons, status_by_order, page),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("adm_audio:level:"))
async def show_lessons_for_level(callback: CallbackQuery, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    level = callback.data.split(":")[-1]
    await callback.answer()
    await _show_lessons(callback, session, level, page=0)


@router.callback_query(F.data.startswith("adm_audio:page:"))
async def paginate_lessons(callback: CallbackQuery, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    parts = callback.data.split(":")
    level = parts[2]
    page = int(parts[3])
    await callback.answer()
    await _show_lessons(callback, session, level, page=page)


# ─── dars → audio turi tanlash ───────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm_audio:lesson:"))
async def show_audio_types(callback: CallbackQuery, session):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return

    lesson_id = int(callback.data.split(":")[-1])
    lesson_repo = CourseLessonRepository(session)
    audio_repo = CourseAudioRepository(session)

    lesson = await lesson_repo.get_by_id(lesson_id)
    if not lesson:
        await callback.answer("Dars topilmadi", show_alert=True)
        return

    uploaded_rows = await audio_repo.list_for_lesson(lesson.level, lesson.lesson_order)
    uploaded_types = {r.audio_type for r in uploaded_rows}
    status = _audio_status_for_lesson(lesson, uploaded_types)
    missing = status["missing"]

    if not missing:
        status_text = "✅ Hozirgi dialog formatiga mos barcha audio yuklangan!"
    else:
        status_text = f"❌ Kerak: {', '.join(_audio_type_label(item) for item in missing)}"
    if status["obsolete"]:
        status_text += (
            "\n⚠️ Eski/ortiqcha audio turlar ishlatilmaydi: "
            + ", ".join(status["obsolete"])
        )

    await callback.answer()
    await callback.message.edit_text(
        f"🎵 <b>{lesson.level.upper()} · Dars {lesson.lesson_order}</b>\n"
        f"📖 {lesson.title}\n\n"
        f"{status_text}\n\n"
        f"Qaysi audio turini yuklaysiz?",
        reply_markup=_audio_types_keyboard(lesson, uploaded_types),
        parse_mode="HTML",
    )


# ─── audio turi tanlandi → fayl kutish ───────────────────────────────────────

@router.callback_query(F.data.startswith("adm_audio:upload:"))
async def ask_for_audio_file(callback: CallbackQuery, session, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return

    parts = callback.data.split(":")
    lesson_id = int(parts[2])
    audio_type = parts[3]

    lesson_repo = CourseLessonRepository(session)
    lesson = await lesson_repo.get_by_id(lesson_id)
    if not lesson:
        await callback.answer("Dars topilmadi", show_alert=True)
        return
    if audio_type not in _audio_types_for_lesson(lesson):
        await callback.answer("Bu darsda bunday audio turi yo'q", show_alert=True)
        return

    await state.set_state(AdminAudioStates.waiting_for_audio)
    await state.update_data(
        lesson_id=lesson_id,
        audio_type=audio_type,
        level=lesson.level,
        lesson_order=lesson.lesson_order,
    )

    type_label = _audio_type_label(audio_type)
    await callback.answer()
    await edit_callback_workflow_message(
        callback,
        state,
        f"🎙 <b>{lesson.level.upper()} · Dars {lesson.lesson_order} · {audio_type}</b>\n"
        f"📖 {lesson.title}\n\n"
        f"⬇️ <b>{type_label}</b> uchun audio faylni yuboring\n"
        f"(voice yoki mp3/ogg fayl)",
        chat_id_key=_AUDIO_PANEL_CHAT_ID,
        message_id_key=_AUDIO_PANEL_MSG_ID,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"adm_audio:lesson:{lesson_id}")]
        ]),
    )


# ─── fayl qabul qilish ───────────────────────────────────────────────────────

@router.message(StateFilter(AdminAudioStates.waiting_for_audio), F.voice | F.audio | F.document)
async def receive_audio_file(message: Message, session, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return

    data = await state.get_data()
    lesson_id = data.get("lesson_id")
    audio_type = data.get("audio_type")
    level = data.get("level")
    lesson_order = data.get("lesson_order")

    # file_id olish
    if message.voice:
        file_id = message.voice.file_id
    elif message.audio:
        file_id = message.audio.file_id
    elif message.document:
        file_id = message.document.file_id
    else:
        await delete_message_safely(message)
        await edit_stored_workflow_message(
            message,
            state,
            "❌ Audio, voice yoki fayl yuboring",
            chat_id_key=_AUDIO_PANEL_CHAT_ID,
            message_id_key=_AUDIO_PANEL_MSG_ID,
        )
        return

    audio_repo = CourseAudioRepository(session)
    lesson_repo = CourseLessonRepository(session)

    await audio_repo.upsert(level=level, lesson_order=lesson_order, audio_type=audio_type, file_id=file_id)
    await delete_message_safely(message)

    lesson = await lesson_repo.get_by_id(lesson_id)
    if not lesson:
        await edit_stored_workflow_message(
            message,
            state,
            "✅ Saqlandi!",
            chat_id_key=_AUDIO_PANEL_CHAT_ID,
            message_id_key=_AUDIO_PANEL_MSG_ID,
        )
        await state.clear()
        return

    # Keyingi yuklanmagan audio turini topamiz
    all_types = _audio_types_for_lesson(lesson)
    uploaded_rows = await audio_repo.list_for_lesson(level, lesson_order)
    uploaded_types = {r.audio_type for r in uploaded_rows}
    missing = [t for t in all_types if t not in uploaded_types]
    next_type = missing[0] if missing else None

    remaining = (
        f"\n⏳ Qolgan: {', '.join(_audio_type_label(item) for item in missing)}"
        if missing
        else "\n🎉 Bu darsning barcha audiolari yuklandi!"
    )

    await edit_stored_workflow_message(
        message,
        state,
        f"✅ <b>Saqlandi!</b>\n"
        f"📍 {level.upper()} · Dars {lesson_order} · <code>{audio_type}</code> ({_audio_type_label(audio_type)})"
        f"{remaining}",
        chat_id_key=_AUDIO_PANEL_CHAT_ID,
        message_id_key=_AUDIO_PANEL_MSG_ID,
        reply_markup=_after_upload_keyboard(lesson, next_type),
    )
    await state.clear()


@router.message(StateFilter(AdminAudioStates.waiting_for_audio))
async def wrong_file_type(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    await delete_message_safely(message)
    await edit_stored_workflow_message(
        message,
        state,
        "⚠️ Voice yoki audio fayl yuboring (matn emas)",
        chat_id_key=_AUDIO_PANEL_CHAT_ID,
        message_id_key=_AUDIO_PANEL_MSG_ID,
    )
