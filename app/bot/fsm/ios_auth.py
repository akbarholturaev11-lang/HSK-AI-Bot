from aiogram.fsm.state import State, StatesGroup


class IOSLinkStates(StatesGroup):
    """Short-lived state for the native iPhone Telegram-first account flow."""

    choosing_language = State()
