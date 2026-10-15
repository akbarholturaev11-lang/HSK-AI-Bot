#!/usr/bin/env python3
"""Generate reusable Mandarin lesson MP3s without sending learner requests to TTS.

Source: deployed static course_v3_data/<level>/lesson_*.json, all 2.0 / 3.0
levels. Extract only fields the lesson UI may speak, never translation
explanations. One file is stored in the shared offline_audio corpus and uploaded to
Cloudflare R2 for Android; Mini App can reuse it without synthesis.

Examples:
  python scripts/build_hsk_offline_audio.py --dry-run
  python scripts/build_hsk_offline_audio.py --only '大家好！' --limit 1
  python scripts/build_hsk_offline_audio.py --limit 25 --delay 2
  python scripts/build_hsk_offline_audio.py --delay 2

Run outside Railway. It is resumable: existing valid MP3s are skipped.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "offline_audio/words"
COURSES = ROOT / "app/static/course_v3_data"
INDEX = ROOT / "app/static/audio/words-index.js"
VOICE = "zh-CN-XiaoxiaoNeural"
RATE = "-10%"
HANZI = re.compile(r"[\u3400-\u9fff]")
SPEAKABLE = {"zh", "phrase", "audio_text"}
ENDPOINT = (
    "wss://api.msedgeservices.com/tts/cognitiveservices/websocket/v1"
)


def audio_name(text: str) -> str:
    """Keep current Android asset naming, with a short hash for long phrases.

    Android assets and server use this exact algorithm; <=240 bytes keeps
    the basename within typical per-file system and packaging limits.
    """
    normal = "_".join(str(ord(c)) for c in text) + ".mp3"
    if len(normal.encode("utf-8")) <= 240:
        return normal
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()
    return "sha1_" + digest + ".mp3"


def valid_audio(path: Path) -> bool:
    try:
        if path.stat().st_size < 128:
            return False
        with path.open("rb") as handle:
            header = handle.read(3)
        return header.startswith(b"ID3") or (
            len(header) > 1 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0
        )
    except OSError:
        return False


def speakable(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or len(text) > 240 or not HANZI.search(text):
        return None
    if any(ord(char) < 32 for char in text):
        return None
    return text


def extract_audio_strings(node: object) -> set[str]:
    """Walk lesson structure but include only spoken Chinese payload fields."""
    found: set[str] = set()
    if isinstance(node, list):
        for child in node:
            found.update(extract_audio_strings(child))
    elif isinstance(node, dict):
        for key, value in node.items():
            if key in SPEAKABLE:
                text = speakable(value)
                if text:
                    found.add(text)
            if isinstance(value, (dict, list)):
                found.update(extract_audio_strings(value))
    return found


def corpus(extra_files: list[Path], only: list[str]) -> list[str]:
    texts: set[str] = set()
    if only:
        for item in only:
            text = speakable(item)
            if text:
                texts.add(text)
    else:
        for path in sorted(COURSES.glob("*/lesson_*.json")):
            lesson = json.loads(path.read_text(encoding="utf-8"))
            texts.update(extract_audio_strings(lesson))
        for path in extra_files:
            for raw in path.read_text(encoding="utf-8").splitlines():
                text = speakable(raw)
                if text:
                    texts.add(text)
    # Short words before the longer, more expensive dialogues.
    return sorted(texts, key=lambda text: (len(text), text))


def write_offline_index() -> int:
    """Small public manifest: only shipped MP3s are eligible for direct fetch.

    Short file names are reconstructed client-side with UTF-16 code units
    (equivalent to Kotlin Char.code for our current BMP Mandarin corpus).
    Only long phrases require an explicit sha1 filename map.
    """
    words = corpus([], [])
    existing = [word for word in words if valid_audio(OUT / audio_name(word))]
    short = [word for word in existing if not audio_name(word).startswith("sha1_")]
    long = {word: audio_name(word) for word in existing
            if audio_name(word).startswith("sha1_")}
    script = (
        "/* Pre-rendered Mandarin words only. Never an access or paywall gate. */\n"
        "window.HSK_OFFLINE_AUDIO=new Set("
        + json.dumps(short + list(long), ensure_ascii=False, separators=(",", ":"))
        + ");\n"
        "window.HSK_OFFLINE_LONG_NAMES="
        + json.dumps(long, ensure_ascii=False, separators=(",", ":"))
        + ";\n"
    )
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(script, encoding="utf-8")
    print(f"Offline manifest: {len(existing)}/{len(words)} ready; "
          f"{len(long)} hashed long phrases; {INDEX.stat().st_size} bytes.",
          flush=True)
    # A stale or missing audio asset must never be advertised as present.
    if len(existing) != len(words):
        print("WARNING: incomplete audio corpus; missing entries use server TTS.",
              file=sys.stderr)
    return 0


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--write-index", action="store_true",
                        help="Write public JS index of existing MP3s; no TTS")
    parser.add_argument("--limit", type=int, default=0,
                        help="Generate at most N missing files; zero means all")
    parser.add_argument("--delay", type=float, default=2.0,
                        help="Delay in seconds between external requests")
    parser.add_argument("--input", type=Path, action="append", default=[])
    parser.add_argument("--only", action="append", default=[],
                        help="Test specific Mandarin text before the batch")
    args = parser.parse_args()
    if args.write_index:
        return write_offline_index()
    words = corpus(args.input, args.only)
    missing = [text for text in words if not valid_audio(OUT / audio_name(text))]
    print(f"Source lessons: {len(list(COURSES.glob('*/lesson_*.json')))}")
    print(f"Unique Chinese audio: {len(words)}; missing: {len(missing)}", flush=True)
    if args.dry_run:
        for text in missing[:25]:
            print("MISSING", repr(text))
        return 0

    try:
        import edge_tts
        import edge_tts.communicate as communicate
        from edge_tts.constants import TRUSTED_CLIENT_TOKEN
    except ImportError:
        print("Install edge-tts==7.2.8 first.", file=sys.stderr)
        return 2
    communicate.WSS_URL = (
        f"{ENDPOINT}?Ocp-Apim-Subscription-Key={TRUSTED_CLIENT_TOKEN}"
    )
    OUT.mkdir(parents=True, exist_ok=True)
    completed = 0
    failed = 0
    consecutive_failures = 0
    to_create = missing[:args.limit] if args.limit > 0 else missing
    for text in to_create:
        target = OUT / audio_name(text)
        temporary = target.with_suffix(".mp3.part")
        generated = False
        for attempt in range(3):
            try:
                await asyncio.wait_for(
                    edge_tts.Communicate(text, VOICE, rate=RATE).save(str(temporary)),
                    timeout=25,
                )
                if not valid_audio(temporary):
                    raise ValueError("Invalid or empty MP3")
                temporary.replace(target)
                completed += 1
                consecutive_failures = 0
                generated = True
                print(f"GENERATED {completed}/{len(to_create)} {text}", flush=True)
                break
            except Exception as exc:
                temporary.unlink(missing_ok=True)
                status = getattr(exc, "status", None)
                print(f"RETRY {attempt+1}/3 {text!r}: "
                      f"{type(exc).__name__} status={status}",
                      file=sys.stderr, flush=True)
                if attempt < 2:
                    # Back off instead of hammering Microsoft's rate limiter.
                    await asyncio.sleep(20 * (attempt + 1) if status == 429 else 5)
        if not generated:
            failed += 1
            consecutive_failures += 1
            if consecutive_failures >= 3:
                print("Stopping after three consecutive failures to avoid "
                      "provider overload.", file=sys.stderr, flush=True)
                break
        await asyncio.sleep(max(1.0, args.delay))
    print(f"Done: generated={completed}, errors={failed}; "
          f"remaining={sum(not valid_audio(OUT / audio_name(t)) for t in words)}",
          flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
