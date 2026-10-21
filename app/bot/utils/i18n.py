"""Bot lookup compatibility backed entirely by generated local catalogs."""
from app.bot.generated.bot_i18n import COURSE_I18N, TEXTS, bot_message
from app.bot.generated.common_i18n import COMMON_MESSAGES
from app.bot.generated.course_i18n import COURSE_MESSAGES

def _gemini_texts_active() -> bool:
    """Gemini asosiy provaydermi? Limit matnlari shunga qarab tanlanadi."""
    try:
        from app.services.ai_provider import gemini_active

        return gemini_active()
    except Exception:
        return False


BOT_SHARED_COMMON_KEYS = {
    "menu_bar_hint": "bot.menu.barHint",
    "menu_profile": "bot.menu.profile",
    "menu_subscription": "bot.menu.subscription",
    "menu_course_mode": "bot.menu.courseMode",
    "menu_partner": "bot.menu.partner",
    "menu_help": "bot.menu.help",
    "language_picker_tj": "bot.languagePicker.tajik",
    "language_picker_ru": "bot.languagePicker.russian",
    "language_picker_uz": "bot.languagePicker.uzbek",
    "language_picker_uz_onboarding": "bot.languagePicker.uzbekOnboarding",
    "course_mode_entry_course": "bot.onboarding.courseModeEntry",
    "course_mode_entry_chat": "bot.onboarding.freeChatEntry",
    "daily_practice_finish_course": "bot.practiceFinish.course",
    "daily_practice_finish_chat": "bot.practiceFinish.freeChat",
    "daily_practice_check_view_answers": "bot.practiceCheck.viewAnswers",
    "trial_lesson_previous": "bot.lessonNavigation.previous",
    "trial_lesson_next": "bot.lessonNavigation.next",
    "course_miniapp_open": "bot.courseKeyboard.miniAppOpen",
    "course_intro_vocab": "bot.courseKeyboard.introVocab",
    "course_dialogue_grammar": "bot.courseKeyboard.dialogueGrammar",
    "course_grammar_exercises": "bot.courseKeyboard.grammarExercises",
    "course_homework_next_lesson": "bot.courseKeyboard.homeworkNextLesson",
    "course_continue": "bot.courseKeyboard.continue",
    "course_review_yes": "bot.courseKeyboard.reviewYes",
    "course_review_no": "bot.courseKeyboard.reviewNo",
    "course_reminder_cancel": "bot.courseKeyboard.reminderCancel",
    "course_v3_open": "bot.courseKeyboard.v3Open",
    "course_study_open": "bot.courseKeyboard.studyOpen",
    "subscription_miniapp_open_button": "bot.subscription.openMiniApp",
    "subscription_free_mode_button": "bot.subscription.freeMode",
    "payment_method_visa_button": "bot.subscription.visaButton",
    "subscription_button_10_days": "bot.subscription.plan10Days",
    "subscription_button_1_month": "bot.subscription.plan1Month",
    "subscription_button_3_months": "bot.subscription.plan3Months",
    "course_reminder_set_button": "bot.promoButton.reminder",
    "hint_section_course_title": "navigation.course",
    "hint_section_practice_title": "navigation.practice",
    "hint_section_profile_title": "navigation.profile",
    "hint_section_rating_title": "navigation.rating",
}
BOT_SHARED_COURSE_KEYS = {
    "hint_section_voice_title": "nav.voice",
    "subscription_expired_later_button": "onboardingNotification.later",
}


def _lookup_text(key: str, lang: str):
    # Shared Bot UI copy uses generated local catalogs. Keep the old Bot
    # dictionaries as fallback for safe rollout and source drift.
    shared_common_key = BOT_SHARED_COMMON_KEYS.get(key)
    text = (COMMON_MESSAGES.get(lang, {}).get(shared_common_key)
            if shared_common_key else None)

    if text is None:
        shared_course_key = BOT_SHARED_COURSE_KEYS.get(key)
        text = (COURSE_MESSAGES.get(lang, {}).get(shared_course_key)
                if shared_course_key else None)

    if text is None:
        text = TEXTS.get(lang, {}).get(key)

    if text is None:
        text = COURSE_I18N.get(lang, {}).get(key)

    if text is None:
        text = TEXTS.get("ru", {}).get(key)

    if text is None:
        text = COURSE_I18N.get("ru", {}).get(key)

    return text


def t(key: str, lang: str = "ru", **kwargs) -> str:
    if key.startswith("bot."):
        code = "tj" if lang in ("tg", "tg-TJ") else lang
        code = code if code in TEXTS else "ru"
        template = bot_message(key[len("bot."):], code)
        if template is None:
            return key
        try:
            return template.format(**kwargs) if kwargs else template
        except (KeyError, ValueError):
            return template

    # Generated UI namespace is local Python data; legacy keys retain their
    # existing Gemini-aware lookup, wording and Russian fallback behavior.
    if key.startswith("common."):
        code = "tj" if lang in ("tg", "tg-TJ") else lang
        code = code if code in COMMON_MESSAGES else "ru"
        template = COMMON_MESSAGES[code].get(key[len("common."):])
        if template is None:
            return key
        try:
            return template.format(**kwargs) if kwargs else template
        except (KeyError, ValueError):
            return template
    lang = lang if lang in TEXTS else "ru"

    # Gemini yoqilganda limitlar boshqacha (matn cheksiz, rasm/ovoz 5/kun), shuning
    # uchun avval `<kalit>_gemini` variantini qidiramiz. Variant yo'q bo'lsa oddiy
    # kalit ishlatiladi — ya'ni faqat limitga aloqador matnlar o'zgaradi.
    text = None
    if _gemini_texts_active():
        text = _lookup_text(f"{key}_gemini", lang)

    if text is None:
        text = _lookup_text(key, lang)

    if text is None:
        return key

    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
