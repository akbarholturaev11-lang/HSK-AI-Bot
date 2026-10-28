"""Server-side revision binding for existing reminder pickers; no new UI copy."""
from uuid import uuid4

from sqlalchemy import select

from app.bot.keyboards.course import reminder_time_keyboard
from app.db.models.smart_reminder import SmartReminderPreference

INTERACTION_KEY = "smart_reminder_interaction"


async def smart_reminder_time_keyboard(session, state, user_id, lang):
    # Observational only: no lock/grant and no Smart row creation. Actual
    # callbacks authenticate and CAS again, so a concurrent OFF wins safely.
    with session.no_autoflush:
        revision = await session.scalar(select(SmartReminderPreference.revision).where(
            SmartReminderPreference.user_id == user_id))
    if revision is None or state is None:
        if state is not None:
            await state.update_data(**{INTERACTION_KEY: None})
        return reminder_time_keyboard(lang)
    nonce = uuid4().hex
    await state.update_data(**{INTERACTION_KEY: {"user_id": user_id, "revision": revision, "nonce": nonce}})
    return reminder_time_keyboard(lang, nonce=nonce)
