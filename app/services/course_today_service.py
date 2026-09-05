"""«Bugungi reja» — signal, ruxsat va muzlatilgan rejani birlashtiruvchi qatlam.

Bu yerda I/O bor (shuning uchun `DailyPlanService` sof bo'lib qoladi) va
aynan uchta ish qilinadi:

1. `LearningSignalsService` orqali signallarni o'qish;
2. ruxsat ko'rinishini MAVJUD gating servislaridan yig'ish — bu yerda hech
   qanday yangi limit qoidasi YOZILMAYDI, aks holda "Known Problem 3"
   (bir xil bo'limga ikki xil qoida) takrorlanardi;
3. kunlik rejani kaliti bo'yicha olish yoki bir marta qurib muzlatish.

Natija `/api/v3/map` va native klientlarning map javobiga bir xil shaklda
qo'shiladi, ya'ni Android va Desktop uni kod o'zgartirmasdan oladi.
"""

from __future__ import annotations

import json
import logging

from app.services.course_access_policy_service import (
    COURSE_ACCESS_AD,
    COURSE_ACCESS_OPEN,
)
from app.services.course_miniapp_access_service import (
    CourseMiniAppAccessService,
    free_course_parts_for_level,
)
from app.services.daily_plan_service import (
    ACCESS_AD,
    ACCESS_LOCKED,
    ACCESS_OPEN,
    DailyPlanService,
    plan_key,
)
from app.services.learning_signals import LearningSignalsService
from app.services.voice_practice_service import VoicePracticeService


logger = logging.getLogger(__name__)

# Test markazi va mashq drilllari ayni bepul slotni bo'lishadi
# (`CourseHskExamService.HSK_EXAM_ACCESS_FEATURE == "training_test"`).
PRACTICE_FEATURE = "training_test"


class CourseTodayService:
    def __init__(self, session):
        self.session = session
        self.access = CourseMiniAppAccessService(session)
        self.signals = LearningSignalsService(session)

    async def _access_view(self, user, *, level, current_part, is_paid, access_policy) -> dict:
        """Har vazifa hozir ochiqmi: open / ad / locked.

        Qiymatlar MAVJUD servislardan o'qiladi — bu yerda yangi qoida yo'q.
        """
        view = {}

        # Dars: admin siyosati (obuna / reklama / vaqtincha bepul).
        requirement = access_policy.requirement_for(
            lesson_order=current_part,
            is_paid=is_paid,
            free_lessons=free_course_parts_for_level(level),
        )
        view["lesson"] = {
            COURSE_ACCESS_OPEN: ACCESS_OPEN,
            COURSE_ACCESS_AD: ACCESS_AD,
        }.get(requirement, ACCESS_LOCKED)

        if is_paid or access_policy.free_active:
            view[PRACTICE_FEATURE] = ACCESS_OPEN
            view["mistake_review"] = ACCESS_OPEN
        else:
            # Test markazi / drill: bepul slot `daily_status`da, tugagach
            # reklama bilan davom — bu bo'limda reklama CHEKSIZ (AI emas).
            status = await self.access.daily_status(user, PRACTICE_FEATURE, lifetime=True)
            view[PRACTICE_FEATURE] = ACCESS_OPEN if status.get("allowed") else ACCESS_AD
            # Xatolar bo'limi ayni `training_test` slotini ishlatadi, lekin
            # boshqa hisoblagichda (`CourseFeatureUsage`).
            entitlements = await self.access.get_entitlements(user)
            allowed = bool((entitlements.get(PRACTICE_FEATURE) or {}).get("allowed"))
            view["mistake_review"] = ACCESS_OPEN if allowed else ACCESS_AD

        # Voice: reklama yo'li YO'Q — bepul limit tugasa faqat obuna.
        try:
            remaining = await VoicePracticeService(self.session).remaining_free_sessions(user)
        except Exception:  # noqa: BLE001 — reja voice tufayli yiqilmasin
            logger.exception("Voice access probe failed for user %s", getattr(user, "id", None))
            remaining = 0
        view["voice"] = ACCESS_OPEN if (remaining is None or remaining > 0) else ACCESS_LOCKED
        return view

    @staticmethod
    def _stored_tasks(profile, key: str) -> list[dict] | None:
        if str(getattr(profile, "daily_plan_key", "") or "") != key:
            return None
        raw = getattr(profile, "daily_plan_json", None)
        if not raw:
            return None
        try:
            tasks = json.loads(raw)
        except (TypeError, ValueError):
            return None
        return tasks if isinstance(tasks, list) else None

    async def payload(
        self,
        user,
        *,
        profile,
        progress,
        level: str,
        is_paid: bool,
        access_policy,
    ) -> dict | None:
        """Map javobiga qo'shiladigan `today` bloki. Xato bo'lsa None."""
        try:
            signals = await self.signals.load(
                user, profile=profile, progress=progress, level=level
            )
            access = await self._access_view(
                user,
                level=level,
                current_part=signals.current_part,
                is_paid=is_paid,
                access_policy=access_policy,
            )
            key = plan_key(level=level, local_day=signals.local_day)
            tasks = self._stored_tasks(profile, key)
            if tasks is None:
                # Kuniga ATIGI bir marta: shundan keyin task identity'si
                # muzlaydi va kun davomida o'zgarmaydi.
                seed = f"{getattr(user, 'id', 0)}|{signals.local_day}"
                tasks = DailyPlanService.build(signals, access=access, seed=seed)
                profile.daily_plan_key = key
                profile.daily_plan_json = json.dumps(tasks, ensure_ascii=False)
            view = DailyPlanService.hydrate(tasks, signals, access=access)
            view["level"] = level
            view["local_day"] = signals.local_day
            return view
        except Exception:  # noqa: BLE001 — reja map javobini yiqitmasin
            logger.exception("Daily plan build failed for user %s", getattr(user, "id", None))
            return None
