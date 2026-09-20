# HSK AI iOS Implementation Plan

Branch: `codex/ios-app`
Target: native iPhone app using Swift + SwiftUI.
Scope boundary: app implementation through a real-device release candidate. App Store submission/review is outside this plan.

## Non-negotiable rules

- Android, Mini App and desktop business logic stay authoritative; iOS must not invent a parallel course/access model.
- Server owns progress, XP, streak, subscription/access, ads, practice/exam scoring and challenge state.
- Tokens live in Keychain, never UserDefaults or logs.
- Network requests are HTTPS-only and pinned to the configured HSK AI API origin.
- User-visible copy must reach Uzbek, Russian and Tajik parity before release.
- Platform-specific behavior stays platform-specific: Android APK update flows are not copied to iOS.
- External checkout is not copied from the Android direct build into iOS without an explicit App Store policy decision.
- Each phase ends in a working state and a focused commit.

## Phase 0 — Foundation

- [x] Dedicated iOS branch.
- [x] iOS implementation plan.
- [x] Android → iOS parity matrix.
- [x] SwiftUI application skeleton.
- [x] Central production API environment.
- [x] HTTPS/origin-guarded API client.
- [x] Keychain-backed credential store.
- [ ] Generate Xcode project and compile on macOS CI/local Xcode.
- [ ] Add baseline unit test target and first network/config tests.

Exit gate: the blank native app builds for an iPhone simulator without touching Android/backend behavior.

## Phase 1 — Native auth

Backend:
- Add `ios` as a first-class native platform in the shared device auth service.
- Add iOS auth transport without duplicating cryptography/session logic.
- Preserve Telegram confirmation, polling-secret secrecy, refresh rotation and revoke behavior.
- Add iOS-specific analytics namespace.

Client:
- Installation key generation and secure persistence.
- Link start → Telegram deep link → status polling → token receipt.
- Access token injection and refresh-on-401.
- Logout/revoke.
- Existing session restore after cold launch.

Exit gate: new and existing Telegram users can sign in on a real iPhone and survive kill/reopen.

## Phase 2 — Bootstrap + onboarding + shell

- Bootstrap account state.
- Device-language pre-auth behavior; server account language after auth.
- Native onboarding parity: level, goal, daily minutes, focus, notification primer.
- Main tab/navigation shell.
- Shared design tokens/components.
- UZ/RU/TJ localization infrastructure.

Exit gate: authenticated user reaches the correct onboarding/main state with no duplicate navigation.

## Phase 3 — Course core

- Course map.
- Cached-first rendering + background refresh.
- Today plan, XP, streak, daily goal, gates and reward chest.
- Lesson fetch and completion idempotency.
- Lesson cards: text, vocabulary, MCQ, listening, matching, sentence gap, grammar/explanation and completion.
- Server TTS playback/cache.
- Hanzi stroke data/rendering.

Exit gate: a learner can complete a real production lesson end-to-end and progress matches Mini App/Android.

## Phase 4 — Practice suite

- Practice start/complete.
- Mistakes overview/review.
- Exam/test center.
- Recognition/word drill.
- Pronunciation drill.
- Correct result/retry/error states.

Exit gate: all learning-result writes are server-authoritative and survive relaunch.

## Phase 5 — Supporting product features

- Dictionary + local cache/versioning.
- Rating/leaderboard.
- Challenges/inbox/learner profile.
- Profile/settings/streak calendar.
- Trial/subscription state display.
- Server-controlled ads/unlock references.

Exit gate: primary Android feature set has an iOS equivalent or an explicitly documented OS-specific exception.

## Phase 6 — AI Voice + Assistant

- AVAudioSession/AVAudioRecorder flow.
- Microphone permission at point of use.
- M4A/AAC upload contract and size limits.
- Voice session/message/end.
- Pronunciation scoring.
- Audio interruption/background handling.
- AI Assistant conversations/messages/media.

Exit gate: voice and assistant work on a physical iPhone with permission-denied and interruption cases tested.

## Phase 7 — Native iOS integrations

- Local study reminders.
- Deep links.
- WidgetKit widget with App Group data bridge.
- Background refresh only where justified by iOS lifecycle rules.

Exit gate: platform integrations degrade safely when permission is denied.

## Phase 8 — Hardening and release candidate

- Unit tests for auth/network/mappers/core state.
- XCUITest smoke: cold launch, auth, onboarding, course, lesson, practice, profile, voice permission.
- Poor network/offline tests.
- Dark mode + Dynamic Type.
- Real-device audio/microphone tests.
- Security pass: Keychain, logs, URL boundary, temp-media cleanup.
- Regression check: Android/Mini App/Desktop unchanged.
- Release build `1.0.0` installed on a physical iPhone.

Exit gate: clean-account and existing-account production smoke pass with no known blocker.

## Commit discipline

Each feature lands as a small iOS-focused commit on `codex/ios-app`. Do not merge/push this work into `main` until the relevant local/CI tests pass and the owner explicitly promotes it.
