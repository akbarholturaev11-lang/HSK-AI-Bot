from aiogram.fsm.state import State, StatesGroup


class DesktopLinkStates(StatesGroup):
    waiting_code = State()
