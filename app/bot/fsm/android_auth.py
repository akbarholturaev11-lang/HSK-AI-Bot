from aiogram.fsm.state import State, StatesGroup


class AndroidLinkStates(StatesGroup):
    """Short-lived state for the Android Telegram-first account flow."""

    choosing_language = State()
