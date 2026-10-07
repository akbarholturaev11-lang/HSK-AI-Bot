from types import SimpleNamespace
import unittest

from app.api.android_live_voice import _append_transcript, _usage_result
from app.services.android_live_voice_service import live_voice_available


class AndroidLiveVoiceGateTests(unittest.TestCase):
    def _settings(self, **overrides):
        values = {
            "ANDROID_VOICE_LIVE_ENABLED": True,
            "ANDROID_VOICE_LIVE_ALLOWED_USERS": "4242, 9001",
            "ANDROID_VOICE_LIVE_MODEL": "gemini-3.8-live",
            "ANDROID_VOICE_LIVE_SESSION_BUDGET_USD": 0.15,
            "GEMINI_API_KEY": "configured-for-test",
            "GEMINI_BILLING_TIER": "paid",
        }
        values.update(overrides)
        return SimpleNamespace(**values)

    def test_live_requires_explicit_paid_allowlist_or_global_rollout_and_budget(self):
        self.assertTrue(live_voice_available(self._settings(), 4242))
        self.assertFalse(live_voice_available(self._settings(), 7))
        self.assertTrue(
            live_voice_available(self._settings(ANDROID_VOICE_LIVE_ALLOWED_USERS="*"), 7)
        )
        self.assertFalse(
            live_voice_available(self._settings(ANDROID_VOICE_LIVE_ENABLED=False), 4242)
        )
        self.assertFalse(
            live_voice_available(self._settings(GEMINI_BILLING_TIER="free"), 4242)
        )
        self.assertFalse(
            live_voice_available(self._settings(ANDROID_VOICE_LIVE_SESSION_BUDGET_USD=0), 4242)
        )

    def test_malformed_allowlist_or_budget_fails_closed(self):
        self.assertFalse(
            live_voice_available(self._settings(ANDROID_VOICE_LIVE_ALLOWED_USERS="4242,nope"), 4242)
        )
        self.assertFalse(
            live_voice_available(self._settings(ANDROID_VOICE_LIVE_ALLOWED_USERS="*,4242"), 4242)
        )
        self.assertFalse(
            live_voice_available(self._settings(ANDROID_VOICE_LIVE_SESSION_BUDGET_USD="invalid"), 4242)
        )

    def test_transcript_chunks_are_appended_without_repeating_overlap(self):
        self.assertEqual("你好世界", _append_transcript("你好", "好世界"))
        self.assertEqual("你好世界", _append_transcript("你好", "你好世界"))

    def test_provider_usage_requires_real_token_counts(self):
        usage = SimpleNamespace(
            prompt_token_count=125,
            response_token_count=75,
            total_token_count=200,
        )
        result = _usage_result(usage, "gemini-3.8-live")
        self.assertIsNotNone(result)
        self.assertEqual((125, 75, 200), (result.prompt_tokens, result.completion_tokens, result.total_tokens))
        self.assertIsNone(_usage_result(SimpleNamespace(), "gemini-3.8-live"))


if __name__ == "__main__":
    unittest.main()
