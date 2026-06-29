import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.db.models.course_challenge import CourseChallenge
from app.services.course_challenge_service import CHALLENGE_TIE_XP, CHALLENGE_WIN_XP, CourseChallengeService


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

    def test_winner_by_duration_on_tie(self):
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
        self.assertEqual(challenge.winner_user_id, 2)

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


class CourseChallengeRewardTests(unittest.IsolatedAsyncioTestCase):
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

    async def test_completed_winner_gets_bonus_xp(self):
        service = CourseChallengeService(SimpleNamespace())
        service.gamification = SimpleNamespace(award=AsyncMock(return_value={"awarded_xp": CHALLENGE_WIN_XP, "xp": 100}))
        winner = SimpleNamespace(id=2)
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
            level="hsk1",
        )

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
