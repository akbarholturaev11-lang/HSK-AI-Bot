import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services.course_miniapp_practice_service import CourseMiniAppPracticeService


def question(question_id, level="hsk1", answer=0):
    return {
        "id": question_id,
        "level": level,
        "lesson": 1,
        "type": "multiple_choice",
        "subtype": "hanzi_to_meaning",
        "prompt": "Question",
        "sentence": "",
        "audio_text": "",
        "pinyin": "",
        "format": "meaning_choice",
        "category": "word",
        "options": ["Correct", "Wrong"],
        "answer_index": answer,
        "explanation": "Explanation",
    }


class CourseMiniAppPracticeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.session = SimpleNamespace(commit=AsyncMock())
        self.service = CourseMiniAppPracticeService(self.session)
        self.user = SimpleNamespace(
            id=5,
            telegram_id=123,
            status="trial",
            payment_status="none",
            end_date=None,
        )
        self.service.user_repo = SimpleNamespace(get_by_telegram_id=AsyncMock(return_value=self.user))
        self.service.access = SimpleNamespace(
            consume_daily_use=AsyncMock(return_value={"allowed": True}),
            verify_ad_authorization=AsyncMock(return_value={"allowed": True}),
        )
        self.service._questions = AsyncMock(return_value=[question("q1")])
        self.service.mistakes = SimpleNamespace(record_items=AsyncMock(return_value=0))
        self.service.gamification = SimpleNamespace(
            award=AsyncMock(return_value={"xp": 20, "awarded_xp": 20, "streak": 1, "league": "Bronze"})
        )

    async def test_an_ad_opens_the_session_without_spending_the_daily_slot(self):
        # A learner who watched an ad must keep their free daily attempt: the
        # ad is the alternative to spending it, not a way to spend it twice.
        analytics = SimpleNamespace(record_server_event=AsyncMock(return_value={"ok": True}))
        with patch(
            "app.services.course_miniapp_practice_service.CourseMiniAppAnalyticsService",
            return_value=analytics,
        ):
            result = await self.service.start(
                123,
                mode="mock",
                level="hsk2",
                lang="ru",
                access_ref="a" * 24,
                ad_supported=True,
            )

        self.assertTrue(result["ok"])
        self.service.access.consume_daily_use.assert_not_awaited()
        self.service.access.verify_ad_authorization.assert_awaited_once_with(
            self.user,
            feature_key="training_test",
            access_ref="a" * 24,
        )

    async def test_an_unwatched_ad_opens_nothing(self):
        # `ad_supported` is only a request. The server checks its own record of
        # the watch, so setting the flag by hand must not open anything.
        self.service.access.verify_ad_authorization = AsyncMock(
            return_value={"allowed": False, "error": "ad_authorization_required"}
        )
        result = await self.service.start(
            123,
            mode="mock",
            level="hsk2",
            lang="ru",
            access_ref="a" * 24,
            ad_supported=True,
        )

        self.assertFalse(result["ok"])
        self.assertEqual("ad_authorization_required", result["error"])
        self.service.access.consume_daily_use.assert_not_awaited()

    async def test_a_malformed_access_ref_is_refused_not_raised(self):
        # A bad ref must come back as an ordinary refusal; letting ValueError
        # escape would surface as a 500 to the learner.
        self.service.access.verify_ad_authorization = AsyncMock(
            side_effect=ValueError("invalid_access_ref")
        )
        result = await self.service.start(
            123,
            mode="mock",
            level="hsk2",
            lang="ru",
            access_ref="!!",
            ad_supported=True,
        )

        self.assertFalse(result["ok"])
        self.assertEqual("invalid_access_ref", result["error"])

    async def test_finishing_an_ad_opened_session_does_not_hit_the_daily_limit(self):
        # Completing used to re-check the daily slot. For a session opened by
        # an ad that answered "limit reached", and the learner lost the result
        # of a practice they had already finished.
        analytics = SimpleNamespace(record_server_event=AsyncMock(return_value={"ok": True}))
        with patch(
            "app.services.course_miniapp_practice_service.CourseMiniAppAnalyticsService",
            return_value=analytics,
        ):
            started = await self.service.start(
                123,
                mode="mock",
                level="hsk2",
                lang="ru",
                access_ref="a" * 24,
                ad_supported=True,
            )
            result = await self.service.complete(
                123,
                session_id=started["session"]["id"],
                mode="mock",
                level="hsk2",
                lang="ru",
                skill="",
                answers=[{"question_id": "q1", "selected_index": 0}],
                access_ref="a" * 24,
                ad_supported=True,
            )

        self.assertTrue(result["ok"], result)
        self.service.access.consume_daily_use.assert_not_awaited()

    async def test_mock_start_consumes_shared_training_test_entitlement(self):
        analytics = SimpleNamespace(record_server_event=AsyncMock(return_value={"ok": True}))
        with patch(
            "app.services.course_miniapp_practice_service.CourseMiniAppAnalyticsService",
            return_value=analytics,
        ):
            result = await self.service.start(
                123,
                mode="mock",
                level="hsk2",
                lang="ru",
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["session"]["mode"], "mock")
        self.service.access.consume_daily_use.assert_awaited_once_with(
            self.user,
            feature_key="training_test",
            ref="mock:hsk2",
            notify_bot=None,
        )

    async def test_daily_feature_limit_blocks_new_session(self):
        self.service.access.consume_daily_use = AsyncMock(
            return_value={"allowed": False, "error": "free_feature_limit_reached"}
        )
        result = await self.service.start(
            123,
            mode="training",
            level="hsk1",
            lang="ru",
            skill="listening",
        )
        # Exact shape on purpose: a denial must not leak anything beyond the
        # error and what the client needs to say when it reopens.
        self.assertEqual(
            result,
            {
                "ok": False,
                "error": "free_feature_limit_reached",
                "reset_at": None,
                "lifetime": False,
            },
        )
        self.service.access.consume_daily_use.assert_awaited_once_with(
            self.user,
            feature_key="training_test",
            ref="training:listening",
            notify_bot=None,
        )

    async def test_v3_pinyin_training_skill_is_supported(self):
        analytics = SimpleNamespace(record_server_event=AsyncMock(return_value={"ok": True}))
        with patch(
            "app.services.course_miniapp_practice_service.CourseMiniAppAnalyticsService",
            return_value=analytics,
        ):
            result = await self.service.start(
                123,
                mode="training",
                level="hsk1",
                lang="ru",
                skill="pinyin",
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["session"]["skill"], "pinyin")

    async def test_start_falls_back_to_static_v3_cards_when_db_lessons_are_missing(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            level_dir = root / "hsk1"
            level_dir.mkdir(parents=True)
            (level_dir / "lesson_01.json").write_text(
                """
                {
                  "level": "hsk1",
                  "lesson_id": 1,
                  "sections": [
                    {
                      "section_no": 1,
                      "cards": [
                        {
                          "type": "pinyin_choice",
                          "prompt": {"uz": "ni pinyin qaysi?", "ru": "ni pinyin?", "tj": "ni pinyin?"},
                          "options": ["ni", "wo", "hao"],
                          "correct_index": 0,
                          "pinyin": "ni",
                          "explanation": {"uz": "ni", "ru": "ni", "tj": "ni"}
                        },
                        {
                          "type": "meaning_guess",
                          "prompt": {"uz": "hao meaning?", "ru": "hao meaning?", "tj": "hao meaning?"},
                          "options": [{"uz": "good", "ru": "good", "tj": "good"}, {"uz": "me", "ru": "me", "tj": "me"}],
                          "correct_index": 0,
                          "explanation": {"uz": "hao = good", "ru": "hao = good", "tj": "hao = good"}
                        }
                      ]
                    }
                  ]
                }
                """,
                encoding="utf-8",
            )
            self.service.lesson_repo = SimpleNamespace(
                list_by_level=AsyncMock(return_value=[]),
            )
            delattr(self.service, "_questions")
            analytics = SimpleNamespace(record_server_event=AsyncMock(return_value={"ok": True}))
            with (
                patch(
                    "app.services.course_miniapp_practice_service.COURSE_V3_DATA_ROOT",
                    root,
                ),
                patch(
                    "app.services.course_miniapp_practice_service.CourseMiniAppAnalyticsService",
                    return_value=analytics,
                ),
            ):
                result = await self.service.start(
                    123,
                    mode="training",
                    level="hsk1",
                    lang="ru",
                    skill="pinyin",
                )

        self.assertTrue(result["ok"])
        questions = result["session"]["questions"]
        self.assertGreaterEqual(len(questions), 1)
        self.assertEqual(questions[0]["source"]["kind"], "course_v3_static_card")
        self.assertIn("ni", questions[0]["options"])
        self.service.lesson_repo.list_by_level.assert_awaited_once_with("hsk1")

    async def test_completion_is_server_graded_and_preserves_payment(self):
        self.service._questions = AsyncMock(
            return_value=[question("q1", "hsk1", 0), question("q2", "hsk2", 1)]
        )
        analytics = SimpleNamespace(record_server_event=AsyncMock(return_value={"ok": True}))
        with patch(
            "app.services.course_miniapp_practice_service.CourseMiniAppAnalyticsService",
            return_value=analytics,
        ):
            result = await self.service.complete(
                123,
                session_id="practice:5:placement:placement:hsk1:v1",
                mode="placement",
                level="hsk1",
                lang="ru",
                skill="",
                answers=[
                    {"question_id": "q1", "selected_index": 0, "percent": 100},
                    {"question_id": "q2", "selected_index": 0, "percent": 100},
                ],
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["percent"], 50)
        self.assertEqual(result["recommendation"], "HSK 1")
        self.assertEqual(self.user.payment_status, "none")
        self.service.access.consume_daily_use.assert_awaited_once_with(
            self.user,
            feature_key="placement",
            ref="placement:hsk1",
            notify_bot=None,
        )
        analytics.record_server_event.assert_awaited_once()
        self.service.mistakes.record_items.assert_awaited_once()
        mistake_items = self.service.mistakes.record_items.await_args.args[1]
        self.assertEqual(mistake_items[0]["format"], "meaning_choice")
        self.assertEqual(mistake_items[0]["language"], "ru")
        self.assertEqual(mistake_items[0]["options"], ["Correct", "Wrong"])
        self.assertEqual(mistake_items[0]["source"]["material_ref"], "q2")
        self.service.gamification.award.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
