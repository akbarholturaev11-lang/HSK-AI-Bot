import json
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from app.db.models.course_challenge import CourseChallenge
from app.services.course_challenge_service import (
    CHALLENGE_QUESTION_COUNT,
    CHALLENGE_TIE_XP,
    CHALLENGE_WIN_XP,
    CourseChallengeService,
)


def challenge_questions(count: int) -> list[dict]:
    return [
        {
            "id": f"q{index}",
            "prompt": "Ma'nosini tanlang",
            "options": ["salom", "xayr"],
            "option_materials": [{"id": "answer-a"}, {"id": "answer-b"}],
            "answer_index": 0,
            "explanation": "你好 = salom",
        }
        for index in range(1, count + 1)
    ]


class CourseChallengeServiceTests(unittest.TestCase):
    def test_winner_by_percent(self):
        # Players answer different sets at their own level, so the winner is
        # decided by percentage even when raw scores differ in the other way.
        challenge = CourseChallenge(
            challenger_user_id=1,
            opponent_user_id=2,
            question_payload="[]",
            challenger_score=8,
            challenger_total=10,
            challenger_percent=80,
            opponent_score=9,
            opponent_total=15,
            opponent_percent=60,
        )
        CourseChallengeService._update_winner(challenge)
        self.assertEqual(challenge.status, "completed")
        self.assertEqual(challenge.winner_user_id, 1)

    def test_equal_percent_is_tie_even_when_client_durations_differ(self):
        challenge = CourseChallenge(
            challenger_user_id=1,
            opponent_user_id=2,
            question_payload="[]",
            challenger_score=7,
            challenger_percent=70,
            opponent_score=7,
            opponent_percent=70,
            challenger_duration_seconds=120,
            opponent_duration_seconds=90,
        )
        CourseChallengeService._update_winner(challenge)
        self.assertEqual(challenge.status, "completed")
        self.assertIsNone(challenge.winner_user_id)

    def test_legacy_winner_falls_back_to_score_without_percent(self):
        challenge = CourseChallenge(
            challenger_user_id=1,
            opponent_user_id=2,
            question_payload="[]",
            challenger_score=8,
            opponent_score=6,
        )
        CourseChallengeService._update_winner(challenge)
        self.assertEqual(challenge.status, "completed")
        self.assertEqual(challenge.winner_user_id, 1)

    def test_no_winner_before_both_complete(self):
        challenge = CourseChallenge(
            challenger_user_id=1,
            opponent_user_id=2,
            question_payload="[]",
            challenger_score=7,
        )
        CourseChallengeService._update_winner(challenge)
        self.assertIsNone(challenge.winner_user_id)

    def test_payload_map_ignores_non_list_role_values(self):
        challenge = CourseChallenge(
            challenger_user_id=1,
            opponent_user_id=2,
            question_payload='{"challenger":"bad","opponent":[{"id":"q1"}]}',
        )
        self.assertEqual(CourseChallengeService._questions(challenge, "challenger"), [])
        self.assertEqual(CourseChallengeService._questions(challenge, "opponent"), [{"id": "q1"}])

    def test_invite_copy_matches_server_tie_rule_in_every_language(self):
        challenge = CourseChallenge(level="hsk1")
        challenger = SimpleNamespace(full_name="Akbar", username="")
        expected = {
            "uz": ("Foiz teng bo'lsa — durrang", "tezroq"),
            "ru": ("При равном проценте — ничья", "скорость"),
            "tj": ("Агар фоиз баробар бошад — мусовӣ", "тезтараш"),
        }

        for lang, (tie_copy, stale_speed_copy) in expected.items():
            with self.subTest(lang=lang):
                text = CourseChallengeService.invite_text(challenge, challenger, lang)
                self.assertIn(tie_copy, text)
                self.assertNotIn(stale_speed_copy, text)


class CourseChallengeRewardTests(unittest.IsolatedAsyncioTestCase):
    async def test_pending_challenge_cannot_be_started_by_either_player(self):
        service = CourseChallengeService(SimpleNamespace())
        challenge = CourseChallenge(
            id=7,
            challenger_user_id=1,
            opponent_user_id=2,
            status="pending",
            level="hsk1",
            lang="uz",
            question_payload='{"challenger":[{"id":"q1"}],"opponent":[]}',
        )
        service._ensure_questions = AsyncMock()

        for user_id in (1, 2):
            with self.subTest(user_id=user_id):
                user = SimpleNamespace(id=user_id, level="hsk1", language="uz")
                service.get_for_user = AsyncMock(return_value=(user, challenge))

                result = await service.start(1000 + user_id, 7)

                self.assertEqual(result, {"ok": False, "error": "challenge_pending"})
                self.assertEqual(challenge.status, "pending")
        service._ensure_questions.assert_not_awaited()

    async def test_start_returns_public_questions_without_mutating_frozen_payload(self):
        service = CourseChallengeService(SimpleNamespace())
        frozen = {
            "challenger": challenge_questions(CHALLENGE_QUESTION_COUNT),
            "opponent": [],
        }
        stored_payload = json.dumps(frozen, ensure_ascii=False)
        challenge = CourseChallenge(
            id=8,
            challenger_user_id=1,
            opponent_user_id=2,
            status="accepted",
            level="hsk1",
            lang="uz",
            question_payload=stored_payload,
        )
        user = SimpleNamespace(id=1, level="hsk1", language="uz")
        service.get_for_user = AsyncMock(return_value=(user, challenge))

        result = await service.start(1001, 8)

        self.assertTrue(result["ok"])
        public_questions = result["session"]["questions"]
        self.assertEqual(len(public_questions), CHALLENGE_QUESTION_COUNT)
        public_question = public_questions[0]
        self.assertNotIn("answer_index", public_question)
        self.assertNotIn("explanation", public_question)
        self.assertNotIn("option_materials", public_question)
        self.assertEqual(public_question["options"], ["salom", "xayr"])
        self.assertIsNotNone(datetime.fromisoformat(result["session"]["started_at"]).tzinfo)
        self.assertEqual(challenge.question_payload, stored_payload)

    async def test_start_rejects_stored_round_without_exact_question_count(self):
        service = CourseChallengeService(SimpleNamespace())
        challenge = CourseChallenge(
            id=8,
            challenger_user_id=1,
            opponent_user_id=2,
            status="accepted",
            level="hsk1",
            lang="uz",
            question_payload=json.dumps(
                {"challenger": challenge_questions(CHALLENGE_QUESTION_COUNT - 1), "opponent": []}
            ),
        )
        user = SimpleNamespace(id=1, level="hsk1", language="uz")
        service.get_for_user = AsyncMock(return_value=(user, challenge))

        result = await service.start(1001, 8)

        self.assertEqual(result, {"ok": False, "error": "practice_questions_not_found"})

    async def test_accept_does_not_open_duel_when_opponent_questions_missing(self):
        session = SimpleNamespace(flush=AsyncMock())
        service = CourseChallengeService(session)
        user = SimpleNamespace(id=2, level="hsk2", language="uz")
        challenge = CourseChallenge(
            id=7,
            challenger_user_id=1,
            opponent_user_id=2,
            status="pending",
            level="hsk1",
            lang="uz",
            question_payload='{"challenger":[{"id":"q1"}],"opponent":[]}',
        )
        service.get_for_user = AsyncMock(return_value=(user, challenge))
        service._generate_questions_for = AsyncMock(return_value=[])

        result = await service.respond(2002, 7, "accept")

        self.assertEqual(result, {"ok": False, "error": "practice_questions_not_found"})
        self.assertEqual(challenge.status, "pending")

    async def test_accept_does_not_open_duel_with_partial_question_set(self):
        session = SimpleNamespace(flush=AsyncMock())
        service = CourseChallengeService(session)
        user = SimpleNamespace(id=2, level="hsk2", language="uz")
        challenge = CourseChallenge(
            id=7,
            challenger_user_id=1,
            opponent_user_id=2,
            status="pending",
            level="hsk1",
            lang="uz",
            question_payload=json.dumps(
                {"challenger": challenge_questions(CHALLENGE_QUESTION_COUNT), "opponent": []}
            ),
        )
        service.get_for_user = AsyncMock(return_value=(user, challenge))
        service._generate_questions_for = AsyncMock(
            return_value=challenge_questions(CHALLENGE_QUESTION_COUNT - 1)
        )

        result = await service.respond(2002, 7, "accept")

        self.assertEqual(result, {"ok": False, "error": "practice_questions_not_found"})
        self.assertEqual(challenge.status, "pending")

    async def test_create_rejects_partial_challenger_question_set(self):
        session = SimpleNamespace(add=Mock(), flush=AsyncMock())
        service = CourseChallengeService(session)
        challenger = SimpleNamespace(
            id=1,
            telegram_id=1001,
            level="hsk1",
            language="uz",
        )
        opponent = SimpleNamespace(id=2, telegram_id=1002)
        service.user_repo = SimpleNamespace(
            get_by_telegram_id=AsyncMock(side_effect=[challenger, opponent])
        )
        service._generate_questions_for = AsyncMock(
            return_value=challenge_questions(CHALLENGE_QUESTION_COUNT - 1)
        )

        result = await service.create(
            1001,
            opponent_telegram_id=1002,
            level="hsk1",
            lang="uz",
        )

        self.assertEqual(result, {"ok": False, "error": "practice_questions_not_found"})
        session.add.assert_not_called()

    async def test_generator_rejects_question_bank_smaller_than_round_contract(self):
        session = SimpleNamespace()
        service = CourseChallengeService(session)
        user = SimpleNamespace(id=1, level="hsk1", language="uz")
        practice = SimpleNamespace(
            _questions=AsyncMock(
                return_value=challenge_questions(CHALLENGE_QUESTION_COUNT - 1)
            )
        )
        progress_repo = SimpleNamespace(get_by_user_id=AsyncMock(return_value=None))

        with patch(
            "app.services.course_challenge_service.CourseMiniAppPracticeService",
            return_value=practice,
        ), patch(
            "app.services.course_challenge_service.CourseProgressRepository",
            return_value=progress_repo,
        ):
            result = await service._generate_questions_for(user)

        self.assertEqual(result, [])

    async def test_completed_winner_gets_bonus_xp(self):
        service = CourseChallengeService(SimpleNamespace())
        service.gamification = SimpleNamespace(award=AsyncMock(return_value={"awarded_xp": CHALLENGE_WIN_XP, "xp": 100}))
        winner = SimpleNamespace(id=2, level="hsk3")
        challenge = CourseChallenge(
            id=42,
            challenger_user_id=1,
            opponent_user_id=2,
            winner_user_id=2,
            status="completed",
            level="hsk1",
            question_payload="[]",
        )

        rewards = await service._award_final_rewards(challenge, {1: SimpleNamespace(id=1), 2: winner})

        self.assertEqual(rewards[2]["awarded_xp"], CHALLENGE_WIN_XP)
        service.gamification.award.assert_awaited_once_with(
            winner,
            activity_type="challenge_win",
            activity_ref="challenge:42:winner",
            base_xp=CHALLENGE_WIN_XP,
            level="hsk3",
        )

    async def test_submit_records_rich_mistake_and_uses_player_level_for_xp(self):
        session = SimpleNamespace(flush=AsyncMock())
        service = CourseChallengeService(session)
        challenger = SimpleNamespace(
            id=1,
            telegram_id=1001,
            level="hsk1",
            language="uz",
            full_name="Challenger",
            username="challenger",
        )
        opponent = SimpleNamespace(
            id=2,
            telegram_id=1002,
            level="hsk3",
            language="tj",
            full_name="Opponent",
            username="opponent",
        )
        question = {
            "id": "hsk3:2:1",
            "lesson": 2,
            "type": "fill_blank_choice",
            "subtype": "hanzi_to_meaning",
            "prompt": "Gapni to'ldiring",
            "sentence": "我____学习。",
            "audio_text": "我在学习。",
            "pinyin": "wǒ zài xuéxí",
            "format": "listening_choice",
            "category": "grammar",
            "options": ["不", "在"],
            "answer_index": 1,
            "explanation": "我在学习。",
        }
        challenge = CourseChallenge(
            id=91,
            challenger_user_id=1,
            opponent_user_id=2,
            status="accepted",
            level="hsk1",
            lang="uz",
            question_payload=json.dumps({"challenger": [], "opponent": [question]}, ensure_ascii=False),
        )
        service.get_for_user = AsyncMock(return_value=(opponent, challenge))
        service._users_by_id = AsyncMock(return_value={1: challenger, 2: opponent})
        service.mistakes = SimpleNamespace(record_items=AsyncMock(return_value=1))
        service.gamification = SimpleNamespace(
            award=AsyncMock(return_value={"awarded_xp": 6, "xp": 50})
        )

        result = await service.submit(
            1002,
            91,
            [{"question_id": "hsk3:2:1", "selected_index": 0}],
            duration_seconds=1,
        )

        self.assertTrue(result["ok"])
        mistake_user, mistakes = service.mistakes.record_items.await_args.args
        self.assertIs(mistake_user, opponent)
        self.assertEqual(service.mistakes.record_items.await_args.kwargs, {"source": "challenge", "level": "hsk3"})
        self.assertEqual(
            mistakes[0],
            {
                "question_id": "hsk3:2:1",
                "question": "Gapni to'ldiring\n我____学习。",
                "selected_answer": "不",
                "correct_answer": "在",
                "explanation": "我在学习。",
                "level": "hsk3",
                "lesson": 2,
                "type": "fill_blank_choice",
                "subtype": "hanzi_to_meaning",
                "format": "listening_choice",
                "category": "grammar",
                "sentence": "我____学习。",
                "audio_text": "我在学习。",
                "pinyin": "wǒ zài xuéxí",
                "language": "tj",
                "options": ["不", "在"],
                "source": {"material_ref": "hsk3:2:1"},
            },
        )
        service.gamification.award.assert_awaited_once_with(
            opponent,
            activity_type="challenge",
            activity_ref="challenge:91:user:2:completed",
            base_xp=6,
            level="hsk3",
        )
        self.assertEqual(result["challenge"]["viewer_level"], "hsk3")
        self.assertEqual(result["challenge"]["other_level"], "hsk1")

    async def test_exact_tie_rewards_both_players(self):
        service = CourseChallengeService(SimpleNamespace())
        service.gamification = SimpleNamespace(award=AsyncMock(return_value={"awarded_xp": CHALLENGE_TIE_XP, "xp": 100}))
        first = SimpleNamespace(id=1)
        second = SimpleNamespace(id=2)
        challenge = CourseChallenge(
            id=43,
            challenger_user_id=1,
            opponent_user_id=2,
            winner_user_id=None,
            status="completed",
            level="hsk2",
            question_payload="[]",
        )

        rewards = await service._award_final_rewards(challenge, {1: first, 2: second})

        self.assertEqual(set(rewards), {1, 2})
        self.assertEqual(service.gamification.award.await_count, 2)


if __name__ == "__main__":
    unittest.main()
