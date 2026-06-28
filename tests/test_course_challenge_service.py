import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.db.models.course_challenge import CourseChallenge
from app.services.course_challenge_service import CHALLENGE_TIE_XP, CHALLENGE_WIN_XP, CourseChallengeService


class CourseChallengeServiceTests(unittest.TestCase):
    def test_winner_by_score(self):
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

    def test_winner_by_duration_on_tie(self):
        challenge = CourseChallenge(
            challenger_user_id=1,
            opponent_user_id=2,
            question_payload="[]",
            challenger_score=7,
            opponent_score=7,
            challenger_duration_seconds=120,
            opponent_duration_seconds=90,
        )
        CourseChallengeService._update_winner(challenge)
        self.assertEqual(challenge.status, "completed")
        self.assertEqual(challenge.winner_user_id, 2)

    def test_no_winner_before_both_complete(self):
        challenge = CourseChallenge(
            challenger_user_id=1,
            opponent_user_id=2,
            question_payload="[]",
            challenger_score=7,
        )
        CourseChallengeService._update_winner(challenge)
        self.assertIsNone(challenge.winner_user_id)


class CourseChallengeRewardTests(unittest.IsolatedAsyncioTestCase):
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
