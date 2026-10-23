"""Regression guards for the verified Mini App lesson rank-up celebration."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8")
COURSE = (ROOT / "app/static/course-v3.html").read_text(encoding="utf-8")


class MiniAppLessonRankUpTests(unittest.TestCase):
    def test_completion_returns_verified_rank_snapshots(self):
        handler = MAIN.split('@app.post("/api/v3/lesson/complete")', 1)[1].split(
            "def _voice_practice_user_id", 1
        )[0]
        self.assertIn("rank_before = int((await gamification.leaderboard(user))", handler)
        self.assertIn("updated_rating = await gamification.leaderboard(user)", handler)
        self.assertIn('rank_after = int(updated_rating.get("rank") or 0)', handler)
        self.assertIn('"rank_before": rank_before', handler)
        self.assertIn('"rank_after": rank_after', handler)

    def test_rank_up_is_triggered_before_end_of_lesson_ad(self):
        closure = COURSE.split("  closeLevelUp:function(dest){", 1)[1].split(
            "  /* Sovg'a sandig'i:", 1
        )[0]
        self.assertIn("if(!dest&&pendingRankUp){App.showRankUp();return}", closure)
        self.assertLess(closure.index("App.showRankUp();return"), closure.index("playLessonEndAd(go)"))

    def test_only_server_verified_real_promotion_is_queued(self):
        self.assertIn("var rankBefore=Number(d&&d.rank_before)||0;", COURSE)
        self.assertIn("rankAfter>0&&rankAfter<rankBefore", COURSE)
        self.assertIn("!d.duplicate", COURSE)
        self.assertNotIn("var rankBefore=currentRatingRank();", COURSE)

    def test_checkpoint_celebration_returns_to_original_checkout_flow(self):
        self.assertIn('if(pendingRankUp){App.showRankUp("checkpoint_next");return}', COURSE)
        self.assertIn(
            'returnDest==="checkpoint_next"?"App.openCheckpointNext()"',
            COURSE,
        )
        self.assertIn("if(App.showSalesBridge())return;", COURSE)

    def test_rank_up_is_immediate_not_blocked_by_leaderboard_refresh(self):
        handler = COURSE.split("  showRankUp:function(returnDest){", 1)[1].split(
            "  renderRankUpBoard:function", 1
        )[0]
        self.assertIn("App.renderRankUpBoard(ranks,returnDest);", handler)
        self.assertIn("loadLatestRating().catch(function(){});", handler)
        self.assertLess(handler.index("App.renderRankUpBoard"), handler.index("loadLatestRating"))
        self.assertIn('$("#lu-cta").disabled=true;', handler)
        self.assertIn('$("#lu-cta").disabled=false;', COURSE)

    def test_completion_includes_immediate_rank_neighbours(self):
        handler = MAIN.split('@app.post("/api/v3/lesson/complete")', 1)[1].split(
            "def _voice_practice_user_id", 1
        )[0]
        self.assertIn('"rank_up_board": rank_up_board', handler)
        self.assertIn("if 0 < rank_after < rank_before:", handler)
        self.assertIn("leaderboard[max(0, me_idx - 1):me_idx + 2]", handler)
        self.assertIn("logging.exception", handler)

    def test_rank_board_fallback_uses_server_position(self):
        self.assertIn("board:d.rank_up_board||[]", COURSE)
        self.assertIn("rk:ranks.after", COURSE)
        self.assertIn("cached.rank===ranks.after", COURSE)


if __name__ == "__main__":
    unittest.main()
