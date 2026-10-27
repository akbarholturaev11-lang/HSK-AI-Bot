# Live Voice Chinese transcription hints

- **Cause:** Live used empty `input_audio_transcription` configuration, leaving
  speech language detection automatic. The learner reported Chinese speech
  being transcribed as English/French. The account's UZ/RU/TJ explanation
  language is a separate setting; Android Play resource splitting does not
  control server-side speech recognition.
- **Fix:** Send the supported Chinese input hint
  `AudioTranscriptionConfig(language_codes=["zh-CN"])`. Keep the existing
  `gemini-3.8-live` model, output transcript, translations, access and budget
  behavior. SDK 2.15.0 is the first release that forwards this field to the
  Gemini Developer API. Its Pydantic requirement needs the coordinated pins
  `pydantic==2.12.5`, `pydantic_core==2.41.5` and `aiogram==3.23.0`.
- **Risk:** Language codes are recognition hints, not a guarantee of accurate
  transcription. They cannot reconstruct an earlier recording. Real provider
  acceptance and recognition quality must be distinguished from local tests.
- **Prevention:** `LiveChineseTranscriptionConfigTests` exercises the real SDK
  Developer API setup serialization through a mocked WebSocket for UZ/RU/TJ.
  It checks the Chinese input hint, unchanged output transcript and model,
  and preserved account explanation language. Check dependency resolution and
  bot/auth/AI/Voice regressions together when changing the SDK.

Do not infer transport support from the SDK type alone: in 1.75.0 the field
exists, but its Developer API converter raises `ValueError`. Its Live connector
also rejects request-level `http_options` and does not merge client-level
`extra_body` into setup. Do not bypass that with private converter patches.

Verification: the SDK 2.15.0 setup-wire test passes with Chinese input hints
for all three explanation languages. A bounded synthetic-Chinese upstream
probe could not connect because provider credentials were unavailable; actual
upstream setup acceptance and recognition quality remain unverified.

Dependency resolution and `pip check` pass in an isolated environment. The
55-file bot/auth/onboarding/identity/AI/Voice batch passes 507 tests and 1114
subtests; 16 PostgreSQL tests skip without an isolated database. The subsequent
real-SDK Live and regular-transcription transport batch passes 15 tests and
10 subtests, including unchanged audio bytes/prompt and usage token accounting.

The broad non-E2E run is **not green**: 3799 tests pass, 131 skip and 19 fail.
Three failures used the test's initial camelCase expectation loaded before its
correction; the final wire test passes. The other 16 reproduce on pristine
`a6d282c0` with the original dependency pins: 13 existing source-contract
failures, two missing preparing-script subtests and a QA worker singleton-router
failure after importing `app.main` (standalone passes under both dependency
sets). Do not count those baseline failures as fixed or as full-suite acceptance.

Sources:

- [Google Live API transcription configuration](https://ai.google.dev/api/live#AudioTranscriptionConfig)
- [Official SDK 2.15.0 change](https://github.com/googleapis/python-genai/commit/fc282b359a7e9e16219587266c94d2bdc506164a)
- [Aiogram 3.23.0 compatibility changes](https://docs.aiogram.dev/en/v3.23.0/changelog.html)
