"""Bounded on-disk media preparation shared by legacy and PWA course-ad flows."""
import contextlib
import os
import shutil
import subprocess
import time
from uuid import uuid4

from app.services.course_ad_service import (
    COURSE_AD_ALLOWED_IMAGE_EXTENSIONS,
    COURSE_AD_ALLOWED_VIDEO_EXTENSIONS,
)

COURSE_AD_MAX_UPLOAD_BYTES = 25 * 1024 * 1024


class CourseAdVideoError(Exception):
    pass


def _transcode_course_ad_video(data: bytes, *, raw_ext: str, media_root: str,
                               output_path: str, safe_input: bool = False) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise CourseAdVideoError("ffmpeg_not_available")

    source_ext = raw_ext if raw_ext in COURSE_AD_ALLOWED_VIDEO_EXTENSIONS else ".mp4"
    source_path = os.path.join(media_root, f".course_ad_upload_{uuid4().hex}{source_ext}")
    descriptor = os.open(source_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
        input_options = []
        if safe_input:
            # A claimed MP4/WebM must never be auto-detected as an HLS or
            # concat playlist capable of reaching network or sibling files.
            input_options = ['-max_alloc', '67108864', '-filter_threads', '1', '-threads', '2', '-protocol_whitelist', 'file,pipe', '-f',
                             'matroska' if source_ext == '.webm' else 'mov']
            if source_ext != '.webm':
                input_options += ['-enable_drefs', '0', '-use_absolute_path', '0']
        subprocess.run(
            [
                ffmpeg, "-y", "-nostdin", "-hide_banner", "-loglevel", "error",
                *input_options,
                "-i", source_path, "-map", "0:v:0", "-map", "0:a?",
                "-vf", "scale='min(720,iw)':-2:force_original_aspect_ratio=decrease,format=yuv420p",
                "-c:v", "libx264", *(["-threads", "2"] if safe_input else []), "-preset", "veryfast", "-profile:v", "main",
                "-level", "3.1", "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart", "-shortest", output_path,
            ],
            check=True,
            timeout=120,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        with contextlib.suppress(OSError):
            os.remove(output_path)
        raise CourseAdVideoError("video_transcode_failed") from exc
    finally:
        with contextlib.suppress(OSError):
            os.remove(source_path)

    if not os.path.exists(output_path) or os.path.getsize(output_path) <= 0:
        raise CourseAdVideoError("video_transcode_failed")


def prepare_course_ad_video_file(data: bytes, *, raw_ext: str, telegram_id: int,
                                 media_root: str) -> str:
    """Keep the established Telegram Admin Mini App filename and MP4 behavior."""
    os.makedirs(media_root, exist_ok=True)
    token = uuid4().hex[:10]
    final_name = f"course_ad_{telegram_id}_{int(time.time())}_{token}.mp4"
    _transcode_course_ad_video(
        data, raw_ext=raw_ext, media_root=media_root,
        output_path=os.path.join(media_root, final_name),
    )
    return final_name


def prepare_pwa_course_ad_video_file(data: bytes, *, raw_ext: str,
                                     media_root: str) -> str:
    """Transcode and atomically publish a randomly named PWA MP4 asset."""
    os.makedirs(media_root, exist_ok=True)
    token = uuid4().hex
    final_name = f"course_ad_pwa_{token}.mp4"
    temporary_path = os.path.join(media_root, f".admin-pwa-{token}.tmp.mp4")
    final_path = os.path.join(media_root, final_name)
    try:
        _transcode_course_ad_video(
            data, raw_ext=raw_ext, media_root=media_root,
            output_path=temporary_path,
            safe_input=True,
        )
        os.replace(temporary_path, final_path)
    except Exception:
        with contextlib.suppress(OSError):
            os.remove(temporary_path)
        raise
    return final_name


def prepare_course_ad_image_file(data: bytes, *, raw_ext: str, telegram_id: int,
                                 media_root: str) -> str:
    """Store an image under the established Telegram Admin Mini App filename."""
    os.makedirs(media_root, exist_ok=True)
    token = uuid4().hex[:10]
    ext = raw_ext if raw_ext in COURSE_AD_ALLOWED_IMAGE_EXTENSIONS else ".jpg"
    final_name = f"course_ad_{telegram_id}_{int(time.time())}_{token}{ext}"
    final_path = os.path.join(media_root, final_name)
    tmp_path = f"{final_path}.upload"
    try:
        with open(tmp_path, "wb") as handle:
            handle.write(data)
        os.replace(tmp_path, final_path)
    except OSError:
        with contextlib.suppress(OSError):
            os.remove(tmp_path)
        raise
    if not os.path.exists(final_path) or os.path.getsize(final_path) <= 0:
        raise CourseAdVideoError("media_upload_failed")
    return final_name
