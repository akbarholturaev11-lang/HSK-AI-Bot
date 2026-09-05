"""Kunlik reja — sof funksiya: signallar + ruxsat -> 1-4 ta vazifa.

Reja DB da SAQLANMAYDI degan qoida emas: task IDENTITY'si kuniga bir marta
quriladi va `course_miniapp_profiles.daily_plan_json` da muzlatiladi, holati
(bajarildi/ochiq) esa har so'rovda qayta hisoblanadi. Sabab: `course_mistakes`
upsert jadvali — zaiflikning kun boshidagi holatini qayta tiklab bo'lmaydi,
shuning uchun sof qayta hisoblash rejani kun davomida o'zgartirib yuborardi.

Bu modulda I/O yo'q — hammasi kirish argumentlaridan. Shu sababli u DB'siz
test qilinadi va Mini App, Android hamda Desktop uchun bir xil natija beradi.
"""

from __future__ import annotations

import hashlib

from app.services.learning_signals import LearningSignals


PLAN_SCHEMA_VERSION = 1

TASK_CONTINUE_LESSON = "continue_lesson"
TASK_MISTAKE_REVIEW = "mistake_review"
TASK_SKILL_DRILL = "skill_drill"
TASK_MOCK_EXAM = "mock_exam"
TASK_VOICE_DIALOG = "voice_dialog"
TASK_TYPES = (
    TASK_CONTINUE_LESSON,
    TASK_MISTAKE_REVIEW,
    TASK_SKILL_DRILL,
    TASK_MOCK_EXAM,
    TASK_VOICE_DIALOG,
)

# Har vazifa qaysi kirish kaliti bilan ochiladi.
TASK_FEATURE = {
    TASK_CONTINUE_LESSON: "lesson",
    TASK_MISTAKE_REVIEW: "mistake_review",
    TASK_SKILL_DRILL: "training_test",
    TASK_MOCK_EXAM: "training_test",
    TASK_VOICE_DIALOG: "voice",
}

# Bajarilganlikni `course_xp_events.activity_type` bo'yicha aniqlaymiz.
TASK_ACTIVITY_TYPE = {
    TASK_MISTAKE_REVIEW: "mistake_review",
    TASK_SKILL_DRILL: "training",
    TASK_MOCK_EXAM: "test",
    TASK_VOICE_DIALOG: "voice",
}

# Zaiflik -> mashq skili. GRAMMATIKA ataylab yo'q: savol banki uni qoplay
# olmaydi (o'lchandi — 30-qismda ham atigi 4/10 savol grammatika), shuning
# uchun grammatika zaifligi `mistake_review` orqali hal qilinadi — u
# o'quvchining O'Z grammatik xatolaridan quriladi.
SKILL_FOR_WEAKNESS = {
    "listening": "listening",
    "character": "characters",
    "word": "characters",
    "pronunciation": "pronunciation",
}

# Skill qaysi qismdan boshlab ishonchli (savol banki uni to'ldira oladi).
# 2026-09-05 da HSK1 bo'yicha o'lchangan mos savollar ulushi:
#   qism  listening  characters  pronunciation
#     1      1/8        6/8          2/8
#     3      4/10      10/10         5/10
#     5      4/10      10/10        10/10
#     8     10/10      10/10        10/10
# Chegaradan oldin skill va'da qilinmaydi — aks holda "tinglash mashqi" deb
# ochilgan mashqda tinglash savoli deyarli bo'lmasdi.
SKILL_MIN_PART = {"listening": 8, "characters": 3, "pronunciation": 5}

# Skill klientda ochiladigan EKRANI borsagina taklif qilinadi. Bugun Mini
# App'da ikkita mashq ekrani bor: "Ieroglif tanish" (characters) va
# "Talaffuz mashqi" (pronunciation). TINGLASH uchun ekran YO'Q — server
# savol bera oladi, lekin ochadigan joy yo'q, shuning uchun u rejaga
# tushmaydi (qat'iy qoida: hozir boshlab bo'lmaydigan vazifa berilmaydi).
# Umumiy drill ekrani qo'shilganda bu ro'yxat kengayadi.
SKILL_WITH_CLIENT_SCREEN = frozenset({"characters", "pronunciation"})

# Aytilgan fokus qaysi zaiflikka ishora qiladi (prior).
FOCUS_TO_WEAKNESS = {
    "listening": "listening",
    "vocabulary": "character",
    "grammar": "grammar",
    "speaking": "pronunciation",
}
# Speaking fokusi drill emas, JONLI SUHBATni ham ko'taradi.
FOCUS_TASK_BOOST = {"speaking": {TASK_VOICE_DIALOG: 1.2}}

# Maqsad vazifa TURLARINING vaznini o'zgartiradi. Qiymatlar mavjud
# imkoniyatlar doirasida: repoda bo'lmagan kontent va'da qilinmaydi.
GOAL_WEIGHTS = {
    "hsk_exam": {
        TASK_MOCK_EXAM: 3.0, TASK_MISTAKE_REVIEW: 2.2,
        TASK_SKILL_DRILL: 1.2, TASK_VOICE_DIALOG: 0.3,
    },
    "daily_communication": {
        TASK_VOICE_DIALOG: 3.0, TASK_SKILL_DRILL: 1.6,
        TASK_MISTAKE_REVIEW: 1.2, TASK_MOCK_EXAM: 0.3,
    },
    "travel": {
        TASK_VOICE_DIALOG: 2.6, TASK_SKILL_DRILL: 1.6,
        TASK_MISTAKE_REVIEW: 1.1, TASK_MOCK_EXAM: 0.3,
    },
    "work_china": {
        TASK_VOICE_DIALOG: 2.3, TASK_SKILL_DRILL: 1.3,
        TASK_MISTAKE_REVIEW: 1.2, TASK_MOCK_EXAM: 0.4,
    },
    "study_china": {
        TASK_SKILL_DRILL: 1.8, TASK_MISTAKE_REVIEW: 1.4,
        TASK_VOICE_DIALOG: 1.2, TASK_MOCK_EXAM: 0.6,
    },
}
DEFAULT_GOAL = "hsk_exam"

# Mini App'da hozir ATIGI ikkita persona ochiq (course-v3.html: PERS).
# Qolgan 8 rol serverda bor, lekin ularni ko'rsatish UI o'zgarishi bo'lgani
# uchun alohida ruxsat talab qiladi.
VOICE_ROLE_FOR_GOAL = {"hsk_exam": "teacher_li"}
DEFAULT_VOICE_ROLE = "friend"

# Zaiflik xom son (0..N); maqsad vaznlari 0..3. Bir tarozida solishtirish
# uchun zaiflik 0..1 ga keltirilib shu koeffitsientga ko'paytiriladi.
WEAKNESS_WEIGHT = 2.0
# Aytilgan fokusning boshlang'ich ustunligi (dalil to'planganda so'nadi).
PRIOR_WEIGHT = 1.5

ACCESS_OPEN = "open"
ACCESS_AD = "ad"
ACCESS_LOCKED = "locked"
# Reklama bilan ochiladigan vazifa BERILADI (Qaror B): reklamali tasklar
# soniga chegara qo'yilmagan.
ISSUABLE_ACCESS = (ACCESS_OPEN, ACCESS_AD)


def plan_key(*, level: str, local_day: str) -> str:
    """Muzlatilgan reja kaliti: sxema versiyasi + band + mahalliy sana."""
    return f"v{PLAN_SCHEMA_VERSION}:{str(level or '').strip().lower()}:{local_day}"


class DailyPlanService:
    @staticmethod
    def _goal_weights(goal: str) -> dict[str, float]:
        return GOAL_WEIGHTS.get(str(goal or "").strip().lower(), GOAL_WEIGHTS[DEFAULT_GOAL])

    @staticmethod
    def _tie_break(seed: str, task_type: str) -> float:
        """Bir xil ballda tartib tasodifiy emas, DETERMINISTIK bo'lsin.

        Seed kun va foydalanuvchidan quriladi, ya'ni kun davomida o'zgarmaydi
        va boshqa qurilmada ham ayni natijani beradi.
        """
        digest = hashlib.sha256(f"{seed}|{task_type}".encode("utf-8")).digest()
        return digest[0] / 2550.0

    @classmethod
    def _weakness_scores(cls, signals: LearningSignals) -> dict[str, float]:
        """Zaiflik + aytilgan fokus (so'nuvchi prior) -> 0..N ball."""
        raw = dict(signals.weakness or {})
        peak = max(raw.values()) if raw and max(raw.values()) > 0 else 0
        prior_key = FOCUS_TO_WEAKNESS.get(signals.preferred_focus or "")
        prior_weight = signals.prior_weight
        scores: dict[str, float] = {}
        for key, value in raw.items():
            observed = (value / peak) if peak else 0.0
            prior = PRIOR_WEIGHT * prior_weight if key == prior_key else 0.0
            scores[key] = WEAKNESS_WEIGHT * observed + prior
        return scores

    @classmethod
    def _best_skill(cls, signals: LearningSignals) -> tuple[str | None, float]:
        """Eng zaif o'lchov uchun mashq skili — bank uni qoplay olsagina."""
        scores = cls._weakness_scores(signals)
        best_skill, best_score = None, 0.0
        for weakness_key, skill in SKILL_FOR_WEAKNESS.items():
            if skill not in SKILL_WITH_CLIENT_SCREEN:
                continue
            if signals.current_part < SKILL_MIN_PART.get(skill, 1):
                continue
            score = scores.get(weakness_key, 0.0)
            if score > best_score:
                best_skill, best_score = skill, score
        return best_skill, best_score

    @classmethod
    def build(
        cls,
        signals: LearningSignals,
        *,
        access: dict[str, str] | None = None,
        seed: str = "",
    ) -> list[dict]:
        """Bugungi vazifalar (faqat IDENTITY). Sof funksiya."""
        access = access or {}
        weights = cls._goal_weights(signals.goal)
        focus_boost = FOCUS_TASK_BOOST.get(signals.preferred_focus or "", {})

        def issuable(task_type: str) -> bool:
            return access.get(TASK_FEATURE[task_type], ACCESS_OPEN) in ISSUABLE_ACCESS

        tasks: list[dict] = []
        # Kurs — asosiy mahsulot, shuning uchun davom etish doim birinchi.
        if signals.has_next_part and issuable(TASK_CONTINUE_LESSON):
            tasks.append(
                {"t": TASK_CONTINUE_LESSON, "ref": f"{signals.level}:{signals.current_part}"}
            )

        candidates: list[tuple[float, str, dict]] = []
        if signals.mistakes_total > 0 and issuable(TASK_MISTAKE_REVIEW):
            # Grammatika zaifligining yagona chorasi shu — unga mos drill yo'q.
            grammar = cls._weakness_scores(signals).get("grammar", 0.0)
            score = weights.get(TASK_MISTAKE_REVIEW, 1.0) + grammar
            candidates.append((score, TASK_MISTAKE_REVIEW, {"t": TASK_MISTAKE_REVIEW}))

        skill, skill_score = cls._best_skill(signals)
        if skill and issuable(TASK_SKILL_DRILL):
            score = weights.get(TASK_SKILL_DRILL, 1.0) + skill_score
            candidates.append((score, TASK_SKILL_DRILL, {"t": TASK_SKILL_DRILL, "skill": skill}))

        if issuable(TASK_MOCK_EXAM):
            candidates.append(
                (weights.get(TASK_MOCK_EXAM, 0.3), TASK_MOCK_EXAM, {"t": TASK_MOCK_EXAM})
            )

        if issuable(TASK_VOICE_DIALOG):
            role = VOICE_ROLE_FOR_GOAL.get(
                str(signals.goal or "").strip().lower(), DEFAULT_VOICE_ROLE
            )
            score = weights.get(TASK_VOICE_DIALOG, 1.0) + focus_boost.get(TASK_VOICE_DIALOG, 0.0)
            candidates.append(
                (score, TASK_VOICE_DIALOG, {"t": TASK_VOICE_DIALOG, "role": role})
            )

        candidates.sort(key=lambda item: (-(item[0] + cls._tie_break(seed, item[1])), item[1]))
        for _, _, task in candidates:
            if len(tasks) >= signals.plan_size:
                break
            tasks.append(task)
        return tasks[: signals.plan_size]

    @staticmethod
    def _is_done(task: dict, signals: LearningSignals) -> bool:
        task_type = str(task.get("t") or "")
        if task_type == TASK_CONTINUE_LESSON:
            ref = str(task.get("ref") or "")
            _, _, part = ref.partition(":")
            try:
                part_no = int(part)
            except ValueError:
                return False
            return part_no <= signals.completed_parts
        activity_type = TASK_ACTIVITY_TYPE.get(task_type)
        return bool(activity_type and activity_type in signals.done_types_today)

    @classmethod
    def hydrate(
        cls,
        tasks: list[dict],
        signals: LearningSignals,
        *,
        access: dict[str, str] | None = None,
    ) -> dict:
        """Muzlatilgan identity + har so'rovda qayta hisoblanadigan holat.

        Kun ichida qulflanib qolgan vazifa ro'yxatda QOLADI va almashtirilmaydi
        (Q-B qoidasi): almashtirish rejani beqaror qilardi.
        """
        access = access or {}
        items = []
        for task in tasks or []:
            task_type = str(task.get("t") or "")
            if task_type not in TASK_TYPES:
                continue
            state = access.get(TASK_FEATURE[task_type], ACCESS_OPEN)
            items.append(
                {
                    "type": task_type,
                    "ref": task.get("ref"),
                    "skill": task.get("skill"),
                    "role": task.get("role"),
                    "done": cls._is_done(task, signals),
                    "access": state,
                    "available": state in ISSUABLE_ACCESS,
                }
            )
        done = sum(1 for item in items if item["done"])
        return {
            "goal_xp": signals.daily_goal_xp,
            "done_xp": signals.today_xp,
            "streak": signals.streak,
            "total": len(items),
            "done": done,
            "complete": bool(items) and done == len(items),
            "tasks": items,
        }
