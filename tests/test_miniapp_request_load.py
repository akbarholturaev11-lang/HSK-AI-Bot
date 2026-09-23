"""Mini App request-load regressions.

These checks lock in the optimizations that keep a normal course open from
waking hidden screens or prefetching server state the learner did not ask for.
"""

import unittest
from pathlib import Path


COURSE = Path("app/static/course-v3.html").read_text(encoding="utf-8")
DESKTOP = Path("app/static/course_v3_data/desktop-download.js").read_text(encoding="utf-8")
ADS = Path("app/static/course_v3_data/ads.js").read_text(encoding="utf-8")


class MiniAppRequestLoadTests(unittest.TestCase):
    def test_hidden_rating_does_not_fetch_on_render_all(self):
        start = COURSE.index("function renderAll()")
        body = COURSE[start:COURSE.index("\n}", start) + 2]
        self.assertIn('if(SCREEN==="rating")renderRating()', body)
        self.assertNotIn("renderMashq();renderRating();", body)

    def test_course_prefetch_does_not_prefetch_practice_limits_or_assets(self):
        self.assertNotIn("function prefetchPracticeLimitStatus()", COURSE)
        start = COURSE.index("function prefetchNearbyLessons()")
        body = COURSE[start:COURSE.index("\n}", start) + 2]
        self.assertNotIn("prefetchPracticeLimitStatus()", body)
        self.assertNotIn("prefetchPracticeAssets()", body)

    def test_large_memorize_bundle_is_not_prefetched(self):
        start = COURSE.index("function prefetchPracticeAssets()")
        end = COURSE.index("\n}", start) + 2
        body = COURSE[start:end]
        self.assertNotIn('fetch("course_v3_data/memo.js', body)
        self.assertIn('loadJsOnce("hsk-words.js', body)

    def test_trial_status_is_lazy_single_flight_and_shared(self):
        self.assertIn(
            "var TRIAL_STATE=null,TRIAL_PROMISE=null,TRIAL_LOADED=false",
            COURSE,
        )
        self.assertIn("if(TRIAL_PROMISE)return TRIAL_PROMISE", COURSE)
        self.assertIn(
            "window.HskTrialState={get:trialFetchStatus,eligibility:trialEligibilityValue}",
            COURSE,
        )
        self.assertIn("window.HskTrialState.get", ADS)
        boot = COURSE[COURSE.index("(function(){\n  var bootLevel="):]
        marker = 'if(bootParams.get("onboarded")==="1")'
        self.assertNotIn("trialFetchStatus()", boot[:boot.index(marker)])

    def test_tts_playback_does_not_duplicate_same_phrase_with_prefetch(self):
        first = COURSE.index("function speak(t)")
        first_body = COURSE[first:COURSE.index("\n}", first) + 2]
        self.assertNotIn("prefetchTTS(t)", first_body)

        voice = COURSE.index("function speak(t)", first + 1)
        voice_body = COURSE[voice:COURSE.index("\n}", voice) + 2]
        self.assertNotIn("_ttsPrefetch(t)", voice_body)

    def test_internal_navigation_suppresses_false_exit_ping(self):
        self.assertIn("function beginInternalNavigation()", COURSE)
        self.assertIn(
            "if(internalNavigationActive()||EXIT_PINGED||!INIT_DATA)return",
            COURSE,
        )
        self.assertIn(
            'beginInternalNavigation();location.href="/hsk-lugat.html',
            COURSE,
        )
        self.assertIn(
            "beginInternalNavigation();\n    setTimeout(function(){location.href=url},40)",
            COURSE,
        )

    def test_download_status_is_the_only_android_availability_request(self):
        self.assertNotIn('"/api/v3/apps/public-status"', DESKTOP)
        self.assertNotIn("function loadAndroidAvailability()", DESKTOP)
        self.assertIn("data.platforms && data.platforms.android", DESKTOP)

    def test_hidden_profile_cannot_emit_entry_seen(self):
        start = DESKTOP.index("function renderProfile()")
        body = DESKTOP[start:DESKTOP.index("\n  function ", start + 1)]
        self.assertIn('document.getElementById("s-profile")', body)
        self.assertIn('!profileScreen.classList.contains("on")', body)


if __name__ == "__main__":
    unittest.main()
