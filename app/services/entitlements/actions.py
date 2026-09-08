"""Cheklanadigan harakatlar ro'yxati.

Bugun har bo'lim o'z kalitini o'zi nomlaydi: `lesson`/`voice`/`placement`/
`training_test` (`course_feature_usages`), `recognition`/`memorize`/
`pronunciation` (`course_miniapp_events`), `quiz_per_lesson_24h`/`audio_daily`
(`StudyMiniAppService`). Uchta nomlash sxemasi, uchta saqlash joyi.

Bu modul ularning ustidan bitta nomlash beradi. Kalit `sirt.harakat`
ko'rinishida: prefiks paywall matnini tanlaydi, qolgani aniq harakatni.

Eski kalitlar YO'QOLMAYDI — `LEGACY_FEATURE_KEYS` orqali ikki tomonlama
o'girish bor, chunki hisoblagichlar o'sha eski kalitlar bilan yozilgan va
tarixiy qatorlar qayta nomlanmaydi.
"""

from __future__ import annotations


# --- darslar ---------------------------------------------------------------
LESSON_START = "lesson.start"

# --- bot AI ----------------------------------------------------------------
AI_TEXT = "ai.text"
AI_PHOTO = "ai.photo"
AI_VOICE = "ai.voice"

# --- AI Voice roleplay -----------------------------------------------------
SPEAKING_SESSION = "speaking.session"

# --- Mini App mashq bo'limlari ---------------------------------------------
PRACTICE_RECOGNITION = "practice.recognition"
PRACTICE_MEMORIZE = "practice.memorize"
PRACTICE_PRONUNCIATION = "practice.pronunciation"
PRACTICE_PLACEMENT = "practice.placement"
PRACTICE_TRAINING_TEST = "practice.training_test"
PRACTICE_MISTAKE_REVIEW = "practice.mistake_review"

# --- Study Mini App --------------------------------------------------------
STUDY_QUIZ = "study.quiz"
STUDY_AUDIO = "study.audio"
STUDY_FLASHCARD_TRANSLATE = "study.flashcard_translate"


ACTIONS = (
    LESSON_START,
    AI_TEXT,
    AI_PHOTO,
    AI_VOICE,
    SPEAKING_SESSION,
    PRACTICE_RECOGNITION,
    PRACTICE_MEMORIZE,
    PRACTICE_PRONUNCIATION,
    PRACTICE_PLACEMENT,
    PRACTICE_TRAINING_TEST,
    PRACTICE_MISTAKE_REVIEW,
    STUDY_QUIZ,
    STUDY_AUDIO,
    STUDY_FLASHCARD_TRANSLATE,
)

ACTION_SET = frozenset(ACTIONS)


# --- paywall sirtlari ------------------------------------------------------
SURFACE_LESSON = "lesson"
SURFACE_AI = "ai"
SURFACE_VOICE = "voice"
SURFACE_SPEAKING = "speaking"
SURFACE_PRACTICE = "practice"
SURFACE_STUDY = "study"

#: Prefiksdan sirtga. Paywall matni SHU sirt bo'yicha tanlanadi, action bo'yicha
#: emas — 14 ta action uchun 14 xil matn yozish shart emas.
_PREFIX_SURFACE = {
    "lesson": SURFACE_LESSON,
    "ai": SURFACE_AI,
    "speaking": SURFACE_SPEAKING,
    "practice": SURFACE_PRACTICE,
    "study": SURFACE_STUDY,
}

#: Prefiks qoidasidan istisnolar: bot ovozining o'z matni bor.
_ACTION_SURFACE_OVERRIDES = {
    AI_VOICE: SURFACE_VOICE,
}


def surface_for(action: str) -> str:
    """Shu harakat uchun paywall sirti."""
    if action in _ACTION_SURFACE_OVERRIDES:
        return _ACTION_SURFACE_OVERRIDES[action]
    prefix = str(action or "").split(".", 1)[0]
    return _PREFIX_SURFACE.get(prefix, SURFACE_LESSON)


ACTION_SURFACE = {action: surface_for(action) for action in ACTIONS}


# --- eski kalitlar bilan ko'prik -------------------------------------------
#: Yangi action -> hisoblagichlar bugun ishlatadigan kalit.
#:
#: Diqqat: `practice.mistake_review` ataylab `training_test` ga boradi. Bu
#: hozirgi xatti-harakat (`course_mistake_service.py:663-685`): xatolar ustida
#: ishlash training_test slotini yeydi. Ko'chirishda buni saqlash shart, aks
#: holda bepul foydalanuvchi kutilmaganda bitta qo'shimcha slot oladi.
LEGACY_FEATURE_KEYS = {
    LESSON_START: "lesson",
    AI_VOICE: "voice",
    SPEAKING_SESSION: "voice",
    PRACTICE_RECOGNITION: "recognition",
    PRACTICE_MEMORIZE: "memorize",
    PRACTICE_PRONUNCIATION: "pronunciation",
    PRACTICE_PLACEMENT: "placement",
    PRACTICE_TRAINING_TEST: "training_test",
    PRACTICE_MISTAKE_REVIEW: "training_test",
    STUDY_QUIZ: "quiz_per_lesson_24h",
    STUDY_AUDIO: "audio_daily",
    STUDY_FLASHCARD_TRANSLATE: "flashcard_translate_daily",
}

#: Mashq bo'limlari — `course_miniapp_events` da kunlik sanaladiganlar.
DAILY_EVENT_ACTIONS = frozenset(
    {
        PRACTICE_RECOGNITION,
        PRACTICE_MEMORIZE,
        PRACTICE_PRONUNCIATION,
        PRACTICE_PLACEMENT,
        PRACTICE_TRAINING_TEST,
    }
)

#: Serverga pul turadigan AI harakatlari — byudjet tekshiruvi shularga tegishli.
AI_BUDGET_ACTIONS = frozenset(
    {AI_TEXT, AI_PHOTO, AI_VOICE, SPEAKING_SESSION, PRACTICE_PRONUNCIATION}
)


def normalize(action: str) -> str:
    """Noma'lum kalitni xavfsiz holga keltiradi.

    Noma'lum action `ValueError` tashlamaydi — chaqiruvchi limit yo'lida
    yiqilib qolmasin. Uning o'rniga eng cheklangan ma'lum action qaytadi.
    """
    value = str(action or "").strip()
    if value in ACTION_SET:
        return value
    return LESSON_START
