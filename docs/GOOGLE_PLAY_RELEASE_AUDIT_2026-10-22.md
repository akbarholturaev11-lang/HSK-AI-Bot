# HSK AI Play code audit — 2026-10-22

**Scope:** `codex/android-play-readiness-20261022` based on `codex/p3-main-integration-20261020`. Read `main` as the architecture and release baseline before changes. **No merge, backend deployment, Play submission, upload or R2 publishing.** This is a source and CI contract review, **not a Google Play approval**.

That scope records the original 2026-10-22 audit. The owner subsequently authorized the main integration reviewed below.

## Source-backed build and entitlement facts

| Item | Audited source / result |
| --- | --- |
| Application ID | `com.pomp.hskai` in `android/app/build.gradle.kts`. Both `direct` and `play` release variants use the same application ID. |
| SDK | `compileSdk=36`, `targetSdk=36`, `minSdk=26`; Android handheld Play submissions require API 36 from 2026-08-31: https://support.google.com/googleplay/android-developer/answer/11926878 |
| Current source build | Read version from `android/app/build.gradle.kts` at build time; main at audit was `1.7.21` / `versionCode=52`. Do **not** assume it exceeds the latest *published* direct APK or a future Play version. |
| Direct APK | `src/direct` retains its external manual checkout, installer permission, FileProvider and in-app APK update mechanism; not edited by this branch. |
| Play | `src/play` contains status-only subscription/limit hosts and no-op sideload update hosts. Play HSK 3.0 dialogs hide prices and checkout CTAs, the shared Android rejected-manual-payment dialog is gated to direct, and rejected manual-payment notifications are suppressed on Play. Server-confirmed Pro/HSK 3.0 access and approval notifications remain available. |
| Pro + HSK 3.0 | Shared server entitlements are still read; no local unlock logic was changed. An account that has not been granted access cannot buy or unlock a paid entitlement inside the initial Play release. Free access granted by server/admin must remain functional. |
| Billing | Not implemented. `src/play/.../SubscriptionCheckoutHost.kt` is the future *native* Play Billing extension point. Server-side validation will be required before implementing purchases. |
| Signing | `.github/workflows/android-release.yml` pins the direct APK certificate SHA-256. The manual Play preflight checks both signed APKs and the signed AAB against this pin. **The real signing key is never included in Git.** |
| Google Play App Signing | First enrollment MUST import the *existing direct APK app signing key*, not let Google create a new signing key. Verify the **app signing certificate** (not just upload certificate) in Play Console against a known-good installed direct APK. |
| Android manifest | Shared permissions: INTERNET, ACCESS_NETWORK_STATE, RECORD_AUDIO, POST_NOTIFICATIONS, VIBRATE; optional microphone feature; backup disabled. Only Direct declares REQUEST_INSTALL_PACKAGES and its update FileProvider. |
| Authentication | Existing Telegram/Google/Apple universal identity and Keystore-backed credential storage retained; no OAuth or user/account migrations in this branch. |
| Account deletion | Authenticated Android confirmation and public `/account-deletion` Google/Apple/Telegram verification are implemented in code. Deletion is queued for human processing; production backend/schema deployment, receipt, status and actual cleanup **not verified** by source alone. See `docs/ACCOUNT_DELETION_OPERATIONS.md`. |
| AI generated text | The Android assistant now offers a user-initiated report action under an AI answer. It opens the existing in-app feedback API with a short answer excerpt and optional description, not an external page. The existing backend sends reports to configured Telegram admins, labels AI complaints separately, and returns success only after at least one admin message is delivered. This is **not a durable moderation queue**; reports fail when no admin receiver/bot is configured. The Android assistant server prompt now explicitly refuses harmful/restricted requests, and a backend test verifies that this rule is forwarded to the model. **Prompt instructions do not constitute a validated moderation/filtering control.** Case triage, retention, restricted-content filtering (including adversarial prompts and model output) and moderation response **still require operational verification**. |
| Privacy | Public `/privacy` policy source updated to reflect selected AI photos, support screenshots, voice, notification tokens and payment/account notification purposes. Publishing the backend policy requires a later independent deployment. |

## Data Safety working inventory — confirm against the deployed data flows

**Do not copy this matrix directly into Play Console as a definitive declaration.** Verify exact providers, third-party SDK collection, data transfer, purposes, retention, encryption, and deletion semantics with real backend/configuration, privacy counsel, and the current Play Console form.

| Data / purpose | Collection or sharing evidence | Disclosure / verification task |
| --- | --- | --- |
| Google/Apple/Telegram account identities, linked provider subject hashes; optional email/name | Auth providers, `AndroidAuthApi`, backend identity flows | Account creation, security, app functionality. Determine exactly when optional email/name are collected and retained. |
| HSK level, lessons, attempts, course progress, XP, mistakes, streak, preferences | `CourseRepository` + authenticated APIs | App functionality, personalization and persistence; verify deletion scope. |
| Subscription, 3.0 unlock status and purchase-review status | `FeatureRepository`, account entitlements | Play reads state; Play does *not* offer a manual payment/receipt upload flow. Direct checkout still collects receipts outside Play; disclose if shared backend account data is used in Play. |
| Microphone and voice interactions | Android RECORD_AUDIO, voice engines, backend AI | Feature-initiated recording only. Verify what audio/transcripts are stored, retention, all AI/transcription subprocessors. |
| AI prompts, answers and user-selected pictures | Assistant chat/media API | User supplied content and media; processing can involve AI providers; verify server storage, retention and encryption in transit. |
| User-submitted bug/AI content reports, optional screenshots | `BugReportDialog`, `FeatureRepository.sendBugReport` | Sent only on explicit submission, screenshot optional. Verify moderator access, retention and removal. |
| Device push token, device/install state, notification preferences | Firebase Messaging/Android push APIs | Account/payment state and optional reminders; verify Firebase/provider data handling, opt-out and token deletion. |
| Support, diagnostics and infrastructure/access logs | Backend/platform logging | Actual deployed telemetry, IP address, identifiers, sharing and retention require inventory before declaration. |
| Website home/download aggregate campaign visits | `app/api/public_site.py`, public traffic metrics | Distinct from Android app data: aggregate visits without cookies/visitor IDs according to source; verify deployment. |

**No assertion of “no data collected”, “no data shared”, 100% deletion or approved legal compliance is justified by static code alone.** Data Safety also asks about secure transport and encryption, optional vs required data, eligible deletion mechanisms and any SDK collection.

## Mandatory external/manual release gates

- [ ] Run `Android CI` on the Play PR; verify **green** unit tests for both variants, lint, static checks, and **Android emulator** regression tests, including Play HSK 3.0 price/checkout absence and Pro/paid/provisional/free entitlements.
- [ ] Trigger `Android Play preflight` *manually* on this branch after secrets are present; verify key pin, signed direct APK, signed Play APK, package identity, no Play installer permission and signed AAB. The workflow only uploads the AAB as a **GitHub Actions artifact**, never to Play.
- [ ] Keep existing release signing secrets outside Git: do not change `com.pomp.hskai`, certificate, or signing key. Configure *Play App Signing with your existing key*. Compare SHA-256 on an already distributed, known-good direct APK and actual Play-signed installation. Confirm Play upload-key and app-signing-key distinctions.
- [ ] Check published direct APK `android/latest.json` and any Play Console builds: increment `versionCode` **above every installed/published predecessor** before the final release. This PR does not bump version numbers or distribute either build.
- [ ] Real-device install update test: install an actual signed direct APK, preserve account/local data, install an **actual Play-delivered test build** with higher `versionCode` and verify seamless update, linked identities, Pro, HSK 3.0, offline files, lessons, voice, permissions, Firebase notifications and no direct APK update prompts.
- [ ] Approve developer account and package in Play Console, declare app access/reviewer test account, provide privacy and deletion URLs, verified support contact, suitable content rating/target audience/ads disclosure and country availability.
- [ ] Independently review app content rights: bundled HSK textbooks, audio, illustrations, panda, icons, brand/logo, third-party licenses. Commercial redistribution rights are **not** established by repository presence.
- [ ] Check live `/privacy`, `/terms`, `/account-deletion`; deploy and test the deletion migration and operator queue. Confirm Google-only, Apple-only and Telegram-only users can request, track and complete deletion in the promised period; verify financial/legal record retention and data processor deletion.
- [ ] File Play Console Data Safety declaration from observed production flows and provider agreements, including AI, audio, photos, diagnostics, account, identity, notifications and support reports; review accuracy with legal/privacy owner.
- [ ] Test harmful-prompt rejection, model-output moderation and reporting an offensive AI answer end-to-end on a deployed backend. Review adversarial multilingual UZ/RU/TJ prompts and AI image/voice inputs. A system prompt and a delivered admin Telegram message **alone do not establish policy compliance**. https://support.google.com/googleplay/android-developer/answer/13985936
- [ ] Prepare app name, Play listing description **without claiming purchase support in Play**, localized UZ/RU/TJ store media, screenshots and privacy/legal/support details.
- [ ] Verify latest Play payments policy for your countries and consumption-only app, without offering external payment steering or sign-up payment prompts. Future Billing must be a separate implementation and reviewed before release.
- [ ] Fulfil personal developer account production-access testing requirements shown by your Play Console (potentially 12 opted-in closed testers for 14 continuous days); verify rather than assume this account's status.
- [ ] Confirm 2026 target SDK, 16 KB page-size/native library compatibility if bundled, Play AAB bundle validation and device catalog in Play Console. Check OAuth registered Play app-signing SHA fingerprints and live Google/Apple authentication.

## UI/UX follow-up using the repository skills

Reviewed `.agents/skills/hsk-ai-ui/SKILL.md`, `.agents/skills/webapp-testing/SKILL.md`, `docs/ui-ux-plan-2026-10-05.md` and the actual changed Kotlin Compose surfaces. This is an **Android native UI code review**, not a Playwright browser pass. `webapp-testing` applies to web surfaces and must not be used to claim native Android screenshots or runtime verification. `frontend-design` is referenced in `AGENTS.md` but is not stored under the repository's `.agents/skills` directory.

| Surface | Found UX risk | Bounded correction | Risk/verification |
| --- | --- | --- | --- |
| Mandatory HSK 3.0 course gate | Play's only way back to HSK 2.0 was a muted secondary text button, violating one-clear-primary-action guidance. | Make the existing HSK 2.0 return callback the primary 52dp action **only in Play**; direct continues to show its purchase primary and secondary return. | Low. Recheck Play locked N1-N3, direct purchase, narrow-width and large text. |
| HSK 3.0 promo/profile | Play no-purchase screens retained some purchase-suggestive headings. | Substitute neutral/existing access or course-version titles in Play, preserve direct wording and entitlements. | Low. Verify localized UZ/RU/TJ copy on-device. |
| AI answer report | Repeated safety affordance competed visually with tutoring answer and had no explicit 48dp touch target. | User-approved ChatGPT-style 48dp Copy, Share, and anchored `⋯` actions below **each individual answer**. The overflow contains a real Report action that preserves the specific answer ID/text; no inert vote buttons. UZ/RU/TJ accessible menu names are canonical Android resources. | Low/medium. Verify TalkBack labels, clipboard, share chooser, per-turn report popup, scroll/keyboard and screenshot. |
| AI report form | Reused generic bug-report heading and an unspecified primary submit height. | Reuse the canonical localized AI complaint title in AI context; keep bug heading for normal reports; 52dp minimum send CTA. | Low. Existing screenshot opt-in behavior and feedback API unchanged. |

Automated source contracts under `tests/test_android_hsk30_profile_books_contract.py` and `tests/test_android_bug_report_flow_contract.py` guard the specific UI properties. Device visual acceptance **pending**: small-screen portrait (320dp), 1.5x/2x font scale, dark/light mode, UZ/RU/TJ wrapping, TalkBack focus, report Dialog over Assistant sheet, return CTA accessibility, offline/error state, and screenshot comparison. The Android emulator/Compose CI is authoritative for actual native interaction; the signed Play preflight remains a separate gate.

## Safe handoff / limitations

This branch intentionally does **not** modify the live backend, payment ledgers, direct APK updater, direct payment/checkout, account migrations, keystore, Play Console or production build numbers. The signed preflight must be run with private secrets outside the repository. A passing static review or a green CI alone is **not** proof of production privacy compliance, signed update compatibility or Play approval.

## Main integration candidate verification — 2026-10-23

The owner authorized bringing branch head `c75b4d618b4950bb200dbcc94444c5a628f9ffb9` onto main `0074480807b1df731c7b912bca3380189b7c62e4`. An isolated worktree produced a clean three-way merge. Review covered the actual Kotlin, backend, resources and workflows; lesson JSON, grading, subscription grants, account ownership and database schema have no changes in this payload.

The review corrected a stale existing profile-book test expectation (`isNew` is already false in main), connected the three previously omitted Assistant/report/profile-book suites to Android CI, and added an API regression for the AI complaint label. The API regression mocks Telegram delivery; it does not establish live moderator receipt.

Executed on the combined candidate:

- All nine Android static guards passed; 39 canonical Android resource files and 56 generated UI artifacts are current, with zero stale artifacts.
- Backend/API, Assistant, public-site and localization tests: 116 passed and 108 subtests passed. Two asyncpg cleanup warnings were emitted; no test failures occurred.
- Direct JVM unit tests: 583 passed; Play JVM unit tests: 534 passed. Both lint tasks completed with zero fatal/errors; existing warnings remain.
- Both debug APKs and instrumentation APKs built. Both R8 release AABs built successfully and were verified unsigned.
- API 36 disposable emulator: Direct 36 passed and Play 28 passed, with zero failures/skips. These cover HSK 3.0 access/return behavior, server-granted access, payment-decision verification/deduplication, notification channel, profile promotions, voice back handling and Direct checkout lifecycle. The owner's signed-in emulator was not used.
- Changed Python modules compile and both edited workflow YAML files parse.

Signed Play preflight, actual Play-delivered update compatibility, live AI reporting/moderation and the external release gates above remain separate from this code integration. No APK distribution, Play submission or R2 publishing was performed by these checks. PR #193 carries the final main promotion and CI evidence.
