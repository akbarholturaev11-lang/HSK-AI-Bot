"""Pure, offline tests for server-issued Mini App lesson completion proofs."""

import unittest

from app.services.course_lesson_completion_proof import (
    PROOF_FUTURE_SKEW_SECONDS,
    PROOF_TTL_SECONDS,
    issue_lesson_completion_proof,
    verify_lesson_completion_proof,
)

SECRET = "fake-telegram-bot-token-only-for-unit-tests"


class LessonCompletionProofTests(unittest.TestCase):
    def _issue(self, *, now=1000):
        return issue_lesson_completion_proof(
            user_id=42, level="nhsk2", lesson_order=7, secret=SECRET, now=now,
        )

    def _verify(self, token, *, now=1000, **kwargs):
        values = {"user_id": 42, "level": "nhsk2", "lesson_order": 7, "secret": SECRET}
        values.update(kwargs)
        return verify_lesson_completion_proof(token, now=now, **values)

    def test_valid_bound_proof_and_24_hour_expiry(self):
        token = self._issue()
        self.assertTrue(self._verify(token))
        self.assertTrue(self._verify(token, now=1000 + PROOF_TTL_SECONDS))
        self.assertFalse(self._verify(token, now=1001 + PROOF_TTL_SECONDS))
        self.assertTrue(self._verify(token, now=1000 - PROOF_FUTURE_SKEW_SECONDS))
        self.assertFalse(self._verify(token, now=999 - PROOF_FUTURE_SKEW_SECONDS))

    def test_cannot_reuse_other_account_course_lesson_or_secret(self):
        token = self._issue()
        self.assertFalse(self._verify(token, user_id=43))
        self.assertFalse(self._verify(token, level="nhsk1"))
        self.assertFalse(self._verify(token, lesson_order=8))
        self.assertFalse(self._verify(token, secret="wrong-secret"))

    def test_payload_and_signature_tampering_are_rejected(self):
        token = self._issue()
        payload, signature = token.split(".")
        changed = ("A" if payload[0] != "A" else "B") + payload[1:]
        self.assertFalse(self._verify(changed + "." + signature))
        changed_sig = ("A" if signature[0] != "A" else "B") + signature[1:]
        self.assertFalse(self._verify(payload + "." + changed_sig))
        for invalid in ("", "a", "x.y.z", "not-base64.x", 123, None, "x" * 513):
            with self.subTest(invalid=invalid):
                self.assertFalse(self._verify(invalid))

    def test_independent_starts_get_distinct_proofs(self):
        a, b = self._issue(), self._issue()
        self.assertNotEqual(a, b)
        self.assertTrue(self._verify(a))
        self.assertTrue(self._verify(b))


if __name__ == "__main__":
    unittest.main()
