from aiogram.fsm.state import State, StatesGroup


QA_MODE_LEVEL_CHOICE_KEY = "qa_mode_level_choice"


class OnboardingStates(StatesGroup):
    choosing_language = State()
    choosing_level = State()
    daily_practice = State()
    choosing_trial_lesson = State()
