import asyncio
import difflib
import json
import logging
import random
import re
import unicodedata
import uuid
from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import func, select, update

from app.config import settings
from app.db.models.voice_practice_session import VoicePracticeSession
from app.db.models.ai_usage import AIUsageEvent
from app.db.models.course_miniapp_profile import CourseMiniAppProfile
from app.db.models.user import User
from app.repositories.user_repo import UserRepository
from app.repositories.course_lesson_repo import CourseLessonRepository
from app.repositories.course_progress_repo import CourseProgressRepository
from app.services import course_daily_window
from app.services.ai_service import AIService, AIUsageResult
from app.services.ai_provider import GEMINI_FAST_MODEL
from app.services.ai_usage_budget_service import AIUsageBudgetService, BudgetRecordResult
from app.services.study_miniapp_service import StudyMiniAppService
from app.services.course_mistake_service import CourseMistakeService
from app.services.course_word_mastery_service import CourseWordMasteryService
from app.services.course_gamification_service import CourseGamificationService
from app.services.course_miniapp_lesson_service import CourseMiniAppLessonService
from app.services.learning_signals import LearningSignalsService
from app.services import course_v3_vocab


logger = logging.getLogger(__name__)

PINYIN_UMLAUT_TRANSLATION = str.maketrans(
    {
        "ü": "v",
        "ǖ": "v",
        "ǘ": "v",
        "ǚ": "v",
        "ǜ": "v",
        "Ü": "v",
        "Ǖ": "v",
        "Ǘ": "v",
        "Ǚ": "v",
        "Ǜ": "v",
    }
)

# Bepul (obunasiz) user KUNIGA shuncha AI Voice sessiya ochadi. Ilgari bu
# umrbod hisoblanardi — bir marta ishlatgan user boshqa hech qachon ocholmasdi.
FREE_TOTAL_SESSIONS = 1
# Bepul (obunasiz) userlar uchun talaffuz baholash kunlik STT kvotasi.
# ASOSIY kirish nazorati — Course Mini App "pronunciation" kunlik gate'i
# (kuniga 1 to'liq sessiya, /api/v3/practice/daily-gate). Bu yerdagi kvota esa
# faqat XARAJAT himoyasi: bitta sessiya (≈10 so'z + qayta urinishlar) bemalol
# sig'adi, lekin cheksiz qayta urinish OpenAI STT xarajatini cheklaydi.
FREE_PRONOUNCE_DAILY = 25
# Talaffuz "o'tdi" chegarasi. Klient ham shu qiymatni ko'rsatadi
# (course_v3_pronunciation.html: score>=60), shuning uchun bitta joyda.
PRONOUNCE_PASS_SCORE = 60
MAX_DIALOGS_PER_SESSION = 7
# AI qaytaradigan xato turlari. `course_mistakes.category` bilan bir xil
# nomlanadi, shunda end_session ularni to'g'ridan-to'g'ri uzata oladi.
VOICE_ERROR_TYPES = frozenset({"grammar", "word", "pronunciation"})
MAX_AUDIO_BYTES = 5 * 1024 * 1024
# Klaviatura orqali yuborilgan xabar uzunligi (Mini App'da ham 200 belgi cheklovi bor).
MAX_TEXT_CHARS = 200
# Javobga endi 2 ta "nima deyish mumkin" taklifi ham kiradi (~70 token).
# Chegara kichik qolsa JSON kesiladi va butun javob AI_RESPONSE_INVALID bo'lardi.
VOICE_REPLY_MAX_TOKENS = 340
# "Nima deyish?" varag'ida ko'rsatiladigan takliflar soni.
MAX_REPLY_SUGGESTIONS = 2

ROLE_PROMPTS = {
    "lily": "You are Lily, a cheerful and empathetic young Chinese friend. React warmly, laugh naturally, and keep beginners talking without sounding like a tutor.",
    "chen": "You are Chen, a calm and practical Chinese travel companion. You are concise, observant, and help the learner handle realistic daily situations.",
    "xiao_mei": "You are Xiao Mei, an energetic university student. You speak casually, show curiosity, and make natural friendly reactions.",
    "teacher_li": "You are Teacher Li, a patient but precise Chinese teacher. Guide with short questions and correct only important mistakes without lecturing.",
    "manager_wang": "You are Manager Wang, a professional Chinese manager. Use polite workplace Chinese, realistic business reactions, and a composed tone.",
    "friend": "You are a warm Chinese friend. Be curious, informal, and encouraging.",
    "roommate": "You are the learner's Chinese roommate. Discuss realistic home and daily-life situations.",
    "seller": "You are a lively Chinese shop seller. Practice prices, quantities, choices, and bargaining.",
    "classmate": "You are a Chinese classmate. Discuss classes, plans, campus life, and homework naturally.",
    "social": "You are an engaging Chinese conversation partner. Adapt the topic to the learner's reply.",
}

# Qat'iy daraja nazorati (ENG muhim): AI hech qachon userning HSK darajasidan
# yuqori so'z yoki grammatika ishlatmasligi kerak. Har bir daraja uchun aniq
# so'z/gap uzunligi cheklovi beriladi.
LEVEL_GUIDANCE = {
    "beginner": "Learner is an absolute beginner (HSK1). Use ONLY the ~150 most basic HSK1 words. Sentences must be 3-6 characters, present tense, no idioms.",
    "hsk1": "Learner is HSK1. Use ONLY HSK1 vocabulary and grammar. Short sentences (3-7 characters), no HSK2+ words, no idioms or slang.",
    "hsk2": "Learner is HSK2. Use ONLY HSK1-HSK2 vocabulary and grammar. Simple sentences (up to ~9 characters). Avoid any HSK3+ words.",
    "hsk3": "Learner is HSK3. Use ONLY HSK1-HSK3 vocabulary and grammar. Everyday sentences. Avoid HSK4+ words and complex written-style structures.",
    "hsk4": "Learner is HSK4. Use ONLY HSK1-HSK4 vocabulary and grammar. Natural but not advanced; avoid HSK5+ words, literary idioms, and long clauses.",
    "hsk1_2": "Learner knows HSK1-HSK2. Use ONLY HSK1-HSK2 vocabulary and grammar. Simple short sentences, no HSK3+ words.",
    "hsk3_4": "Learner knows HSK3-HSK4. Use ONLY HSK1-HSK4 vocabulary and grammar. Avoid HSK5+ words and literary structures.",
}


def _level_guidance(level: str) -> str:
    return LEVEL_GUIDANCE.get(level) or LEVEL_GUIDANCE["hsk1"]


LANGUAGE_NAMES = {"ru": "Russian", "tj": "Tajik", "uz": "Uzbek"}

# Maqsad suhbat REGISTRINI tanlaydi, vazifa bermaydi — o'quvchi darsda emas,
# suhbatda ekanini his qilishi kerak.
GOAL_REGISTER = {
    "travel": "This learner is preparing to travel in China, so lean toward travel-shaped situations.",
    "study_china": "This learner is preparing to study in China, so lean toward campus and student-life situations.",
    "work_china": "This learner is preparing to work in China, so lean toward workplace and everyday-professional situations.",
    "daily_communication": "This learner wants everyday conversation, so lean toward ordinary daily-life situations.",
    "hsk_exam": "This learner is preparing for the HSK exam, so keep the language close to textbook-standard everyday topics.",
}

# Eng kuchli zaiflik AI ga NIMANI tuzatishini aytadi, lekin gapiriladigan
# javobni o'zgartirmaydi — aks holda suhbat darsga aylanib qolardi.
WEAKNESS_NOTE = {
    "grammar": "This learner most often makes GRAMMAR mistakes (word order, particles, measure words), so when they make one put the fix in `correction` and keep your spoken reply about the conversation.",
    "word": "This learner most often picks the WRONG WORD, so when they do put the fix in `correction` and keep your spoken reply about the conversation.",
    "character": "This learner most often confuses similar WORDS, so when they do put the fix in `correction` and keep your spoken reply about the conversation.",
    "pronunciation": "This learner most often produces unclear or confused SOUNDS, so when a word comes out wrong put the fix in `correction` and keep your spoken reply about the conversation.",
    "listening": "This learner struggles most with LISTENING, so keep your sentences short and clearly structured.",
}

# Har bir rol uchun bir nechta ochilish varianti — sessiya boshlanganda tasodifiy
# biri tanlanadi, shunda AI har safar bir xil gap bilan boshlamaydi.
OPENING_MESSAGES = {
    "friend": [
        {
            "chinese_reply": "你好！我来了，别害羞，先跟我说一句中文吧。",
            "suggestions": [
                {
                    "zh": "你好，很高兴认识你",
                    "pinyin": "Nǐ hǎo, hěn gāoxìng rènshi nǐ",
                    "translations": {"uz": "Salom, siz bilan tanishganimdan xursandman", "ru": "Привет, рад(а) познакомиться", "tj": "Салом, аз шиносоӣ бо шумо шодам"},
                },
                {
                    "zh": "我在学中文",
                    "pinyin": "Wǒ zài xué Zhōngwén",
                    "translations": {"uz": "Men xitoy tilini o'rganyapman", "ru": "Я учу китайский", "tj": "Ман забони чиниро меомӯзам"},
                },
            ],
            "pinyin": "Nǐ hǎo! Wǒ lái le, bié hàixiū, xiān gēn wǒ shuō yí jù Zhōngwén ba.",
            "translations": {
                "uz": "Ni hao! Keldim, uyalmang, avval menga xitoycha bitta gap ayting.",
                "ru": "Нихао! Я здесь, не стесняйтесь, скажите мне сначала одну фразу по-китайски.",
                "tj": "Ниҳао! Ман омадам, шарм накунед, аввал ба ман як ҷумлаи чинӣ гӯед.",
            },
        },
        {
            "chinese_reply": "嘿，是我！今天过得怎么样？",
            "suggestions": [
                {
                    "zh": "很好，谢谢！",
                    "pinyin": "Hěn hǎo, xièxie!",
                    "translations": {"uz": "Yaxshi, rahmat!", "ru": "Хорошо, спасибо!", "tj": "Хуб, раҳмат!"},
                },
                {
                    "zh": "今天不太好",
                    "pinyin": "Jīntiān bú tài hǎo",
                    "translations": {"uz": "Bugun unchalik yaxshi emas", "ru": "Сегодня не очень", "tj": "Имрӯз чандон хуб не"},
                },
            ],
            "pinyin": "Hēi, shì wǒ! Jīntiān guò de zěnme yàng?",
            "translations": {
                "uz": "Salom, bu men! Bugun kuningiz qanday o'tyapti?",
                "ru": "Привет, это я! Как прошёл твой день?",
                "tj": "Салом, ин манам! Имрӯз рӯзатон чӣ хел гузашт?",
            },
        },
        {
            "chinese_reply": "哈喽！好久不见，想我了吗？",
            "suggestions": [
                {
                    "zh": "我想你了",
                    "pinyin": "Wǒ xiǎng nǐ le",
                    "translations": {"uz": "Sizni sog'indim", "ru": "Я скучал(а)", "tj": "Ман шуморо пазмон шудам"},
                },
                {
                    "zh": "是的，很想",
                    "pinyin": "Shì de, hěn xiǎng",
                    "translations": {"uz": "Ha, juda", "ru": "Да, очень", "tj": "Ҳа, хеле"},
                },
            ],
            "pinyin": "Hā lóu! Hǎojiǔ bú jiàn, xiǎng wǒ le ma?",
            "translations": {
                "uz": "Salom! Ancha bo'ldi ko'rishmaganimizga, sog'indingizmi?",
                "ru": "Привет! Давно не виделись, скучали по мне?",
                "tj": "Салом! Дер боз надида будем, дилам бароятон танг шуд?",
            },
        },
    ],
    "teacher_li": [
        {
            "chinese_reply": "哎，找到你啦！今天想聊点什么呢？",
            "suggestions": [
                {
                    "zh": "我们说说学校吧",
                    "pinyin": "Wǒmen shuōshuo xuéxiào ba",
                    "translations": {"uz": "Keling, maktab haqida gaplashaylik", "ru": "Давайте поговорим о школе", "tj": "Биёед дар бораи мактаб гап занем"},
                },
                {
                    "zh": "我不知道，你说吧",
                    "pinyin": "Wǒ bù zhīdào, nǐ shuō ba",
                    "translations": {"uz": "Bilmadim, siz ayting", "ru": "Не знаю, скажите вы", "tj": "Намедонам, шумо гӯед"},
                },
            ],
            "pinyin": "Āi, zhǎodào nǐ la! Jīntiān xiǎng liáo diǎn shénme ne?",
            "translations": {
                "uz": "Voy, sizni topdim! Bugun nima haqida gaplashamiz?",
                "ru": "Ага, нашёл вас! О чём поговорим сегодня?",
                "tj": "Ҳа, шуморо ёфтам! Имрӯз дар бораи чӣ гап занем?",
            },
        },
        {
            "chinese_reply": "嗨，是我。我们随便聊聊吧，别紧张。",
            "suggestions": [
                {
                    "zh": "好的，谢谢老师",
                    "pinyin": "Hǎo de, xièxie lǎoshī",
                    "translations": {"uz": "Xo'p, rahmat ustoz", "ru": "Хорошо, спасибо, учитель", "tj": "Хуб, раҳмат устод"},
                },
                {
                    "zh": "我想说中文",
                    "pinyin": "Wǒ xiǎng shuō Zhōngwén",
                    "translations": {"uz": "Men xitoycha gapirmoqchiman", "ru": "Я хочу говорить по-китайски", "tj": "Ман мехоҳам чинӣ гап занам"},
                },
            ],
            "pinyin": "Hāi, shì wǒ. Wǒmen suíbiàn liáo liao ba, bié jǐnzhāng.",
            "translations": {
                "uz": "Salom, bu men. Keling, erkin suhbatlashamiz, xavotir olmang.",
                "ru": "Привет, это я. Давайте просто поболтаем, не волнуйтесь.",
                "tj": "Салом, ин манам. Биёед озод сӯҳбат кунем, ташвиш накашед.",
            },
        },
        {
            "chinese_reply": "你好呀，今天心情怎么样？",
            "suggestions": [
                {
                    "zh": "我很高兴",
                    "pinyin": "Wǒ hěn gāoxìng",
                    "translations": {"uz": "Men juda xursandman", "ru": "Я очень рад(а)", "tj": "Ман хеле шодам"},
                },
                {
                    "zh": "今天不太好",
                    "pinyin": "Jīntiān bú tài hǎo",
                    "translations": {"uz": "Bugun unchalik yaxshi emas", "ru": "Сегодня не очень", "tj": "Имрӯз чандон хуб не"},
                },
            ],
            "pinyin": "Nǐ hǎo ya, jīntiān xīnqíng zěnme yàng?",
            "translations": {
                "uz": "Salom, bugun kayfiyatingiz qanday?",
                "ru": "Привет, как настроение сегодня?",
                "tj": "Салом, имрӯз кайфиятатон чӣ хел?",
            },
        },
    ],
}

# Suhbat davomida AI aynan bitta mavzuga (masalan doim "sevgilingiz bormi") yopishib
# qolmasligi uchun har bir sessiyaga (session id asosida, barqaror) 3 ta mavzu tanlanadi.
TOPIC_POOL = [
    "food they like or ate today",
    "weekend or free-time plans",
    "the weather",
    "family or friends",
    "a hobby",
    "movies or music they enjoy",
    "travel or a place they want to visit",
    "shopping",
    "school or work life",
    "sports",
    "their hometown",
    "favorite season",
    "morning routine",
    "future goals or dreams",
    "a funny memory",
    "phone or technology habits",
    "cooking",
    "pets or animals",
    "holidays or celebrations",
    "favorite things or colors",
]


class VoicePracticeError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class VoicePracticeService:
    def __init__(self, session):
        self.session = session
        self.user_repo = UserRepository(session)
        self.progress_repo = CourseProgressRepository(session)
        self.lesson_repo = CourseLessonRepository(session)
        # Mintaqa bitta so'rov ichida o'zgarmaydi.
        self._offset_cache: dict[int, int] = {}

    @staticmethod
    def _extract_words(payload: dict | None, limit: int) -> list[dict]:
        words = []
        for item in (payload or {}).get("vocabulary", []):
            if not isinstance(item, dict) or not item.get("zh"):
                continue
            words.append(
                {
                    "zh": str(item.get("zh") or "")[:40],
                    "pinyin": str(item.get("pinyin") or "")[:80],
                    "meaning": str(item.get("meaning") or "")[:160],
                }
            )
            if len(words) >= limit:
                break
        return words

    async def _course_context(self, user, language: str) -> dict:
        empty = {"lesson_id": None, "lesson_order": None, "title": "", "words": [], "review_words": []}
        progress = await self.progress_repo.get_by_user_id(user.id)
        if not progress or not progress.current_lesson_id:
            return empty
        lesson = await self.lesson_repo.get_by_id(progress.current_lesson_id)
        if not lesson:
            return empty
        lesson_service = CourseMiniAppLessonService(self.session)
        payload = await lesson_service.get_payload(
            lesson_order=int(lesson.lesson_order),
            lang=language,
            level=str(lesson.level),
        )
        words = self._extract_words(payload, 4)

        # Takror so'zlari endi TASODIFIY emas — SRS jadvalidan olinadi, ya'ni
        # o'quvchining aynan muddati kelgan so'zlari suhbatga qo'shiladi.
        # Ilgari bu yerda oldingi darslar bo'ylab 10 tagacha `get_payload`
        # chaqirilardi (har biri to'liq dars payload'ini qurardi) va ulardan
        # `random.sample` bilan 6 ta so'z olinardi.
        current_order = int(lesson.lesson_order)
        review_words = await self._srs_review_words(
            user, language, exclude={w["zh"] for w in words}
        )
        return {
            "lesson_id": lesson.id,
            "lesson_order": current_order,
            "title": str(lesson.title or "")[:160],
            "level": str(lesson.level or ""),
            "words": words,
            "review_words": review_words,
        }

    async def _srs_review_words(
        self, user, language: str, *, exclude: set[str], limit: int = 6
    ) -> list[dict]:
        """Takrorga tegishli so'zlar — SRS (Leitner) jadvalidan.

        Mashq bo'limlari bilan bir xil manba, shuning uchun suhbatda aynan
        o'quvchi unutishga yaqin so'zlar eshitiladi. Pinyin/ma'no lug'at
        indeksidan olinadi — u process ichida keshlangan, SO'ROV QILMAYDI.

        DIQQAT: bu yerda SRS faqat O'QILADI. `record_drill` chaqirilmaydi —
        suhbatda aytilgan so'z baholangan mashq emas, qutini oldinga surish
        o'quvchining rejalashtirilgan takrorlarini jimgina yeb qo'yardi.
        """
        try:
            mastery = CourseWordMasteryService(self.session)
            band, current_part, offset_minutes = await mastery.context(user)
            rows = await mastery.select(
                user,
                skill="pronunciation",
                level=band,
                current_part=current_part,
                limit=max(limit * 2, 10),
                timezone_offset_minutes=offset_minutes,
            )
        except Exception:  # noqa: BLE001 — SRS o'qilmasa suhbat baribir boshlanadi
            logger.exception("Voice SRS review lookup failed for user %s", getattr(user, "id", None))
            return []

        index = {
            str(item.get("zh") or ""): item
            for item in course_v3_vocab.words_for_level(band)
        }
        # Muddati kelgan takrorlar birinchi, keyin qolgan o'rgatilgan so'zlar.
        ordered = [r for r in rows if r.get("kind") == "review"] + [
            r for r in rows if r.get("kind") != "review"
        ]
        out: list[dict] = []
        seen = set(exclude)
        for row in ordered:
            zh = str((row or {}).get("zh") or "").strip()
            if not zh or zh in seen:
                continue
            seen.add(zh)
            entry = index.get(zh) or {}
            meanings = entry.get("meaning") or {}
            out.append(
                {
                    "zh": zh[:40],
                    "pinyin": str(entry.get("pinyin") or "")[:80],
                    "meaning": str(meanings.get(language) or meanings.get("ru") or "")[:160],
                }
            )
            if len(out) >= limit:
                break
        return out

    async def _learner_plan(self, user, telegram_id: int, level: str) -> dict:
        """Sessiya boshida muzlatiladigan moslashuv rejasi.

        Ilovaning qolgan qismi allaqachon shu signallar bo'yicha moslashadi
        (kunlik reja, xatolar bo'limi, SRS mashqlari) — AI Voice esa faqat HSK
        darajasini bilardi. Butun blok himoyalangan: signal o'qilmasa suhbat
        oddiy (moslashuvsiz) rejimda davom etadi.
        """
        plan: dict = {}
        try:
            result = await self.session.execute(
                select(CourseMiniAppProfile).where(CourseMiniAppProfile.user_id == user.id)
            )
            # DIQQAT: profil YARATILMAYDI — `start_session` o'qish yo'li.
            profile = result.scalar_one_or_none()
            progress = await self.progress_repo.get_by_user_id(user.id)
            signals = await LearningSignalsService(self.session).load(
                user, profile=profile, progress=progress, level=level
            )
        except Exception:  # noqa: BLE001 — moslashuv suhbatni yiqitmasin
            logger.exception("Voice learner signals failed for user %s", getattr(user, "id", None))
            return {}

        plan["goal"] = str(signals.goal or "")
        plan["focus"] = str(signals.preferred_focus or "")
        weakness = {k: int(v or 0) for k, v in (signals.weakness or {}).items()}
        top = max(weakness.items(), key=lambda kv: kv[1], default=("", 0))
        plan["weak"] = top[0] if top[1] > 0 else ""

        # Qayta sinash uchun bitta o'tgan xato: o'quvchining aynan xitoycha
        # jumlasi va to'g'ri varianti. Boshqa mashq turlaridagi variant tanlash
        # savollari mos kelmaydi, shuning uchun ikkala tomon ham xitoycha
        # bo'lishi shart.
        try:
            overview = await CourseMistakeService(self.session).overview(telegram_id, limit=6)
            for entry in (overview or {}).get("items") or []:
                question = str(entry.get("question") or "").strip()
                answer = str(entry.get("correct_answer") or "").strip()
                if not question or not answer or question == answer:
                    continue
                if not self._cjk_chars(question) or not self._cjk_chars(answer):
                    continue
                plan["retest"] = [{"q": question[:60], "a": answer[:60]}]
                break
        except Exception:  # noqa: BLE001
            logger.exception("Voice mistake retest lookup failed for user %s", telegram_id)
        return plan

    @staticmethod
    def _day_start(offset_minutes: int = 0) -> datetime:
        """Joriy limit kunining boshlanishi, o'quvchining mintaqasida.

        Oyna Course limitlari bilan bir xil joydan hisoblanadi, shuning uchun
        AI Voice va Mashq limitlari bir vaqtda yangilanadi.
        """
        return course_daily_window.day_start(offset_minutes)

    async def _offset_minutes(self, telegram_id: int) -> int:
        """O'quvchining vaqt mintaqasi (daqiqada), Mini App profilidan.

        Profil bo'lmasa 0 — eski UTC oynasi.
        """
        key = int(telegram_id)
        cached = self._offset_cache.get(key)
        if cached is not None:
            return cached
        result = await self.session.execute(
            select(CourseMiniAppProfile.timezone_offset_minutes)
            .join(User, User.id == CourseMiniAppProfile.user_id)
            .where(User.telegram_id == key)
        )
        offset = course_daily_window.normalize_offset_minutes(result.scalar_one_or_none() or 0)
        self._offset_cache[key] = offset
        return offset

    @staticmethod
    def _is_paid(user) -> bool:
        return StudyMiniAppService.is_paid_user(user)

    async def _is_paid_telegram_user(self, telegram_id: int) -> bool:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        return self._is_paid(user)

    async def _ensure_budget_available(self, telegram_id: int) -> None:
        access = await AIUsageBudgetService(self.session).can_use_ai(telegram_id)
        if access.allowed:
            return
        raise VoicePracticeError(
            access.message_key or "ai_budget_cooldown",
            "AI usage budget is temporarily unavailable.",
            403,
        )

    @staticmethod
    def _budget_notice_payload(*records: BudgetRecordResult | None) -> dict | None:
        for record in records:
            if not record:
                continue
            if record.cooldown_started or record.budget_depleted:
                return {
                    "code": record.message_key or (
                        "ai_budget_depleted_notice" if record.budget_depleted else "ai_budget_cooldown_notice"
                    ),
                    "cooldown_started": bool(record.cooldown_started),
                    "budget_depleted": bool(record.budget_depleted),
                    "cooldown_hours": int(record.cooldown_hours),
                }
        return None

    async def _session_count(self, telegram_id: int, *, today_only: bool) -> int:
        # Limit faqat HAQIQIY suhbat uchun yonadi. Ilgari sessiya QATORI
        # yaratilishi kifoya edi — AI xato bersa yoki mikrofonga ruxsat
        # berilmasa ham bepul o'quvchi kunlik slotidan ayrilardi.
        query = select(func.count(VoicePracticeSession.id)).where(
            VoicePracticeSession.user_telegram_id == telegram_id,
            VoicePracticeSession.turn_count > 0,
        )
        if today_only:
            offset = await self._offset_minutes(telegram_id)
            query = query.where(VoicePracticeSession.started_at >= self._day_start(offset))
        result = await self.session.execute(query)
        return int(result.scalar_one() or 0)

    async def _pronounce_count_today(self, telegram_id: int) -> int:
        """Bugun shu user nechta talaffuz (STT) urinishi qilganini sanaydi."""
        offset = await self._offset_minutes(telegram_id)
        query = select(func.count(AIUsageEvent.id)).where(
            AIUsageEvent.user_telegram_id == telegram_id,
            AIUsageEvent.source == "voice_practice_pronounce",
            AIUsageEvent.created_at >= self._day_start(offset),
        )
        result = await self.session.execute(query)
        return int(result.scalar_one() or 0)

    async def remaining_free_sessions(self, user) -> int | None:
        """Bugun yana nechta bepul voice sessiya qolgan. None = limitsiz.

        Kunlik reja "hozir boshlab bo'lmaydigan" vazifani bermasligi kerak,
        shuning uchun u shu hisobga tayanadi. Limit KUNLIK (umrbod emas).
        """
        if self._is_paid(user):
            return None
        used = await self._session_count(int(getattr(user, "telegram_id", 0) or 0), today_only=True)
        return max(0, FREE_TOTAL_SESSIONS - used)

    async def user_status(self, telegram_id: int) -> dict:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            raise VoicePracticeError("USER_NOT_FOUND", "Voice Practice'ni ochishdan oldin botni /start qiling.", 404)

        paid = self._is_paid(user)
        # Bepul limit ham KUNLIK sanaladi: bir marta ishlatgan user ertaga
        # yana ochadi. Ilgari bu bepul userlar uchun umrbod hisob edi.
        used = await self._session_count(telegram_id, today_only=True)
        limit = None if paid else FREE_TOTAL_SESSIONS

        # Kurs progressi: user o'z HSK bandida nechta darsni tugatgan. Mashq
        # sahifalari (ieroglif tanish / talaffuz / yodlash) kontentni o'rganilgan
        # darslar bilan cheklashi uchun ishlatiladi. Band mos kelmasa 0.
        def _band(value) -> str:
            v = str(value or "").strip().lower()
            if v.startswith("hsk4"):
                return "hsk4"
            return v if v in {"hsk1", "hsk2", "hsk3"} else "hsk1"

        completed_lessons = 0
        try:
            progress = await CourseProgressRepository(self.session).get_by_user_id(user.id)
            if progress and _band(progress.level) == _band(getattr(user, "level", None)):
                completed_lessons = int(getattr(progress, "completed_lessons_count", 0) or 0)
        except Exception:  # noqa: BLE001
            completed_lessons = 0

        return {
            "is_paid": paid,
            "plan": "premium" if paid else "free",
            "remaining_voice_limit": -1 if paid else max(0, limit - used),
            # Limit qachon ochilishi — UTC ISO. Klient buni o'z mintaqasida
            # ko'rsatadi; server formatlangan soat qaytarmaydi.
            "reset_at": (
                None
                if paid
                else course_daily_window.next_day_reset(
                    await self._offset_minutes(telegram_id)
                ).isoformat()
            ),
            "level": getattr(user, "level", None) or "hsk1",
            "language": getattr(user, "language", None) or "ru",
            "completed_lessons": completed_lessons,
        }

    async def start_session(
        self,
        telegram_id: int,
        *,
        role: str,
        level: str,
        language: str,
        voice: str,
    ) -> dict:
        if role not in ROLE_PROMPTS:
            raise VoicePracticeError("INVALID_ROLE", "Unknown conversation role.")
        level = (level or "").strip().lower()
        if level.startswith("hsk4"):
            level = "hsk4"  # users.level "hsk4a"/"hsk4b" bands map to HSK4 speech level
        if level not in {"beginner", "hsk1_2", "hsk3_4", "hsk1", "hsk2", "hsk3", "hsk4"}:
            raise VoicePracticeError("INVALID_LEVEL", "Unknown HSK level.")
        if language not in LANGUAGE_NAMES:
            language = "ru"
        if voice not in {"female", "male"}:
            voice = "female"

        status = await self.user_status(telegram_id)
        if not status["is_paid"] and status["remaining_voice_limit"] <= 0:
            raise VoicePracticeError("LIMIT_EXCEEDED", "Voice Practice limit reached.", 403)
        if status["is_paid"]:
            await self._ensure_budget_available(telegram_id)

        user = await self.user_repo.get_by_telegram_id(telegram_id)
        course_context = await self._course_context(user, language) if user else {
            "lesson_id": None, "lesson_order": None, "title": "", "words": [], "review_words": []
        }
        offset_minutes = await self._offset_minutes(telegram_id)
        await self._retire_stale_sessions(telegram_id, offset_minutes)
        item = await self._reusable_session(telegram_id, offset_minutes)
        if item is None:
            item = VoicePracticeSession(id=str(uuid.uuid4()), user_telegram_id=telegram_id)
            self.session.add(item)
        item.role = role
        item.level = level
        item.language = language
        item.voice = voice
        item.status = "active"
        item.ended_at = None
        item.history = []
        item.corrections = []
        item.lesson_id = course_context.get("lesson_id")
        item.target_words = course_context.get("words") or []
        item.review_words = course_context.get("review_words") or []
        # Moslashuv rejasi sessiya boshida MUZLATILADI: `_generate_reply` bir
        # sessiyada 7 marta ishlaydi, har safar qayta hisoblash so'rov narxini
        # 7 ga ko'paytirar va murabbiylik suhbat o'rtasida siljirdi. Klientga
        # QAYTARILMAYDI — bu ichki murabbiylik ma'lumoti.
        item.plan_json = await self._learner_plan(user, telegram_id, level) if user else {}
        await self.session.commit()

        next_status = await self.user_status(telegram_id)
        return {
            "session_id": item.id,
            "user_status": {"is_paid": status["is_paid"], "plan": status["plan"]},
            "remaining_limit": next_status["remaining_voice_limit"],
            "character": role,
            "course_context": course_context,
            "opening_message": self._opening_message(role, language),
            "max_dialogs": MAX_DIALOGS_PER_SESSION,
        }

    async def _retire_stale_sessions(self, telegram_id: int, offset_minutes: int) -> None:
        """Kechagi ochiq qolgan sessiyalarni yopadi.

        Ilova majburan yopilsa `/session/end` chaqirilmaydi va qator abadiy
        `active` bo'lib qolardi. Cron kerak emas — keyingi start o'zi tozalaydi.
        """
        await self.session.execute(
            update(VoicePracticeSession)
            .where(
                VoicePracticeSession.user_telegram_id == telegram_id,
                VoicePracticeSession.status == "active",
                VoicePracticeSession.started_at < self._day_start(offset_minutes),
            )
            .values(status="abandoned", ended_at=datetime.now(timezone.utc))
        )

    async def _reusable_session(
        self, telegram_id: int, offset_minutes: int
    ) -> VoicePracticeSession | None:
        """Bugungi hali gapirilmagan sessiya qatori (bo'lsa).

        `_session_count` endi `turn_count > 0` ni sanaydi, ya'ni gapirilmagan
        qator limitni yoqmaydi. Shu sababli start tugmasini qayta-qayta bosish
        cheksiz qator yaratishi mumkin edi — qatorni qayta ishlatib, buni
        kunlik bittaga cheklaymiz.
        """
        result = await self.session.execute(
            select(VoicePracticeSession)
            .where(
                VoicePracticeSession.user_telegram_id == telegram_id,
                VoicePracticeSession.turn_count == 0,
                VoicePracticeSession.started_at >= self._day_start(offset_minutes),
            )
            .order_by(VoicePracticeSession.started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_active_session(self, telegram_id: int, session_id: str) -> VoicePracticeSession:
        result = await self.session.execute(
            select(VoicePracticeSession)
            .where(VoicePracticeSession.id == session_id)
            .where(VoicePracticeSession.user_telegram_id == telegram_id)
            .limit(1)
        )
        item = result.scalar_one_or_none()
        if not item or item.status != "active":
            raise VoicePracticeError("SESSION_NOT_FOUND", "Voice session not found.", 404)
        return item

    @staticmethod
    def _clean_reply(raw: str) -> dict:
        try:
            data = json.loads(raw)
        except (TypeError, json.JSONDecodeError) as error:
            raise VoicePracticeError("AI_RESPONSE_INVALID", "AI returned an invalid response.", 502) from error

        chinese = str(data.get("chinese_reply") or "").strip()
        if not chinese:
            raise VoicePracticeError("AI_RESPONSE_INVALID", "AI returned an empty response.", 502)
        correction = str(data.get("correction") or "").strip()[:700] or None
        # Xato TURI. Ilgari suhbatdagi HAR QANDAY xato "pronunciation" deb
        # yozilardi — klaviaturadan yozilgan grammatik xato ham. Bu zaiflik
        # signalini (LearningSignals._weakness) va kunlik rejani buzardi.
        error_type = str(data.get("error_type") or "").strip().lower()
        if error_type not in VOICE_ERROR_TYPES:
            error_type = ""
        if not correction:
            error_type = "none"
        elif not error_type:
            # Tasniflab bo'lmagan xato uchun loyihaning mavjud odati "word"
            # (qarang course_mistake_service._category, learning_signals).
            error_type = "word"
        return {
            "chinese_reply": chinese[:500],
            "pinyin": str(data.get("pinyin") or "").strip()[:700],
            "translation": str(data.get("translation") or "").strip()[:700],
            "correction": correction,
            "error_type": error_type,
            "suggestions": VoicePracticeService._clean_suggestions(data.get("suggestions")),
        }

    @staticmethod
    def _clean_suggestions(raw) -> list[dict]:
        """"Nima deyish?" varag'i uchun takliflar.

        AI ularni suhbat javobi bilan BIR chaqiruvda qaytaradi, ya'ni
        qo'shimcha so'rov ham, qo'shimcha kechikish ham yo'q. Yaroqsiz javob
        bo'lsa bo'sh ro'yxat qaytadi va klient doimiy xavfsiz iboralarga
        qaytadi — varaq hech qachon bo'sh qolmaydi.
        """
        if not isinstance(raw, list):
            return []
        out: list[dict] = []
        seen: set[str] = set()
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            zh = str(entry.get("zh") or "").strip()[:40]
            # Xitoycha bo'lmagan taklif klaviaturaga qo'yilsa foydasiz.
            if not zh or zh in seen or not VoicePracticeService._cjk_chars(zh):
                continue
            seen.add(zh)
            out.append(
                {
                    "zh": zh,
                    "pinyin": str(entry.get("pinyin") or "").strip()[:80],
                    "translation": str(entry.get("translation") or "").strip()[:160],
                }
            )
            if len(out) >= MAX_REPLY_SUGGESTIONS:
                break
        return out

    @staticmethod
    def _opening_message(role: str, language: str) -> dict:
        variants = OPENING_MESSAGES.get(role) or OPENING_MESSAGES["friend"]
        message = random.choice(variants)
        translations = message.get("translations") or {}
        suggestions = []
        for entry in (message.get("suggestions") or [])[:MAX_REPLY_SUGGESTIONS]:
            entry_tr = entry.get("translations") or {}
            suggestions.append(
                {
                    "zh": str(entry.get("zh") or ""),
                    "pinyin": str(entry.get("pinyin") or ""),
                    "translation": str(entry_tr.get(language) or entry_tr.get("ru") or ""),
                }
            )
        return {
            "chinese_reply": str(message.get("chinese_reply") or ""),
            "pinyin": str(message.get("pinyin") or ""),
            "translation": str(translations.get(language) or translations.get("ru") or ""),
            "correction": None,
            "error_type": "none",
            "suggestions": suggestions,
        }

    async def _generate_reply(self, item: VoicePracticeSession, transcription: str) -> tuple[dict, AIUsageResult]:
        target_language = LANGUAGE_NAMES.get(item.language, "Russian")
        recent = list(item.history or [])[-4:]
        target_words = json.dumps(list(item.target_words or [])[:3], ensure_ascii=False)
        review_words = json.dumps(list(item.review_words or [])[:6], ensure_ascii=False)
        next_dialog_no = int(item.turn_count or 0) + 1
        is_closing_dialog = next_dialog_no >= MAX_DIALOGS_PER_SESSION
        closing_instruction = (
            "THIS IS THE FINAL EXCHANGE: no matter the topic, warmly wrap up now — give a short natural "
            "reason to go, say a friendly goodbye in Chinese (e.g. 再见/下次聊), and DO NOT ask any follow-up question."
            if is_closing_dialog
            else "End with one short playful follow-up question when natural."
        )
        # O'tgan darslardan so'zlarni suhbatga qo'shib takrorlatish — endi barcha
        # rollar uchun, faqat 2-3 tasi butun suhbat davomida tarqoq holda.
        review_list = list(item.review_words or [])[:6]
        if review_list:
            review_instruction = (
                f"The learner already studied these words before: {review_words}. "
                "Across this whole conversation (not all in one reply), naturally weave in 2-3 of them into what "
                "you say, spread over different turns, so the learner hears and can reuse them — it must not feel "
                "like a vocabulary drill. "
            )
            if item.role == "teacher_li":
                review_instruction += "Occasionally give a light, encouraging nudge to try using one yourself. "
        else:
            review_instruction = ""
        # Har bir sessiya (session id asosida barqaror) o'zining 3 ta mavzusini oladi,
        # shunda AI har safar bir xil mavzularga (masalan doim "sevgilingiz bormi") qaytmaydi.
        topic_rng = random.Random(item.id)
        session_topics = topic_rng.sample(TOPIC_POOL, k=min(3, len(TOPIC_POOL)))
        topic_instruction = (
            "Naturally guide the conversation across these topics during the session (one at a time, shift when "
            f"it feels natural, don't force all of them in one reply): {', '.join(session_topics)}. "
        )
        # Moslashuv bloki — QAT'IY 3 jumladan oshmaydi. Sabab: flash-lite kichik
        # model, uzun system prompt eng muhim qoidani (STRICT LEVEL RULE)
        # suyultirib yuboradi. Reja bo'sh bo'lsa blok umuman chiqmaydi va
        # prompt moslashuvdan oldingi holatiga qaytadi.
        plan = item.plan_json if isinstance(item.plan_json, dict) else {}
        learner_lines: list[str] = []
        goal_line = GOAL_REGISTER.get(str(plan.get("goal") or ""))
        if goal_line:
            learner_lines.append(goal_line)
        weak_line = WEAKNESS_NOTE.get(str(plan.get("weak") or ""))
        if weak_line:
            learner_lines.append(weak_line)
        retest = plan.get("retest")
        if isinstance(retest, list) and retest and isinstance(retest[0], dict):
            wrong = str(retest[0].get("q") or "").strip()[:60]
            right = str(retest[0].get("a") or "").strip()[:60]
            if wrong and right:
                learner_lines.append(
                    f'Earlier this learner said "{wrong}" when the correct form was "{right}"; at most ONCE in '
                    "this whole conversation ask something where that structure would naturally come up, never "
                    "mention it was a past mistake and never ask them to repeat it."
                )
        learner_instruction = (" ".join(learner_lines[:3]) + " ") if learner_lines else ""

        # Suhbatda allaqachon aytilgan maqsad so'zlar — model bir xil so'zni
        # qayta-qayta surmasligi uchun. So'rov qilmaydi, saqlangan tarixdan.
        spoken = "".join(
            str(entry.get("user") or "")
            for entry in list(item.history or [])
            if isinstance(entry, dict)
        )
        already_used = [
            zh
            for zh in (
                str((word or {}).get("zh") or "")
                for word in [*list(item.target_words or []), *review_list]
                if isinstance(word, dict)
            )
            if zh and zh in spoken
        ]
        used_instruction = (
            f"The learner has already used {json.dumps(already_used[:8], ensure_ascii=False)} in this chat, "
            "so don't push those again. "
            if already_used
            else ""
        )
        messages = [
            {
                "role": "system",
                "content": (
                    f"{ROLE_PROMPTS[item.role]} "
                    f"STRICT LEVEL RULE (most important): {_level_guidance(item.level)} "
                    "Never use any word or grammar above the learner's level, even if it feels natural. "
                    "If you must reference something harder, replace it with a simpler word the learner knows. "
                    f"Current-lesson target words: {target_words}. {used_instruction}"
                    f"{learner_instruction}{review_instruction}"
                    "Fast voice roleplay. Reply in 1 short Chinese sentence, rarely 2. "
                    "Use one target word only if natural. Be playful and warm: joke, laugh, lightly tease weak "
                    "answers, never humiliate; switch topic if the learner seems uncomfortable. "
                    f"{topic_instruction}"
                    "Talk like a real person chatting with a friend, not a textbook: vary your sentence openers "
                    "and reactions every turn, and never reuse the exact phrasing or interjection you used earlier "
                    "in this same conversation (see the message history). This is a real casual chat, not a lesson "
                    "or class — never say things like 'let's start' or explicitly frame it as studying. "
                    f"{closing_instruction} Translate into {target_language}. "
                    "Correct only important errors. "
                    "JSON only: chinese_reply, pinyin, translation, correction, error_type, suggestions. "
                    "Use null correction when the learner's Chinese was fine. "
                    "error_type classifies that correction: \"grammar\" (word order, particle, "
                    "measure word, aspect, missing/extra function word), \"word\" (wrong or "
                    "non-existent word, wrong meaning), \"pronunciation\" (the transcript shows a "
                    "real but wrong near-homophone of what they clearly meant). "
                    "Use \"none\" when correction is null. "
                    "suggestions = exactly 2 things THE LEARNER could say back to you right now: "
                    "they must be natural, useful answers to what you just said (if you asked a "
                    "question, they must actually answer it), different from each other, and STRICTLY "
                    "within the learner's level rule above. Each is "
                    f'{{\"zh\": Chinese, \"pinyin\": pinyin with tone marks, \"translation\": {target_language}}}. '
                    "Keep them short (3-8 characters)."
                ),
            }
        ]
        for entry in recent:
            if not isinstance(entry, dict):
                continue
            user_text = str(entry.get("user") or "").strip()
            assistant_text = str(entry.get("assistant") or "").strip()
            if user_text:
                messages.append({"role": "user", "content": user_text[:360]})
            if assistant_text:
                messages.append({"role": "assistant", "content": assistant_text[:360]})
        messages.append({"role": "user", "content": transcription[:500]})

        # AI Voice suhbatini tezlashtirish uchun Gemini eng tez modeli (flash-lite)
        # bilan javob beradi; Gemini yo'q/xato bo'lsa OpenAI gpt-4o-mini zaxira.
        # JSON sxema (chinese_reply/pinyin/translation/correction) o'zgarmaydi.
        ai = AIService()
        usage_result = await ai.complete_messages_with_usage(
            messages=messages,
            openai_model="gpt-4o-mini",
            response_format={"type": "json_object"},
            max_completion_tokens=VOICE_REPLY_MAX_TOKENS,
            temperature=0.85,
            frequency_penalty=0.5,
            presence_penalty=0.3,
            gemini_model=GEMINI_FAST_MODEL,
        )
        return self._clean_reply(usage_result.content), usage_result

    async def process_message(
        self,
        telegram_id: int,
        *,
        session_id: str,
        audio_bytes: bytes,
        filename: str,
        text: str = "",
    ) -> dict:
        if not settings.ai_enabled:
            raise VoicePracticeError("AI_UNAVAILABLE", "Voice AI sozlanmagan.", 503)
        # Klaviatura orqali yozilgan matn bo'lsa STT bosqichi kerak emas.
        # Dialog limiti, budget gate va javob oqimi ovoz bilan bir xil qoladi.
        typed_text = str(text or "").strip()[:MAX_TEXT_CHARS]
        if not typed_text:
            if not audio_bytes:
                raise VoicePracticeError("EMPTY_AUDIO", "Audio bo'sh.")
            if len(audio_bytes) > MAX_AUDIO_BYTES:
                raise VoicePracticeError("AUDIO_TOO_LARGE", "Audio hajmi juda katta.", 413)

        item = await self._get_active_session(telegram_id, session_id)
        if item.turn_count >= MAX_DIALOGS_PER_SESSION:
            raise VoicePracticeError("TURN_LIMIT_EXCEEDED", "Bu voice sessiya dialog limitiga yetdi.", 403)
        paid = await self._is_paid_telegram_user(telegram_id)
        if paid:
            await self._ensure_budget_available(telegram_id)

        transcribe_record = None
        reply_record = None
        try:
            if typed_text:
                transcription = typed_text
            else:
                ai = AIService()
                transcription_result = await asyncio.wait_for(
                    ai.transcribe_voice_with_usage(
                        audio_bytes=audio_bytes,
                        filename=filename,
                        user_language=item.language,
                        user_level=item.level,
                        gemini_model=GEMINI_FAST_MODEL,
                    ),
                    timeout=35,
                )
                transcription = transcription_result.content.strip()
                if not transcription:
                    raise VoicePracticeError("TRANSCRIPTION_EMPTY", "No speech was detected.")
                transcribe_record = await AIUsageBudgetService(self.session).record_usage(
                    telegram_id=telegram_id,
                    result=transcription_result,
                    source="voice_practice_transcribe",
                )
            reply, reply_usage = await asyncio.wait_for(self._generate_reply(item, transcription), timeout=30)
            reply_record = await AIUsageBudgetService(self.session).record_usage(
                telegram_id=telegram_id,
                result=reply_usage,
                source="voice_practice_reply",
            )
        except VoicePracticeError:
            raise
        except asyncio.TimeoutError as error:
            raise VoicePracticeError("AI_TIMEOUT", "Voice AI timed out. Try again.", 504) from error
        except Exception as error:
            logger.exception("Voice Practice AI failed for user %s", telegram_id)
            raise VoicePracticeError("AI_FAILED", "Voice AI failed. Try again.", 502) from error

        history = list(item.history or [])
        history.append(
            {
                "user": transcription,
                "assistant": reply["chinese_reply"],
                "pinyin": reply.get("pinyin") or "",
                "translation": reply.get("translation") or "",
                "correction": reply.get("correction") or None,
                "error_type": reply.get("error_type") or "none",
            }
        )
        item.history = history[-20:]
        if reply["correction"]:
            item.corrections = [*list(item.corrections or []), reply["correction"]][-20:]
        item.turn_count += 1
        session_should_end = item.turn_count >= MAX_DIALOGS_PER_SESSION
        await self.session.commit()

        status = await self.user_status(telegram_id)
        return {
            "transcription": transcription,
            **reply,
            "audio_reply_url": None,
            "audio_reply_base64": None,
            "remaining_limit": status["remaining_voice_limit"],
            "turn_count": item.turn_count,
            "max_dialogs": MAX_DIALOGS_PER_SESSION,
            "session_should_end": session_should_end,
            "budget_notice": self._budget_notice_payload(transcribe_record, reply_record),
        }

    @staticmethod
    def _cjk_chars(text: str) -> list[str]:
        return [c for c in str(text or "") if "一" <= c <= "鿿"]

    @staticmethod
    def _normalize_pinyin(text: str) -> str:
        raw = str(text or "").translate(PINYIN_UMLAUT_TRANSLATION).lower().replace("u:", "v")
        decomposed = unicodedata.normalize("NFKD", raw)
        without_marks = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
        return re.sub(r"[^a-z0-9]+", " ", without_marks).strip()

    @classmethod
    def _pinyin_score(cls, target_pinyin: str, heard: str) -> int:
        target = re.sub(r"[^a-z]+", "", cls._normalize_pinyin(target_pinyin))
        heard_norm = cls._normalize_pinyin(heard)
        heard_compact = re.sub(r"[^a-z]+", "", heard_norm)
        if not target or not heard_compact:
            return 0
        if target == heard_compact or target in heard_compact or heard_compact in target:
            shorter = min(len(target), len(heard_compact))
            longer = max(len(target), len(heard_compact))
            if longer and shorter / longer >= 0.72:
                return 100
        return int(round(difflib.SequenceMatcher(None, target, heard_compact).ratio() * 100))

    @classmethod
    def _pronunciation_score(cls, target: str, heard: str, target_pinyin: str = "") -> int:
        target_chars = cls._cjk_chars(target)
        hanzi_score = 0
        if target_chars:
            heard_counts = Counter(cls._cjk_chars(heard))
            matched = 0
            for ch in target_chars:
                if heard_counts.get(ch, 0) > 0:
                    heard_counts[ch] -= 1
                    matched += 1
            hanzi_score = int(round(matched / len(target_chars) * 100))
        return max(hanzi_score, cls._pinyin_score(target_pinyin, heard))

    async def score_pronunciation(
        self,
        telegram_id: int,
        *,
        target: str,
        target_pinyin: str = "",
        audio_bytes: bytes,
        filename: str,
        language: str,
        level: str,
    ) -> dict:
        if not settings.ai_enabled:
            raise VoicePracticeError("AI_UNAVAILABLE", "Voice AI sozlanmagan.", 503)
        if not self._cjk_chars(target):
            raise VoicePracticeError("INVALID_TARGET", "Talaffuz uchun so'z topilmadi.")
        if not audio_bytes:
            raise VoicePracticeError("EMPTY_AUDIO", "Audio bo'sh.")
        if len(audio_bytes) > MAX_AUDIO_BYTES:
            raise VoicePracticeError("AUDIO_TOO_LARGE", "Audio hajmi juda katta.", 413)

        paid = await self._is_paid_telegram_user(telegram_id)
        if paid:
            await self._ensure_budget_available(telegram_id)
        else:
            # Bepul user: AI chaqirishdan OLDIN kunlik kvotani tekshiramiz, aks holda
            # cheksiz OpenAI STT xarajati bo'ladi. Limit tugasa Premium-sheet chiqadi.
            used_today = await self._pronounce_count_today(telegram_id)
            if used_today >= FREE_PRONOUNCE_DAILY:
                raise VoicePracticeError(
                    "PRONOUNCE_LIMIT_EXCEEDED",
                    "Bugungi bepul talaffuz urinishlari tugadi.",
                    403,
                )

        record = None
        try:
            ai = AIService()
            transcription_result = await asyncio.wait_for(
                ai.transcribe_voice_with_usage(
                    audio_bytes=audio_bytes,
                    filename=filename,
                    user_language=(language or "ru"),
                    user_level=(level or "hsk1"),
                    speech_hint=f"{target} ({target_pinyin})" if target_pinyin else target,
                    gemini_model=GEMINI_FAST_MODEL,
                ),
                timeout=35,
            )
            record = await AIUsageBudgetService(self.session).record_usage(
                telegram_id=telegram_id,
                result=transcription_result,
                source="voice_practice_pronounce",
            )
            await self.session.commit()
        except VoicePracticeError:
            raise
        except asyncio.TimeoutError as error:
            raise VoicePracticeError("AI_TIMEOUT", "Voice AI timed out. Try again.", 504) from error
        except Exception as error:
            logger.exception("Pronunciation scoring failed for user %s", telegram_id)
            raise VoicePracticeError("AI_FAILED", "Voice AI failed. Try again.", 502) from error

        heard = (transcription_result.content or "").strip()
        score = self._pronunciation_score(target, heard, target_pinyin)
        passed = score >= PRONOUNCE_PASS_SCORE
        # Interval takrori: to'g'ri talaffuz so'zni siyraklashtiradi, xato
        # uni bugunga qaytaradi. Ball SERVERDA hisoblangani uchun bu yozuvga
        # ishonch bor va klientdan hech narsa so'ralmaydi.
        await self._record_pronunciation_mastery(telegram_id, target=target, correct=passed)
        if not passed:
            # Talaffuz mashqi ilgari serverda BAHOLANARDI, lekin natija hech
            # qayerga yozilmasdi: o'quvchi bir so'zni o'nlab marta noto'g'ri
            # aytsa ham "Xatolarim" bo'sh qolardi va reja uni ko'rmasdi.
            # Ball serverda hisoblangani uchun bu yozuvga ishonch bor —
            # mijozning so'ziga emas.
            await self._record_pronunciation_mistake(
                telegram_id,
                target=target,
                target_pinyin=target_pinyin,
                heard=heard,
                score=score,
                level=level,
            )
        return {
            "ok": True,
            "score": score,
            "passed": passed,
            "heard": heard,
            "target": target,
            "target_pinyin": target_pinyin,
            "budget_notice": self._budget_notice_payload(record),
        }

    async def _safe_rollback(self) -> None:
        """Tozalashning o'zi ham mashqni yiqitmasligi kerak.

        Signal yozuvlari "hech qachon yiqitmaydi" deb va'da qiladi, lekin
        `rollback` ning o'zi ham xato berishi mumkin (sessiya allaqachon
        yopilgan bo'lsa). U holda va'da buzilardi.
        """
        try:
            await self.session.rollback()
        except Exception:  # noqa: BLE001
            logger.exception("Rollback after a signal write failed")

    async def _record_pronunciation_mastery(
        self,
        telegram_id: int,
        *,
        target: str,
        correct: bool,
    ) -> None:
        """Talaffuz natijasini interval takroriga yozadi.

        `target` mijozdan keladi va gap ham bo'lishi mumkin (kurs ichidagi
        talaffuz kartasi butun iborani yuboradi). Mastery servisi kurs
        lug'atida yo'q narsani jimgina tashlaydi, shuning uchun bu yerda
        qo'shimcha tekshiruv kerak emas.
        """
        try:
            user = await self.user_repo.get_by_telegram_id(telegram_id)
            if not user:
                return
            await CourseWordMasteryService(self.session).record_drill(
                user,
                skill="pronunciation",
                results=[{"hanzi": target, "correct": bool(correct)}],
            )
            await self.session.commit()
        except Exception:  # noqa: BLE001 — jadval yozuvi mashqni yiqitmasin
            logger.exception("Pronunciation mastery write failed for user %s", telegram_id)
            await self._safe_rollback()

    async def _record_pronunciation_mistake(
        self,
        telegram_id: int,
        *,
        target: str,
        target_pinyin: str,
        heard: str,
        score: int,
        level: str,
    ) -> None:
        """Yiqilgan talaffuz urinishini Xatolarim bo'limiga yozadi.

        Baholash tugagach chaqiriladi va HECH QACHON mashqni yiqitmaydi:
        yozuv muvaffaqiyatsiz bo'lsa o'quvchi baribir o'z ballini ko'radi.
        """
        try:
            user = await self.user_repo.get_by_telegram_id(telegram_id)
            if not user:
                return
            prompt = f"{target} ({target_pinyin})".strip() if target_pinyin else target
            await CourseMistakeService(self.session).record_items(
                user,
                [
                    {
                        "question": prompt,
                        "selected_answer": heard or None,
                        "correct_answer": target,
                        "explanation": target_pinyin or None,
                        "category": "pronunciation",
                        "pinyin": target_pinyin,
                        "audio_text": target,
                    }
                ],
                source="pronunciation",
                level=(level or "").strip().lower() or None,
            )
            await self.session.commit()
        except Exception:  # noqa: BLE001 — signal yozuvi mashqni yiqitmasin
            logger.exception("Pronunciation mistake write failed for user %s", telegram_id)
            await self._safe_rollback()

    async def end_session(self, telegram_id: int, session_id: str) -> dict:
        item = await self._get_active_session(telegram_id, session_id)
        ended_at = datetime.now(timezone.utc)
        started_at = item.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        item.status = "completed"
        item.ended_at = ended_at

        # To'liq dialog transkripti: har bir navbat uchun user jumlasi, AI javobi,
        # pinyin/tarjima va xato bo'lgan-bo'lmagani. Frontend "zo'r gapirgan joylar"ni
        # (xato=null) yashil, xatolarni qizil qilib ko'rsatadi.
        transcript: list[dict] = []
        good_count = 0
        mistake_count = 0
        errors_by_type = {key: 0 for key in sorted(VOICE_ERROR_TYPES)}
        for entry in list(item.history or []):
            if not isinstance(entry, dict):
                continue
            user_text = str(entry.get("user") or "").strip()
            if not user_text:
                continue
            correction = str(entry.get("correction") or "").strip() or None
            if correction:
                mistake_count += 1
            else:
                good_count += 1
            entry_type = str(entry.get("error_type") or "").strip().lower()
            if correction and entry_type in VOICE_ERROR_TYPES:
                errors_by_type[entry_type] += 1
            transcript.append(
                {
                    "user": user_text,
                    "assistant": str(entry.get("assistant") or "").strip(),
                    "pinyin": str(entry.get("pinyin") or "").strip(),
                    "translation": str(entry.get("translation") or "").strip(),
                    "correction": correction,
                    "error_type": entry_type if correction else "none",
                    "good": correction is None,
                }
            )

        user = await self.user_repo.get_by_telegram_id(telegram_id)
        # Gapirilmagan sessiya (`turn_count == 0`) uchun XP/streak berilmaydi:
        # `award` faqat `activity_ref` bo'yicha dedupe qiladi, ya'ni ochib-yopish
        # 10 XP + streak + kunlik rejaning `voice_dialog` vazifasini bergan
        # bo'lardi. Limit endi gapirilgandan keyin yonadi, shuning uchun bu
        # himoya bo'lmasa ferma bepul o'quvchilarga ham ochilardi.
        if user and int(item.turn_count or 0) > 0:
            # Xatolarim bo'limi uchun: userning aynan noto'g'ri jumlasini savol,
            # to'g'ri variantni javob qilib yozamiz (avvalgidek savol=tuzatish emas).
            mistake_items = []
            for entry in list(item.history or []):
                if not isinstance(entry, dict):
                    continue
                correction = str(entry.get("correction") or "").strip()
                if not correction:
                    continue
                user_text = str(entry.get("user") or "").strip()
                mistake_item = {
                    "question": user_text or correction,
                    "selected_answer": user_text or None,
                    "correct_answer": correction,
                    "explanation": correction,
                }
                # Xato turini AI bergan bo'lsa — o'shani uzatamiz. Bermagan
                # bo'lsa (o'zgarishdan OLDIN boshlangan sessiyalar) `category`
                # kaliti umuman qo'yilmaydi va CourseMistakeService._category
                # ning `source == "voice"` fallback'i eski xatti-harakatni
                # saqlaydi. `language` ATAYLAB berilmaydi — voice jumlalari
                # word_choice distraktor havzasiga aralashmasligi kerak.
                entry_type = str(entry.get("error_type") or "").strip().lower()
                if entry_type in VOICE_ERROR_TYPES:
                    mistake_item["category"] = entry_type
                mistake_items.append(mistake_item)
            await CourseMistakeService(self.session).record_items(
                user,
                mistake_items,
                source="voice",
                level=item.level,
                lesson_id=item.lesson_id,
            )
            reward = await CourseGamificationService(self.session).award(
                user,
                activity_type="voice",
                activity_ref=f"voice:{item.id}",
                base_xp=10,
                level=item.level,
            )
        else:
            reward = None
        await self.session.commit()
        return {
            "ok": True,
            "duration_seconds": max(0, int((ended_at - started_at).total_seconds())),
            "message_count": item.turn_count,
            "corrections": list(item.corrections or []),
            "transcript": transcript,
            "good_count": good_count,
            "mistake_count": mistake_count,
            "errors_by_type": errors_by_type,
            "reward": reward,
            **self._session_metrics(item, transcript),
        }

    @staticmethod
    def _session_metrics(item: VoicePracticeSession, transcript: list[dict]) -> dict:
        """Suhbat o'lchovlari — QO'SHIMCHA AI chaqiruvisiz.

        Bularning hammasi saqlangan tarixdan arifmetika bilan chiqadi. LLM
        xulosasi qo'shilmadi: `end_session` hozir ~50 ms da qaytadi va natija
        kartasi faqat shundan keyin chiziladi; modelga chiqish uni 1.5-5 s ga
        cho'zib, AI xatosida o'quvchini XP dan ham, transkriptdan ham
        ayirardi.

        DIQQAT: bu yerda AKUSTIK yoki TON tahlili YO'Q va bo'lishi ham mumkin
        emas — STT matni bilan ishlaymiz. Shuning uchun natijalar "ball" emas,
        SANOQ sifatida ko'rsatilishi kerak.
        """
        said = [str(row.get("user") or "") for row in transcript]
        joined = "".join(said)
        pool: list[str] = []
        seen: set[str] = set()
        for word in [*list(item.target_words or []), *list(item.review_words or [])]:
            zh = str((word or {}).get("zh") or "").strip() if isinstance(word, dict) else ""
            if zh and zh not in seen:
                seen.add(zh)
                pool.append(zh)
        used = [zh for zh in pool if zh in joined]
        lengths = [len(VoicePracticeService._cjk_chars(text)) for text in said if text]
        turns = int(item.turn_count or 0)
        return {
            "target_used": {"used": len(used), "total": len(pool), "words": used[:12]},
            "avg_chars": round(sum(lengths) / len(lengths), 1) if lengths else 0.0,
            "turns": turns,
            "completed": turns >= MAX_DIALOGS_PER_SESSION,
        }
