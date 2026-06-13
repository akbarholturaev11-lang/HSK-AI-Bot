from aiogram.fsm.state import State, StatesGroup


class BroadcastStates(StatesGroup):
    waiting_for_target = State()
    waiting_for_text = State()
    waiting_for_button_url = State()
    waiting_for_button_text = State()
