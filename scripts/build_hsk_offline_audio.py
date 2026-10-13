#!/usr/bin/env python3
"""Prepare shared offline Mandarin audio for Android and Telegram Mini App.

Run locally (NOT on Railway): python scripts/build_hsk_offline_audio.py --dry-run
Then: python scripts/build_hsk_offline_audio.py --limit 100
Then: python scripts/build_hsk_offline_audio.py

Reads Chinese literals from course seed scripts plus optional UTF-8 input files
(one Chinese word/phrase per line). Existing MP3 files are never regenerated.
Generated assets are shared: Android bundles android/.../assets/audio/words,
and the Mini App's TTS service serves the very same files directly.
"""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "android/app/src/main/assets/audio/words"
SEEDS = ROOT / "scripts"
VOICE = "zh-CN-XiaoxiaoNeural"
RATE = "-10%"
CHINESE = re.compile(r"[\u3400-\u9fff]")
# Limit extraction to quoted Chinese values, rather than arbitrary Python code.
QUOTED = re.compile(r"""(['"])([^\n\r]{1,240}?)\1""")
REPLACEMENT = re.compile(r"[\u3400-\u9fff]")
CONTROL = re.compile(r"[\x00-\x1f]")
ENDPOINT = (
    "wss://api.msedgeservices.com/tts/cognitiveservices/websocket/v1"
)


def audio_name(text: str) -> str:
    return "_".join(str(ord(char)) for char in text) + ".mp3"


def corpus(extra_files: list[Path]) -> list[str]:
    texts: set[str] = set()
    for path in sorted(SEEDS.glob("seed_hsk*_lesson_*.py")):
        source = path.read_text(encoding="utf-8")
        for match in QUOTED.finditer(source):
            value = match.group(2).strip()
            if CHINESE.search(value) and not CONTROL.search(value):
                texts.add(value)
    for path in extra_files:
        for line in path.read_text(encoding="utf-8").splitlines():
            value = line.strip()
            if value and CHINESE.search(value) and len(value) <= 240:
                texts.add(value)
    return sorted(t for t in texts if len(t) <= 240)


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0,
                        help="Maximum missing MP3 files to create (0=all)")
    parser.add_argument("--delay", type=float, default=1.5,
                        help="Seconds between Microsoft requests")
    parser.add_argument("--input", type=Path, action="append", default=[],
                        help="Additional UTF-8 Chinese lines file")
    args = parser.parse_args()
    words = corpus(args.input)
    missing = [t for t in words if not (OUT / audio_name(t)).is_file()]
    print(f"Unique Chinese literals: {len(words)}; missing MP3: {len(missing)}")
    if args.dry_run:
        for t in missing[:25]:
            print("MISSING", t)
        return 0
    try:
        import edge_tts
        import edge_tts.communicate as cm
        from edge_tts.constants import TRUSTED_CLIENT_TOKEN
    except ImportError:
        print("Install dependencies: pip install -r requirements.txt", file=sys.stderr)
        return 2
    cm.WSS_URL = (
        f"{ENDPOINT}?Ocp-Apim-Subscription-Key={TRUSTED_CLIENT_TOKEN}"
    )
    OUT.mkdir(parents=True, exist_ok=True)
    completed = 0
    errors = 0
    for word in missing[:args.limit] if args.limit > 0 else missing:
        target = OUT / audio_name(word)
        temporary = target.with_suffix(".mp3.part")
        try:
            await asyncio.wait_for(
                edge_tts.Communicate(word, VOICE, rate=RATE).save(str(temporary)),
                timeout=20,
            )
            if temporary.stat().st_size < 128:
                raise ValueError("Empty MP3")
            temporary.replace(target)
            completed += 1
            print(f"OK {completed}: {word}")
        except Exception as exc:
            errors += 1
            print(f"FAILED {word}: {type(exc).__name__}", file=sys.stderr)
            temporary.unlink(missing_ok=True)
            if errors >= 5:
                print("Stopping after 5 failures to avoid provider load.")
                break
        await asyncio.sleep(max(0.5, args.delay))
    print(f"Generated: {completed}; failed: {errors}; still missing: "
          f"{sum(not (OUT / audio_name(t)).is_file() for t in words)}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
