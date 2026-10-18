"""Serve only bundled tour audio files, preserving correct MIME types.

Tour narration includes .wav files (f01..f10) and .mp3 files (b1, etc.).
The public route must not accidentally treat WAV files as MP3 or allow
arbitrary file reads.
"""
from __future__ import annotations

import re
from pathlib import Path

AUDIO_TOUR_ROOT = Path(__file__).resolve().parents[1] / "static" / "audio" / "tour"
_AUDIO_NAME = re.compile(r"[A-Za-z0-9_-]+\.(?:wav|mp3)\Z")
_LANGS = frozenset(("uz", "ru", "tj"))


def resolve_tour_audio(lang: str, filename: str) -> tuple[Path, str] | None:
    if lang not in _LANGS or not _AUDIO_NAME.fullmatch(filename):
        return None
    audio = AUDIO_TOUR_ROOT / lang / filename
    if not audio.is_file():
        return None
    return audio, ("audio/wav" if audio.suffix == ".wav" else "audio/mpeg")
