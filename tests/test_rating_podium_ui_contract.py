"""Source-level safeguards for the ranking podium. These do not replace mobile UI tests."""
import unittest
from pathlib import Path

WEB = Path("app/static/course-v3.html").read_text(encoding="utf-8")
CSS = Path("app/static/course_v3_data/rating-podium.css").read_text(encoding="utf-8")
ANDROID = Path("android/app/src/main/java/com/pomp/hskai/feature/rating/RatingScreen.kt").read_text(encoding="utf-8")
PODIUM = Path("android/app/src/main/java/com/pomp/hskai/feature/rating/RatingPodium.kt").read_text(encoding="utf-8")
MAIN = Path("android/app/src/main/java/com/pomp/hskai/MainActivity.kt").read_text(encoding="utf-8")
SERVICE = Path("app/services/course_gamification_service.py").read_text(encoding="utf-8")


class RatingPodiumUiTests(unittest.TestCase):
    def test_web_renders_one_server_member_count_in_centre_only(self):
        self.assertIn("rating-podium.css?v=20261014-1", WEB)
        self.assertIn("function ratingPodiumHtml(memberCount)", WEB)
        self.assertIn("league:String(d.league||\"\")", WEB)
        body = WEB.split("function ratingPodiumHtml(memberCount){", 1)[1].split(
            "function _renderRatingContent()", 1
        )[0]
        self.assertIn("item(index,\"gold\",true)", body)
        self.assertIn("item(sideIndices[0],\"silver\",false)", body)
        self.assertIn("item(sideIndices[1],\"bronze\",false)", body)
        self.assertIn("center?'<strong class=\"rating-cup-count\">'", body)
        self.assertIn("rating-podium-list", CSS)

    def test_switcher_is_removed_but_own_entry_buttons_keep_routes(self):
        body = WEB.split("function _renderRatingContent(){", 1)[1].split(
            "/* ---------- Clipboard / share / toast helpers ---------- */", 1
        )[0]
        self.assertNotIn("rt-seg", body)
        self.assertNotIn("rt-ladder", body)
        self.assertNotIn("setRatingTab(", body)
        self.assertIn('show:function(s,ratingSource)', WEB)
        self.assertIn('ratingTabCur=ratingSource==="friends"?"friends":"league"', WEB)
        self.assertIn('openFriends:function(){App.show("rating","friends")}', WEB)
        self.assertIn('profile-friends-link', WEB)
        self.assertIn('if(ratingTabCur==="friends")', body)

    def test_no_unimplemented_automatic_promotion_claim(self):
        self.assertIn("Рейтинги ҳафта · Топ 5", WEB)
        self.assertNotIn("r.promote+' <span", WEB)
        self.assertIn("rating_weekly_top_five", ANDROID)
        self.assertNotIn("TabSwitch(selected", ANDROID)

    def test_native_has_real_server_league_and_one_member_count(self):
        self.assertIn("RatingPodium(", ANDROID)
        self.assertNotIn("item { LeagueLadder", ANDROID)
        self.assertIn("LEAGUE_LADDER.indexOfFirst", PODIUM)
        self.assertIn("count = memberCount", PODIUM)
        self.assertEqual(PODIUM.count("count = null"), 2)
        self.assertIn("onOpenChallenges", ANDROID)
        self.assertIn("ratingViewModel.selectTab(RatingTab.LEAGUE)", MAIN)
        self.assertIn("ratingViewModel.selectTab(RatingTab.FRIENDS)", MAIN)

    def test_backend_rank_logic_is_unchanged(self):
        self.assertIn("CourseXpEvent.week_start == week_start", SERVICE)
        self.assertIn("func.coalesce(weekly.c.weekly_xp, 0).desc()", SERVICE)
        self.assertIn("def league_for_xp(xp_total:", SERVICE)
        self.assertIn('"league_size": len(rows)', SERVICE)


if __name__ == "__main__":
    unittest.main()
