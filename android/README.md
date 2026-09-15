# Pomp HSK AI — Android client

Native Kotlin/Compose client of the existing HSK AI backend. Same Telegram
account, same subscription, same course progress as the bot, Mini App, macOS
and Windows clients. The Android client reuses the shared backend auth and
course contracts.

## One-time bootstrap: the Gradle wrapper

`gradlew`, `gradlew.bat` and `gradle/wrapper/gradle-wrapper.jar` **must be
committed** so that no build depends on a globally installed Gradle. Only
`gradle/wrapper/gradle-wrapper.properties` is written by hand; the other three
are produced by Gradle itself.

If they are missing, generate them once and commit them:

```bash
cd android
gradle wrapper --gradle-version 8.14.5
git add gradlew gradlew.bat gradle/wrapper/gradle-wrapper.jar
git commit -m "build(android): add the Gradle wrapper"
```

Any Gradle 8.x can generate them (Homebrew, SDKMAN, or the one bundled with
Android Studio). That bootstrap Gradle is used exactly once — afterwards every
build, local and CI, goes through `./gradlew`.

CI enforces this: the workflow fails if any wrapper file is absent, and
`gradle/actions/wrapper-validation` verifies the jar against Gradle's published
checksums so a committed binary cannot be swapped for a tampered one.

## Build and test

```bash
./gradlew testPlayDebugUnitTest   # JVM unit tests (Play build)
./gradlew lintPlayDebug           # Android Lint
./gradlew assemblePlayDebug       # debug APK
./gradlew bundlePlayRelease       # unsigned AAB unless signing is configured
```

Requires JDK 17 and `compileSdk 36` installed through the Android SDK Manager.

Five static checks run before Gradle in CI and take about a second each. They
exist because the Kotlin compiler needs the Android SDK, which is not always
available where these sources are edited:

```bash
python3 tools/check_interface_fakes.py     # a fake fell behind its interface
python3 tools/check_named_arguments.py     # a call passes a name that is gone
python3 tools/check_flavor_parity.py       # the flavours can no longer swap
python3 tools/check_strings_translated.py  # a string is missing uz, ru or tg
python3 tools/check_palette_matches_miniapp.py  # a colour drifted from the Mini App
```

## Distribution flavours

Two flavours ship the same product through different channels, and differ in
exactly one thing — whether the app may point the learner at a checkout
outside the app.

| Flavour  | Channel                    | External checkout |
|----------|----------------------------|-------------------|
| `play`   | Google Play                | no                |
| `direct` | APK, website, Telegram     | yes               |

Google Play forbids sending users out of the app to pay, so the `play` build
must not even contain the wording. That is why the difference is a source set
(`src/play`, `src/direct`) rather than a runtime flag: the strings and the
screens simply are not compiled into the build that must not have them. The
`play` build only ever *reads* limit and subscription status from the server.

Both flavours keep the same `applicationId`, so a learner who installed the
APK can be updated from Play later without reinstalling.

## Configuration

`gradle.properties` holds `POMP_API_ORIGIN`, the compile-time API origin. It
matches the desktop client's allowlisted origin and is a public value, not a
secret. Requests to any other host are rejected at runtime by
`OriginGuardInterceptor`.

## Release signing

Never committed. Provide either `android/keystore.properties`:

```properties
storeFile=/absolute/path/to/release.jks
storePassword=...
keyAlias=...
keyPassword=...
```

or the environment variables `POMP_ANDROID_KEYSTORE_FILE`,
`POMP_ANDROID_KEYSTORE_PASSWORD`, `POMP_ANDROID_KEY_ALIAS`,
`POMP_ANDROID_KEY_PASSWORD`.

When none are present the release build is produced unsigned, so a public
release stays fail-closed rather than silently shipping an unsignable bundle.

The keystore itself lives outside the repository (`~/.pomp-hskai/`) so that a
clean checkout or a `git clean -fdx` cannot destroy it. Back it up: every
future update — through the bot today, through Play later — must be signed with
the same key, and a direct-install APK signed by a different key will not
upgrade over the installed one.

## Distribution: the bot hands out the APK

There is no Play listing yet. The whole channel is the Telegram bot: the admin
uploads one signed `direct` release APK, Telegram keeps the bytes, and every
learner afterwards receives that same `file_id`. Nothing of ours serves the
download and there is no second copy to drift out of sync with the first.

```bash
cd android && ./gradlew assembleDirectRelease
# → app/build/outputs/apk/direct/release/hsk-ai-<version>-<code>-direct-release.apk
```

Then, in the bot: **Admin panel → 📱 Android ilova → ⬆️ Yangi APK yuklash**,
send the file as a *document*, confirm the version, publish. Learners reach it
with `/android` or the **📱 Android ilova** button in their profile.
**🚫 Tarqatishni to'xtatish** stops the handout immediately — one settings
write, no deploy.

The artifact name is load-bearing. `archivesBaseName` makes Gradle emit
`hsk-ai-<versionName>-<versionCode>-<flavour>-<buildType>.apk`, which is the
only place the version survives the trip through Telegram — the bot never opens
the APK. It is also how the upload step refuses a `play` or `debug` build:
both install perfectly and then strand whoever installed them, the first with
no way to pay and the second with an application id that no real release can
ever update.

Server side: `app/services/android_release_service.py` (the stored release),
`app/bot/handlers/admin_android.py` (publishing), `app/bot/handlers/android_app.py`
(handing it over). The published release lives in one `bot_settings` row, so
there is no migration and withdrawing a bad build is a single write.

## In-app updates, and why only one flavour has them

Android cannot update a sideloaded app silently. The system always shows its
own install confirmation, so the `direct` build's update is one tap and then
that dialog — never a background swap the way the Tauri desktop client does it.

The Play build has none of it. Google Play forbids an app it distributes from
updating itself by any other route, so this is a source set rather than a
runtime flag: `src/direct` holds the card, the downloader,
`REQUEST_INSTALL_PACKAGES` and the `FileProvider`, and `src/play` holds a
composable that renders nothing. The permission and the provider are simply
not in the Play APK — check with
`aapt2 dump badging <apk> | grep REQUEST_INSTALL_PACKAGES`.

How it works:

1. The profile screen asks `GET /api/v3/android-update/check?version_code=N`.
   The answer is 204 unless a newer build with a download link is published —
   no release, no link, no version code, or a caller already current all
   collapse to the same empty answer.
2. A card appears in the profile, and nowhere else: an update is not urgent
   enough to stand between someone and the lesson they opened the app for.
3. Tapping downloads the APK to `cacheDir/updates/update.apk`, checks the size
   against what the server announced, and opens the system installer.

Android refuses an update signed by a different key, so a swapped file cannot
replace the app with something else. The size check catches the one thing that
signature check cannot: a release uploaded to the bot and to storage as two
different builds.

Publishing an update is the same panel as the APK itself: **Admin panel → 📱
Android ilova → 🔗 Yangilanish havolasi**, pasting the https link to the APK in
storage. Publishing a new APK **clears** the previous link on purpose — a new
version must never be advertised with the old file behind it.

Every release must raise `versionCode` in `android/app/build.gradle.kts`.
Nothing compares version names; an update nobody's app can see is the failure
mode of forgetting.

## Localisation

Backend language codes are `uz` / `ru` / `tj`. Android resource qualifiers are
`values` (Uzbek default), `values-ru` and `values-tg` — Tajik is ISO 639-1
`tg` on Android. `core/i18n/AppLanguage` owns that mapping; never send `tg` to
the API and never create a `values-tj` folder.
