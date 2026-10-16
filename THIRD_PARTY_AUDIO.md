# Emergency Mandarin word recordings

HSK AI prefers its own bundled Edge Xiaoxiao MP3 recordings, previously
generated cached lesson MP3s, and the configured Edge/Gemini providers. When
neither provider is available, the server may retrieve a **short publicly
licensed human pronunciation recording** for an isolated Chinese word. These
recordings are cached and served as MP3 to support Android 1.7.10, whose
playback path assumes MP3. No account data or user recordings are sent to the
audio repositories.

These recordings have their own licenses. They are **not** part of HSK AI's
proprietary source licensing.

## Offline emergency recording for 你好

The bundled `app/static/audio/tts_fallback/nihao-cc-by-sa.mp3` is an
**adaptation** of two Mandarin syllable recordings (`ni2` + `hao3`),
including the correct third-tone sandhi `ní hǎo`. Original speaker:
**Chen Wang**; source: [hugolpz/audio-cmn](https://github.com/hugolpz/audio-cmn),
`64k/syllabs/cmn-ni2.mp3` and `cmn-hao3.mp3`, curated/compressed by
Hugo Lopez. Licensed under **Creative Commons Attribution-ShareAlike**,
which also applies to the combined audio. Changes: removed each original
MP3's metadata and gapless-control frame and joined the audio streams.
This deliberately simple join can sound slower than naturally spoken 你好;
it is an emergency fallback when normal audio is unavailable. Authors do
not endorse HSK AI.

## Sources and attribution

1. **你好 (nǐ hǎo)**: recording by **Sjors Provoost**, 15 February 2011,
   [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Zh_n%C7%90_h%C7%8Eo.ogg).
   Original Ogg file converted to MP3 by Wikimedia Commons. Licensed under
   [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/).
   No endorsement implied.

2. **Other HSK words where available**:
   [hugolpz/audio-cmn](https://github.com/hugolpz/audio-cmn)
   (curation/compression by Hugo Lopez and collaborators, human
   pronunciation recordings by **Yue Tan**, and contributing recorders).
   Recordings licensed under CC BY-SA; see the
   [original repository](https://github.com/hugolpz/audio-cmn) for detailed
   author credits and license information.

The MP3s are used as-is, as audio pronunciations, not embedded in lessons'
text content, and fetched only on provider failure. Third-party sources may
be unreachable or lack a given word. In those cases the TTS endpoint can
still return an error; it will never substitute unrelated audio. The
per-process server cache is ephemeral until a persistent volume is
provisioned.
