#!/usr/bin/env python3
"""Bundle every dictionary word's pronunciation into the APK.

The dictionary's words and writing order already travel with the app. The
sound did not: the listen button asked the server to synthesise the word, so
with no connection it said nothing. This renders the same audio the server
would — same voice, same rate, read from `app/api/android_course.py` so the
two cannot drift — once, at build time.

  assets/audio/words/<code points>.mp3   one file per word, e.g. 你们 ->
                                         20320_20204.mp3

The server's MP3 is 48 kbps with silence at both ends. For a spoken word that
is mostly padding and bit rate nobody hears, so the audio is trimmed and
re-encoded at 32 kbps mono: roughly a third of the size, same voice.

Existing files are kept, so a run after a word-list change only renders the
new words. `--force` renders everything again (after a voice change).

This needs network access and three packages the app itself never uses:

    pip install edge-tts miniaudio lameenc
    python3 android/tools/build_word_audio.py

`check_dictionary_assets.py` verifies that every word has its file; it does
not need any of these packages.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from array import array
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
ASSETS = ROOT / "android" / "app" / "src" / "main" / "assets"
AUDIO_DIR = ASSETS / "audio" / "words"
SERVER_TTS = ROOT / "app" / "api" / "android_course.py"

SAMPLE_RATE = 24_000
BIT_RATE = 32
# Quieter than this is silence. edge-tts pads its output with near-zero
# samples; speech is far above this.
SILENCE_LEVEL = 400
# Kept on each side of the speech so the attack and the tail are not clipped.
PAD_SECONDS = 0.06
CONCURRENCY = 6
ATTEMPTS = 3


def server_constant(name: str) -> str:
    text = SERVER_TTS.read_text(encoding="utf-8")
    match = re.search(rf'^{name}\s*=\s*"([^"]+)"', text, re.M)
    if not match:
        raise SystemExit(f"{name} not found in {SERVER_TTS}")
    return match.group(1)


def audio_name(word: str) -> str:
    return "_".join(str(ord(ch)) for ch in word) + ".mp3"


def js_literal(path: Path, name: str) -> object:
    text = path.read_text(encoding="utf-8")
    marker = f"const {name}="
    value, _ = json.JSONDecoder().raw_decode(text, text.index(marker) + len(marker))
    return value


def trim_and_encode(mp3: bytes) -> bytes:
    import lameenc
    import miniaudio

    decoded = miniaudio.decode(
        mp3,
        output_format=miniaudio.SampleFormat.SIGNED16,
        nchannels=1,
        sample_rate=SAMPLE_RATE,
    )
    samples = array("h", decoded.samples)
    loud = [i for i, value in enumerate(samples) if abs(value) > SILENCE_LEVEL]
    if loud:
        pad = int(PAD_SECONDS * SAMPLE_RATE)
        samples = samples[max(0, loud[0] - pad): min(len(samples), loud[-1] + pad)]

    encoder = lameenc.Encoder()
    encoder.set_bit_rate(BIT_RATE)
    encoder.set_in_sample_rate(SAMPLE_RATE)
    encoder.set_channels(1)
    encoder.set_quality(2)
    return bytes(encoder.encode(samples.tobytes()) + encoder.flush())


async def render(word: str, voice: str, rate: str) -> bytes:
    import edge_tts

    audio = bytearray()
    async for chunk in edge_tts.Communicate(word, voice, rate=rate).stream():
        if chunk.get("type") == "audio":
            audio.extend(chunk["data"])
    if not audio:
        raise RuntimeError("empty audio")
    return trim_and_encode(bytes(audio))


async def main_async(force: bool) -> int:
    voice = server_constant("ANDROID_TTS_VOICE")
    rate = server_constant("ANDROID_TTS_RATE")
    words = js_literal(ASSETS / "hsk-words.js", "WORDS")
    texts = sorted({str(word.get("h", "")).strip() for word in words} - {""})

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    todo = [t for t in texts if force or not (AUDIO_DIR / audio_name(t)).is_file()]
    print(f"{len(texts)} words, {len(todo)} to render ({voice}, {rate})")

    gate = asyncio.Semaphore(CONCURRENCY)
    failed: list[str] = []
    done = 0

    async def one(word: str) -> None:
        nonlocal done
        async with gate:
            for attempt in range(ATTEMPTS):
                try:
                    data = await render(word, voice, rate)
                    (AUDIO_DIR / audio_name(word)).write_bytes(data)
                    break
                except Exception as exc:  # network hiccups are the usual cause
                    if attempt == ATTEMPTS - 1:
                        print(f"  failed: {word}: {exc}")
                        failed.append(word)
                    else:
                        await asyncio.sleep(1 + attempt * 2)
            done += 1
            if done % 100 == 0:
                print(f"  {done}/{len(todo)}")

    await asyncio.gather(*(one(word) for word in todo))

    # A word dropped from the list leaves its file behind otherwise.
    wanted = {audio_name(t) for t in texts}
    stale = [path for path in AUDIO_DIR.glob("*.mp3") if path.name not in wanted]
    for path in stale:
        path.unlink()

    total = sum(path.stat().st_size for path in AUDIO_DIR.glob("*.mp3"))
    print(f"audio/words/: {len(wanted) - len(failed)} files, {total / 1024 / 1024:.1f} MB"
          + (f", removed {len(stale)} stale" if stale else ""))
    if failed:
        print(f"{len(failed)} word(s) failed; run again to retry them")
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="render every word again")
    args = parser.parse_args()
    return asyncio.run(main_async(args.force))


if __name__ == "__main__":
    sys.exit(main())
