"""Published Android updates use read-only Google Play Releases API."""
import json
import unittest

from scripts.android_sync_play_releases import confirmed_codes, merge
from app.services.android_play_release_history_service import parse_play_release_history


def release(*codes, status="RELEASE_LIFECYCLE_STATE_PUBLISHED", track="production"):
    return {"track": track,
            "activeArtifacts": [{"versionCode": code} for code in codes],
            "releaseLifecycleState": status}


def response(*items):
    return {"releases": list(items)}


class PlayReleaseHistoryTests(unittest.TestCase):
    def test_workflow_is_read_only_and_never_opens_a_play_edit(self):
        from pathlib import Path
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/android-play-release-mirror.yml").read_text()
        self.assertIn("/tracks/production/releases", workflow)
        self.assertNotIn("--request POST", workflow)
        self.assertNotIn("--request DELETE", workflow)
        self.assertNotIn("/edits", workflow)
        self.assertIn("ANDROID_PLAY_RELEASE_SYNC_ENABLED", workflow)

    def test_only_published_production_releases_count(self):
        data = response(
            release(10, 11), release(25),
            release(99, status="RELEASE_LIFECYCLE_STATE_DRAFT"),
            release(80, status="RELEASE_LIFECYCLE_STATE_APPROVED_NOT_PUBLISHED"),
            release(71, status="RELEASE_LIFECYCLE_STATE_IN_REVIEW"),
        )
        self.assertEqual(confirmed_codes(data), [10, 25])

    def test_multi_apk_release_is_one_with_conservative_lower_bound(self):
        data = response(release(21, 24), release(31, 35), release(60))
        self.assertEqual(confirmed_codes(data), [21, 31, 60])
        self.assertEqual(merge(data, {})["published_version_codes"], [21, 31, 60])

    def test_published_release_history_is_append_only_and_idempotent(self):
        initial = merge(response(release(11)), {})
        self.assertEqual(initial["published_version_codes"], [11])
        same = merge(response(release(11)), initial)
        self.assertEqual(same["published_version_codes"], [11])
        newer = merge(response(release(11), release(25)), same)
        self.assertEqual(newer["published_version_codes"], [11, 25])
        self.assertEqual(parse_play_release_history(json.dumps(newer).encode()), (11, 25))
        # A truncated API history never withdraws previously published codes.
        self.assertEqual(merge(response(release(25)), newer)["published_version_codes"], [11, 25])

    def test_incomplete_or_wrong_track_fails_without_inventing_releases(self):
        for bad in (
            response(),
            response(release(1, status="RELEASE_LIFECYCLE_STATE_DRAFT")),
            response(release(-1)),
            response(release(1, track="internal")),
            response({"track": "production", "releaseLifecycleState":
                      "RELEASE_LIFECYCLE_STATE_PUBLISHED"}),
            {"track": "production", "releases": [release(1)]},
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    merge(bad, {})
        valid = merge(response(release(11)), {})
        for invalid in ([11, 11], [20, 11], [True], [], "11"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    parse_play_release_history(json.dumps(
                        {**valid, "published_version_codes": invalid}
                    ).encode())


if __name__ == "__main__":
    unittest.main()
