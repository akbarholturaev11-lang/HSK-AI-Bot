# HSK AI iOS Parity Matrix

Source of truth: current native Android client + shared backend services.
Status legend: ✅ done · 🟡 in progress · ⬜ not started · ➖ intentionally platform-specific.

| Area | Android reference | Server contract | iOS status | iOS implementation |
|---|---|---|---|---|
| App shell | `MainActivity.kt` | — | ✅ | SwiftUI 5-tab shell |
| Secure credentials | `SecureCredentialStore.kt` | shared auth | ✅ | Keychain; access token RAM-only |
| Telegram link auth | `LinkScreen.kt`, `AndroidAuthApi.kt` | `/api/v3/ios-auth/*` | 🟡 | First-class iOS transport + Telegram flow; physical-device smoke pending |
| Bootstrap/session restore | `AuthRepository.kt` | `/api/v3/ios/bootstrap` | ✅ | RAM access token + rotating Keychain refresh token |
| Onboarding | `feature/onboarding/*` | `/api/v3/ios/course/onboarding` | 🟡 | Level/goal native flow done; remaining preferences/notification primer pending |
| Notification primer | `NotificationPrimerScreen.kt` | preferences | ✅ | Native permission request is user-triggered from Profile reminder control |
| Course map | `CourseScreen.kt` | `GET /api/v3/ios/course/map` | ✅ | Native XP/streak/league/today/unit rendering |
| Cached-first course | `CourseRepository.kt` | same | ✅ | Device/account-scoped disk cache + network revalidate |
| Today plan | `TodayPlanCard.kt` | map `today` block | 🟡 | Summary rendered; task routing/actions pending |
| Daily goal/preferences | `StudySetup*` | `/api/v3/ios/preferences/study` | ✅ | Native Profile daily minutes, XP goal and preferred-focus controls backed by shared preferences |
| Lesson engine | `feature/lesson/*` | iOS lesson + complete | ✅ | Glass SwiftUI engine; choice/builder/match/grammar/vocab/pronunciation + checkpoint exit-ticket |
| TTS/audio | `LessonAudioPlayer.kt`, `TtsCache.kt` | shared course audio | 🟡 | Mandarin playback wired; server-byte cache/interruption parity pending |
| Hanzi stroke | `StrokeAnimation.kt` | `/api/v3/android/stroke` | ⬜ | Native/embedded renderer |
| Practice | `PracticeScreen.kt` | `/api/v3/ios/practice/*` | ✅ | Native glass placement, mistakes, exams, recognition and pronunciation drills |
| Mistakes | `MistakesScreen.kt` | `/api/v3/ios/mistakes/*` | ✅ | Overview pagination + server-graded review + completion/result |
| Word drill | `WordDrillScreen.kt` | gate/words/report | ✅ | Adaptive server plan + local dictionary distractors + mastery reporting |
| Exams/tests | Android feature API | exams start/complete | ✅ | Native exam center/session/completion |
| Dictionary | `DictionaryScreen.kt` | dictionary + ETag | ✅ | Native glass dictionary + refresh/cache parity |
| Rating | `RatingScreen.kt` | `/api/v3/ios/rating/leaderboard` | ✅ | Native weekly league leaderboard and account stats |
| Challenges | `ChallengeRunScreen.kt` | `/api/v3/ios/challenges*` | ✅ | Native list/accept/decline/start/quiz/submit flow backed by shared service |
| Referral | profile/rating flows | `/api/v3/ios/referral/overview` | ✅ | Shared referral state + native ShareLink invite flow |
| Profile | `ProfileScreen.kt` | account + course state | ✅ | Native glass account/progress/access profile + editable shared study preferences |
| Trial state | `AndroidFeatureApi.kt` | `/api/v3/ios/subscription/trial*` | ✅ | Shared trial state/start surfaced in native Profile |
| Subscription state | profile/limit flows | `/api/v3/ios/subscription/overview` | ✅ | Read-only shared subscription/access state in native Profile |
| External checkout | Android `direct` flavor | external checkout | ➖ | Do not copy until iOS policy decision |
| Ads/unlock | `AdScreen.kt` | ad list/view + access ref | ⬜ | iOS channel |
| AI Voice | `feature/voice/*` | `/api/v3/ios/voice/*` | ✅ | Native role picker, typed/microphone turns, suggestions, TTS reply and session summary |
| Pronunciation | voice/practice flows | `/api/v3/ios/voice/pronounce` | ✅ | AVAudioRecorder + shared scoring + adaptive mastery reporting |
| AI Assistant | `feature/assistant/*` | Android assistant API | ⬜ | Assistant feature |
| Study reminders | WorkManager notifications | preferences/local state | ✅ | Daily local UNCalendarNotificationTrigger + persisted opt-in |
| Android APK updater | direct flavor update code | Android release manifest | ➖ | Not applicable on iOS |
| Smart widget | Glance widget | local/shared state | ⬜ | WidgetKit |
| Deep links | `DeepLinkRouter.kt` | — | ✅ | `pomp-hsk-ai://` native tab routing + XCTest coverage |
| UZ localization | `values/` | language preference | 🟡 | Auth/onboarding/course/Foundation/lesson/practice/mistakes strings present |
| RU localization | `values-ru/` | language preference | 🟡 | Auth/onboarding/course/Foundation/lesson/practice/mistakes strings present |
| TJ localization | `values-tg/` | language preference | 🟡 | Auth/onboarding/course/Foundation/lesson/practice/mistakes strings present |
| Unit tests | Android JVM tests | — | 🟡 | Network/auth/course/lesson/Foundation/practice/mistakes XCTest coverage; broader feature coverage pending |
| UI smoke tests | Android instrumentation | — | ⬜ | XCUITest |

## Backend cleanup rule

The table lists current Android-prefixed routes because that is the real deployed contract today. iOS must not impersonate Android. During Phase 1, expose iOS/native-mobile transport backed by the same shared services, then point the Swift client at that contract.

## Definition of parity

Parity means the same user/account sees the same authoritative progress, access state, XP/streak, mistakes, daily goal and challenge state across Mini App, Android and iOS. Pixel-identical UI is not required; native iOS interaction patterns are preferred where behavior stays equivalent.
