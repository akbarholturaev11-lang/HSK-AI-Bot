from aiogram.fsm.state import State, StatesGroup


class PartnerApplicationStates(StatesGroup):
    waiting_promotion_channel = State()
    waiting_audience_size = State()
    waiting_contact_username = State()


class PartnerPayoutStates(StatesGroup):
    waiting_bank_name = State()
    waiting_account_details = State()
    waiting_holder_name = State()
    waiting_note = State()


class AdminPartnerStates(StatesGroup):
    waiting_usdt_tjs_rate = State()
    waiting_commission_percent = State()
    waiting_commission_fixed = State()
    waiting_signup_bonus = State()
    waiting_min_payout = State()
    waiting_payout_screenshot = State()
    waiting_partner_message = State()
