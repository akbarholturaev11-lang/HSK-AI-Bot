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

## Localisation

Backend language codes are `uz` / `ru` / `tj`. Android resource qualifiers are
`values` (Uzbek default), `values-ru` and `values-tg` — Tajik is ISO 639-1
`tg` on Android. `core/i18n/AppLanguage` owns that mapping; never send `tg` to
the API and never create a `values-tj` folder.
