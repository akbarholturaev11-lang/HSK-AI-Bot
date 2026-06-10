from aiogram.fsm.state import State, StatesGroup


class AdminPriceStates(StatesGroup):
    waiting_amount = State()
    waiting_qr_code = State()
    waiting_rate = State()
    waiting_payment_details = State()


class AdminRequiredChannelStates(StatesGroup):
    waiting_channel = State()
