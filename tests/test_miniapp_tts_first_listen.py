"""First-play latency regressions for Mandarin audio in the Telegram Mini App."""
from pathlib import Path
import unittest

HTML = (Path(__file__).resolve().parents[1] / "app/static/course-v3.html").read_text("utf-8")
AUDIO = HTML.split("function prefetchTTS(t){", 1)[1].split("/* ---------- App ---------- */", 1)[0]
LESSON = HTML.split("function startLesson(idx,opts){", 1)[1].split("function lessonMaterialRef(", 1)[0]
PREVIEW = HTML.split("function openLessonSheet(idx){", 1)[1].split("/* ---------- Skip-ahead test", 1)[0]


class MiniappFirstListenTests(unittest.TestCase):
    def test_first_two_words_are_prefetched_on_lesson_preview(self):
        self.assertIn("function warmLessonPreviewAudio(lv,n){", AUDIO)
        self.assertIn("if(first.length<2)first.push(text)", AUDIO)
        self.assertIn("warmLessonPreviewAudio((MAP&&MAP.level)||\"hsk1\",l.n)", PREVIEW)

    def test_first_card_audio_warms_during_panda_loading(self):
        self.assertIn("cardAudioTexts(Flow.queue[Flow.i])[0]", LESSON)
        self.assertIn("firstCardAudio?prefetchTTS(firstCardAudio)", LESSON)
        self.assertIn("Promise.race([audioWarmup", LESSON)
        self.assertIn("},1800);", LESSON)

    def test_provider_failure_does_not_trigger_duplicate_tts_fetch(self):
        self.assertIn("if(src)playSource(src);else _ttsFallback(t)", AUDIO)
        self.assertNotIn("playSource(_ttsCache[t]||ttsUrl(t))", AUDIO)

    def test_background_prefetch_bounded_to_three_phrases(self):
        self.assertIn("count<3", AUDIO)
        self.assertIn("seen[word]=true;prefetchTTS(word);count++", AUDIO)


if __name__ == "__main__":
    unittest.main()
