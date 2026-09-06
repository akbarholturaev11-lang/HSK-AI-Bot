"""AI Voice va talaffuz mashqida transkripsiya FAQAT xitoychani kutadi.

Muammo: prompt "Likely {ona tili} or Chinese" derdi, shuning uchun model
o'quvchining xitoycha nutqini kirill harflarga o'girib yozardi — masalan
"huǒguō" -> "Хуагу". Shundan keyin AI javobi ham, tuzatish ham mutlaqo boshqa
narsa haqida chiqardi va o'quvchiga "bot meni tushunmadi" bo'lib ko'rinardi.

Botdagi umumiy ovozli savol-javob yo'li BUNDAN MUSTASNO: u yerda o'quvchi
o'z ona tilida gapiradi.
"""

import unittest
from unittest.mock import AsyncMock, patch

from app.services.ai_service import AIService


async def _prompt_for(**kwargs) -> str:
    chain = AsyncMock(return_value=("你好", {}, "gemini"))
    service = AIService()
    with patch.object(service.chain, "transcribe", chain):
        await service.transcribe_voice_with_usage(
            audio_bytes=b"x",
            filename="voice.mp4",
            user_language="tj",
            user_level="hsk1",
            **kwargs,
        )
    return chain.await_args.kwargs["prompt"]


class TranscriptionLanguageTests(unittest.IsolatedAsyncioTestCase):
    async def test_voice_practice_asks_for_hanzi_and_forbids_transliteration(self):
        prompt = await _prompt_for(expect_chinese=True)
        self.assertIn("Hanzi", prompt)
        self.assertIn("NEVER transliterate", prompt)
        # Ona tili endi ehtimoliy variant sifatida taklif qilinmaydi.
        self.assertNotIn("Tajik", prompt)

    async def test_the_bot_qa_path_still_expects_the_learners_own_language(self):
        prompt = await _prompt_for()
        self.assertIn("Tajik", prompt)
        self.assertNotIn("NEVER transliterate", prompt)

    async def test_the_pronunciation_hint_still_reaches_the_chinese_prompt(self):
        prompt = await _prompt_for(expect_chinese=True, speech_hint="火锅 (huǒguō)")
        self.assertIn("火锅", prompt)
        self.assertIn("do not copy it if it was not spoken", prompt)
