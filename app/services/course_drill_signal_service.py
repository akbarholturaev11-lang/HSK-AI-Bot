"""Mijoz boshqaradigan mashqlarning natijasini SERVER TEKSHIRUVI bilan yozish.

Mini App'ning "Ieroglif tanish" va "Yodlash" bo'limlari savollarni o'zi
quradi (`hsk-words.js`, `memo.js`) va o'zining ekran dizayniga ega. Ularni
umumiy MCQ dvigateliga o'tkazish ekranni butunlay almashtirishni talab
qilardi, shuning uchun ular o'z oqimida qoladi.

Lekin natijasi yo'qolmasligi kerak: aks holda `character` zaifligi faqat
darslardan to'planadi va kunlik reja o'quvchining ieroglif muammosini
ko'rmaydi.

Yechim — darslar uchun allaqachon ishlatiladigan qoida bilan bir xil
(`CourseLessonMistakeMaterialService`): mijoz XATO BO'LGAN ELEMENTNI aytadi,
server esa uni O'ZINING lug'atidan (`course_v3_vocab`) qayta quradi. Mijoz
savol matnini ham, to'g'ri javobni ham yubormaydi va soxta xato yoza olmaydi:
serverda topilmagan ieroglif jimgina tashlab yuboriladi.
"""

from __future__ import annotations

import logging

from app.services.course_mistake_service import CourseMistakeService
from app.services.course_v3_vocab import words_for_level


logger = logging.getLogger(__name__)

DRILL_FEATURES = {"recognition", "memorize"}
DRILL_LEVELS = ("hsk1", "hsk2", "hsk3", "hsk4")
DRILL_LANGUAGES = {"uz", "ru", "tj"}
# Bitta sessiyadan yoziladigan xatolar chegarasi. Mashqda 10 savol bor,
# zaxira bilan olamiz; ortiqchasi tashlanadi.
MAX_DRILL_MISTAKES = 20


class CourseDrillSignalService:
    def __init__(self, session):
        self.session = session

    @staticmethod
    def _level(value: str) -> str:
        level = str(value or "").strip().lower()
        if level.startswith("hsk4"):
            return "hsk4"
        return level if level in DRILL_LEVELS else "hsk1"

    @classmethod
    def _vocabulary(cls, level: str) -> dict[str, dict]:
        """Shu daraja va undan quyi darajalardagi barcha so'zlar.

        Mashq quyi darajalardagi so'zlarni ham beradi, shuning uchun tekshiruv
        faqat joriy daraja bilan cheklanmaydi — aks holda haqiqiy xatolar
        "topilmadi" deb tashlanardi.
        """
        level = cls._level(level)
        index: dict[str, dict] = {}
        for item_level in DRILL_LEVELS:
            for word in words_for_level(item_level):
                zh = str(word.get("zh") or "").strip()
                if zh and zh not in index:
                    index[zh] = word
            if item_level == level:
                break
        return index

    @staticmethod
    def _meaning(word: dict, language: str) -> str:
        meaning = word.get("meaning")
        if isinstance(meaning, dict):
            return str(meaning.get(language) or meaning.get("ru") or meaning.get("uz") or "").strip()
        return str(meaning or "").strip()

    @classmethod
    def build_items(cls, *, level: str, language: str, entries: list) -> list[dict]:
        """Mijoz aytgan ieroglifllarni server lug'atidan qayta quradi.

        Serverda topilmagan yoki takrorlangan yozuvlar tashlanadi.
        """
        language = str(language or "").strip().lower()
        if language not in DRILL_LANGUAGES:
            language = "ru"
        vocabulary = cls._vocabulary(level)
        items: list[dict] = []
        seen: set[str] = set()
        for entry in entries[:MAX_DRILL_MISTAKES]:
            if not isinstance(entry, dict):
                continue
            zh = str(entry.get("hanzi") or "").strip()
            if not zh or zh in seen:
                continue
            word = vocabulary.get(zh)
            if not word:
                # Mijoz o'ylab topgan yoki kurs lug'atidan tashqaridagi belgi.
                continue
            seen.add(zh)
            pinyin = str(word.get("pinyin") or "").strip()
            meaning = cls._meaning(word, language)
            # Savol MIJOZDAN emas, server lug'atidan quriladi.
            prompt = " · ".join(part for part in (pinyin, meaning) if part) or zh
            selected = str(entry.get("selected") or "").strip()[:64]
            items.append(
                {
                    "question": prompt,
                    "selected_answer": selected or None,
                    "correct_answer": zh,
                    "explanation": meaning or None,
                    "category": "character",
                    "pinyin": pinyin,
                    "language": language,
                }
            )
        return items

    async def record(
        self,
        user,
        *,
        feature: str,
        level: str,
        language: str,
        entries: list,
    ) -> int:
        """Yozilgan xatolar sonini qaytaradi. Yozuv mashqni hech qachon yiqitmaydi."""
        feature = str(feature or "").strip().lower()
        if feature not in DRILL_FEATURES:
            raise ValueError("Unknown drill feature")
        if not user:
            return 0
        items = self.build_items(level=level, language=language, entries=entries or [])
        if not items:
            return 0
        try:
            await CourseMistakeService(self.session).record_items(
                user,
                items,
                source=feature,
                level=self._level(level),
            )
        except Exception:  # noqa: BLE001 — signal yozuvi mashqni yiqitmasin
            logger.exception("Drill mistake write failed for user %s", getattr(user, "id", None))
            return 0
        return len(items)
