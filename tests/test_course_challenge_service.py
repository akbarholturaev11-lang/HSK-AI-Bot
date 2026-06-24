import unittest

from app.db.models.course_challenge import CourseChallenge
from app.services.course_challenge_service import CourseChallengeService


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


if __name__ == "__main__":
    unittest.main()
