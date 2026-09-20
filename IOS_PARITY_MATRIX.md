# HSK AI iOS Parity Matrix

Source of truth: current native Android client + shared backend services.
Status legend: ✅ done · 🟡 in progress · ⬜ not started · ➖ intentionally platform-specific.

| Area | Android reference | Server contract | iOS status | iOS implementation |
|---|---|---|---|---|
| App shell | `MainActivity.kt` | — | 🟡 | SwiftUI app skeleton |
| Secure credentials | `SecureCredentialStore.kt` | shared auth | 🟡 | Keychain |
| Telegram link auth | `LinkScreen.kt`, `AndroidAuthApi.kt` | `/api/v3/android-auth/*` today | ⬜ | Native iOS auth transport |
| Bootstrap/session restore | `AuthRepository.kt` | native auth bootstrap | ⬜ | Auth session coordinator |
| Onboarding | `feature/onboarding/*` | Android course onboarding | ⬜ | SwiftUI onboarding |
| Notification primer | `NotificationPrimerScreen.kt` | preferences | ⬜ | UNUserNotificationCenter |
| Course map | `CourseScreen.kt` | `GET /api/v3/android/course/map` | ⬜ | Course feature |
| Cached-first course | `CourseRepository.kt` | same | ⬜ | URL/disk cache + revalidate |
| Today plan | `TodayPlanCard.kt` | map `today` block | ⬜ | Course feature |
| Daily goal/preferences | `StudySetup*` | study preferences | ⬜ | Profile/course settings |
| Lesson engine | `feature/lesson/*` | lesson + complete | ⬜ | Native SwiftUI cards |
| TTS/audio | `LessonAudioPlayer.kt`, `TtsCache.kt` | `/api/v3/android/tts` | ⬜ | AVPlayer + disk cache |
| Hanzi stroke | `StrokeAnimation.kt` | `/api/v3/android/stroke` | ⬜ | Native/embedded renderer |
| Practice | `PracticeScreen.kt` | practice start/complete | ⬜ | Practice feature |
| Mistakes | `MistakesScreen.kt` | mistakes + review APIs | ⬜ | Mistakes feature |
| Word drill | `WordDrillScreen.kt` | gate/words/report | ⬜ | Drill feature |
| Exams/tests | Android feature API | exams start/complete | ⬜ | Exam feature |
| Dictionary | `DictionaryScreen.kt` | dictionary + ETag | ⬜ | Dictionary feature/cache |
| Rating | `RatingScreen.kt` | leaderboard | ⬜ | Rating feature |
| Challenges | `ChallengeRunScreen.kt` | challenges APIs | ⬜ | Challenge flow |
| Referral | profile/rating flows | referral overview | ⬜ | Profile/rating |
| Profile | `ProfileScreen.kt` | profile/overview/preferences | ⬜ | Profile feature |
| Trial state | `AndroidFeatureApi.kt` | trial status/start | ⬜ | Access state |
| Subscription state | profile/limit flows | subscription overview | ⬜ | Read-only access state first |
| External checkout | Android `direct` flavor | external checkout | ➖ | Do not copy until iOS policy decision |
| Ads/unlock | `AdScreen.kt` | ad list/view + access ref | ⬜ | iOS channel |
| AI Voice | `feature/voice/*` | voice APIs | ⬜ | AVAudioRecorder/AVPlayer |
| Pronunciation | voice/practice flows | voice pronounce | ⬜ | Voice/practice |
| AI Assistant | `feature/assistant/*` | Android assistant API | ⬜ | Assistant feature |
| Study reminders | WorkManager notifications | preferences/local state | ⬜ | local notification scheduling |
| Android APK updater | direct flavor update code | Android release manifest | ➖ | Not applicable on iOS |
| Smart widget | Glance widget | local/shared state | ⬜ | WidgetKit |
| Deep links | `DeepLinkRouter.kt` | — | ⬜ | URL routing |
| UZ localization | `values/` | language preference | ⬜ | String Catalog |
| RU localization | `values-ru/` | language preference | ⬜ | String Catalog |
| TJ localization | `values-tg/` | language preference | ⬜ | String Catalog |
| Unit tests | Android JVM tests | — | ⬜ | XCTest |
| UI smoke tests | Android instrumentation | — | ⬜ | XCUITest |

## Backend cleanup rule

The table lists current Android-prefixed routes because that is the real deployed contract today. iOS must not impersonate Android. During Phase 1, expose iOS/native-mobile transport backed by the same shared services, then point the Swift client at that contract.

## Definition of parity

Parity means the same user/account sees the same authoritative progress, access state, XP/streak, mistakes, daily goal and challenge state across Mini App, Android and iOS. Pixel-identical UI is not required; native iOS interaction patterns are preferred where behavior stays equivalent.
