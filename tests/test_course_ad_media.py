"""Course-ad media preparation keeps legacy output and PWA assets bounded."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services.course_ad_media import (
    CourseAdVideoError,
    prepare_course_ad_video_file,
    prepare_pwa_course_ad_video_file,
)


class CourseAdVideoPreparationTests(unittest.TestCase):
    def test_pwa_video_uses_transcoded_mp4_and_atomic_server_filename(self):
        with tempfile.TemporaryDirectory(prefix="course-ad-pwa-video-") as media_root:
            def fake_run(command, *, check, timeout):
                self.assertTrue(command[0].endswith("ffmpeg"))
                self.assertIn("-nostdin", command)
                self.assertIn("libx264", command)
                self.assertEqual(timeout, 120)
                Path(command[-1]).write_bytes(b"encoded-mp4")

            with patch("app.services.course_ad_media.shutil.which", return_value="/usr/bin/ffmpeg"), \
                    patch("app.services.course_ad_media.subprocess.run", side_effect=fake_run):
                filename = prepare_pwa_course_ad_video_file(
                    b"source-video", raw_ext=".webm", media_root=media_root,
                )

            self.assertRegex(filename, r"^course_ad_pwa_[0-9a-f]{32}\.mp4$")
            self.assertEqual((Path(media_root) / filename).read_bytes(), b"encoded-mp4")
            self.assertEqual({path.name for path in Path(media_root).iterdir()}, {filename})

    def test_pwa_transcode_failure_removes_source_and_staging_files(self):
        with tempfile.TemporaryDirectory(prefix="course-ad-pwa-video-fail-") as media_root:
            with patch("app.services.course_ad_media.shutil.which", return_value="/usr/bin/ffmpeg"), \
                    patch("app.services.course_ad_media.subprocess.run",
                          side_effect=subprocess.CalledProcessError(1, ["ffmpeg"])):
                with self.assertRaisesRegex(CourseAdVideoError, "video_transcode_failed"):
                    prepare_pwa_course_ad_video_file(
                        b"invalid-video", raw_ext=".mp4", media_root=media_root,
                    )
            self.assertEqual(list(Path(media_root).iterdir()), [])

    def test_missing_ffmpeg_fails_closed_without_publishing_media(self):
        with tempfile.TemporaryDirectory(prefix="course-ad-no-ffmpeg-") as media_root:
            with patch("app.services.course_ad_media.shutil.which", return_value=None):
                with self.assertRaisesRegex(CourseAdVideoError, "ffmpeg_not_available"):
                    prepare_course_ad_video_file(
                        b"source-video", raw_ext=".mp4", telegram_id=123,
                        media_root=media_root,
                    )
            self.assertEqual(list(Path(media_root).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
