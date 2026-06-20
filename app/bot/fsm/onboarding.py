from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    choosing_language = State()
    choosing_level = State()
    daily_practice = State()
    choosing_trial_lesson = State()
