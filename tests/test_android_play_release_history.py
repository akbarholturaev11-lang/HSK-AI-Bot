"""Official Google Play releases are counted, not versionCode gaps."""
import json
import unittest

from scripts.android_sync_play_releases import confirmed_codes, merge
from app.services.android_play_release_history_service import parse_play_release_history


def release(*codes, status="completed"):
    return {"versionCodes": [str(x) for x in codes], "status": status}


class PlayReleaseHistoryTests(unittest.TestCase):
    def test_qa_draft_halted_and_multi_apk_release_not_overcounted(self):
        track = {"track": "production", "releases": [
            release(10, 11), release(25, status="inProgress"),
            release(99, status="draft"), release(80, status="halted")
        ]}
        self.assertEqual(confirmed_codes(track), [11, 25])

    def test_real_release_polling_only_appends_newly_published_version(self):
        one = merge({"track": "production", "releases": [release(11)]}, {})
        self.assertEqual(one["published_version_codes"], [11])
        repeat = merge({"track": "production", "releases": [release(11)]}, one)
        self.assertEqual(repeat["published_version_codes"], [11])
        next_release = merge({"track": "production", "releases": [
            release(11), release(25, status="inProgress")
        ]}, repeat)
        self.assertEqual(next_release["published_version_codes"], [11, 25])
        self.assertEqual(parse_play_release_history(json.dumps(next_release).encode()), (11, 25))
        self.assertEqual(merge({"track": "production", "releases": [
            release(11), release(25, status="halted")
        ]}, next_release)["published_version_codes"], [11, 25])

    def test_invalid_or_empty_sources_rejected(self):
        for bad in ({"track": "internal", "releases": [release(1)]},
                    {"track": "production", "releases": [release(1, status="draft")]},
                    {"track": "production", "releases": [release(-1)]}):
            with self.assertRaises(ValueError):
                merge(bad, {})
        state = merge({"track": "production", "releases": [release(11)]}, {})
        for invalid in ([11, 11], [20, 11], [True], [], "11"):
            with self.subTest(invalid=invalid):
                record = {**state, "published_version_codes": invalid}
                with self.assertRaises(ValueError):
                    parse_play_release_history(json.dumps(record).encode())


if __name__ == "__main__":
    unittest.main()
