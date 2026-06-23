from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from app.bot.fsm.onboarding import OnboardingStates
from app.bot.fsm.partner import PartnerApplicationStates, PartnerPayoutStates
from app.services.required_channel_service import is_admin_user


ONBOARDING_STATES = {
    OnboardingStates.choosing_language.state,
    OnboardingStates.choosing_level.state,
    OnboardingStates.daily_practice.state,
    OnboardingStates.choosing_trial_lesson.state,
}
PARTNER_STATES = {
    PartnerApplicationStates.waiting_promotion_channel.state,
    PartnerApplicationStates.waiting_audience_size.state,
    PartnerApplicationStates.waiting_contact_username.state,
    PartnerPayoutStates.waiting_bank_name.state,
    PartnerPayoutStates.waiting_account_details.state,
    PartnerPayoutStates.waiting_holder_name.state,
    PartnerPayoutStates.waiting_note.state,
    PartnerPayoutStates.waiting_qr_code.state,
}
PARTNER_MENU_TEXTS = {
    "🤝 Ҳамкорӣ",
    "🤝 Партнёрство",
    "🤝 Hamkorlik",
}
PENDING_FORCE_SUB_TEXT = "force_sub_pending_text"
PENDING_FORCE_SUB_MESSAGE_ID = "force_sub_pending_message_id"
PENDING_FORCE_SUB_ACTION = "force_sub_pending_action"
PENDING_FORCE_SUB_PAYLOAD = "force_sub_pending_payload"
FORCE_SUB_ACTION_OPEN_COURSE = "open_course_mode"
FORCE_SUB_ACTION_OPEN_FREE_QA = "open_free_qa_mode"


def _is_partner_entry_event(event: Any) -> bool:
    if isinstance(event, Message):
        text = (event.text or "").strip()
        if not text:
            return False
        command = text.split(maxsplit=1)[0].split("@", maxsplit=1)[0]
        return text in PARTNER_MENU_TEXTS or command == "/partner"
    if isinstance(event, CallbackQuery):
        return (event.data or "").startswith("partner:")
    return False


class RequiredChannelMiddleware(BaseMiddleware):
    def __init__(self, sessionmaker):
        self.sessionmaker = sessionmaker

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ):
        tg_user = getattr(event, "from_user", None)
        if not tg_user:
            return await handler(event, data)

        if is_admin_user(tg_user.id):
            return await handler(event, data)

        if isinstance(event, CallbackQuery) and (event.data or "") == "force_sub:check":
            return await handler(event, data)

        if isinstance(event, Message) and (event.text or "").strip().startswith("/start"):
            return await handler(event, data)

        if _is_partner_entry_event(event):
            return await handler(event, data)

        state = data.get("state")
        if state and await state.get_state() in ONBOARDING_STATES | PARTNER_STATES:
            return await handler(event, data)

        return await handler(event, data)
