"""Regression contracts for the Telegram Mini App lesson and practice layout."""

import unittest
from pathlib import Path


SOURCE = (Path(__file__).resolve().parents[1] / "app/static/course-v3.html").read_text(encoding="utf-8")


class CourseMobilePracticeContractTests(unittest.TestCase):
    def test_question_card_stays_in_scrollable_body(self):
        start = SOURCE.index("function syncLessonCoachLine(){")
        end = SOURCE.index("function renderLessonCoach(card,mood){", start)
        coach = SOURCE[start:end]
        self.assertIn('dock.classList.remove("beside")', coach)
        self.assertIn('dock.classList.toggle("question"', coach)
        self.assertNotIn("slot.appendChild(material[i])", coach)
        self.assertIn(".fbody{flex:1;min-height:0;overflow-y:auto;", SOURCE)

    def test_mobile_question_is_readable_and_options_scroll(self):
        self.assertIn(".fbody .qcard{width:100%;min-width:0}", SOURCE)
        self.assertIn(".fbody .qcard .qh.qask{font-size:clamp(", SOURCE)
        self.assertIn("@media(max-width:390px),(max-height:740px)", SOURCE)
        self.assertIn(".fbody .opt{min-height:50px;", SOURCE)

    def test_russian_question_does_not_force_chinese_serif(self):
        self.assertIn('qask\'+(/[\\u3400-\\u9fff]/.test(p)?" han":"")+', SOURCE)

    def test_hsk30_practice_rechecks_stale_denial(self):
        start = SOURCE.index("  show:function(s){")
        end = SOURCE.index("    var previous=SCREEN;", start)
        show = SOURCE[start:end]
        self.assertIn("courseTrackStatus(true)", show)
        self.assertIn("if(refreshed&&refreshed.allowed)", show)
        self.assertIn("renderHsk30AccessGate(loaded)", show)
        self.assertIn("if(MASHQ_ACCESS_PENDING)return", show)


if __name__ == "__main__":
    unittest.main()
