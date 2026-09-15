from aiogram.fsm.state import State, StatesGroup


class AdminAndroidStates(StatesGroup):
    """Publishing the APK the bot hands out."""

    waiting_for_apk = State()
    waiting_for_version = State()
    waiting_for_update_url = State()
