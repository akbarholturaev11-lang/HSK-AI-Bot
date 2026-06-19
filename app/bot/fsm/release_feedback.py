from aiogram.fsm.state import State, StatesGroup


class ReleaseFeedbackAdminStates(StatesGroup):
    waiting_title = State()
    waiting_content = State()
    waiting_feature = State()
    waiting_send_at = State()


class ReleaseFeedbackUserStates(StatesGroup):
    waiting_required_comment = State()
    waiting_optional_comment = State()
