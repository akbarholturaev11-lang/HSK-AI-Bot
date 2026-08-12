"""The STT prompt must never reach the tutor as if the learner had said it.

Both transcription providers hand the prompt back when the audio is short or
unclear. That echo used to be scored as real speech ("no mistakes"), quoted
back by the roleplay partner, and — because the echo is English and contains
"do not translate" — it flipped the translation field out of the learner's
language. The fixtures below are the two real transcripts that exposed it.
"""

import unittest

from app.services.ai_service import AIService, _strip_prompt_echo

PROMPT = (
    "Transcribe only, do not translate. "
    "Likely Tajik or Chinese, level hsk4. "
    "Keep Chinese, pinyin, names, numbers, and short mixed-language phrases."
)

ECHO = (
    "context: ### Transcribe only, do not translate. Likely Tajik or Chinese, "
    "level hsk4. Keep Chinese, pinyin, names, numbers, and short "
    "mixed-language phrases. ###"
)


class StripPromptEchoTests(unittest.TestCase):
    def test_keeps_speech_when_the_echo_trails_it(self):
        text = _strip_prompt_echo(f"不是不是,我说的是 老西 {ECHO}", PROMPT)
        self.assertEqual(text, "不是不是,我说的是 老西")

    def test_keeps_speech_when_the_echo_leads(self):
        text = _strip_prompt_echo(f"{ECHO} 你听错了,我说是 俄语", PROMPT)
        self.assertEqual(text, "你听错了,我说是 俄语")

    def test_pure_echo_becomes_empty_so_callers_report_no_speech(self):
        self.assertEqual(_strip_prompt_echo(ECHO, PROMPT), "")

    def test_bare_echo_without_the_provider_marker(self):
        text = _strip_prompt_echo(f"{PROMPT} 我说是 俄语", PROMPT)
        self.assertEqual(text, "我说是 俄语")

    def test_speech_hint_suffix_is_stripped_too(self):
        prompt = (
            f"{PROMPT} Pronunciation target hint: 你好 (nǐ hǎo). "
            "Use the hint only to resolve unclear Chinese sounds; do not copy "
            "it if it was not spoken."
        )
        self.assertEqual(_strip_prompt_echo(f"你好 {prompt}", prompt), "你好")

    def test_ordinary_speech_is_untouched(self):
        for spoken in (
            "我说的是俄语。",
            "Ман бо забони тоҷикӣ гап мезанам.",
            "老师，我不明白 context 这个词。",
        ):
            with self.subTest(spoken=spoken):
                self.assertEqual(_strip_prompt_echo(spoken, PROMPT), spoken)

    def test_empty_input_is_safe(self):
        self.assertEqual(_strip_prompt_echo("", PROMPT), "")
        self.assertEqual(_strip_prompt_echo("你好", ""), "你好")


class TranscribeVoiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_transcribe_voice_returns_cleaned_text(self):
        service = AIService.__new__(AIService)

        async def fake_transcribe(**kwargs):
            return f"{ECHO} 我说是 俄语", {"total_tokens": 3}, "stub-model"

        class _Chain:
            transcribe = staticmethod(fake_transcribe)

        service.chain = _Chain()
        result = await service.transcribe_voice_with_usage(
            audio_bytes=b"",
            filename="clip.m4a",
            user_language="tj",
            user_level="hsk4",
        )
        self.assertEqual(result.content, "我说是 俄语")


if __name__ == "__main__":
    unittest.main()
