# Android Play language resources missing after an in-app language change

## Cause

Play 1.7.22 (53) allowed the default App Bundle language splits. Google Play
selects those resources using the device's system languages, while HSK AI's
picker and `AppLocale.wrap()` use the independently selected account/login
language. A missing Russian/Tajik Android resource falls back to the default
Uzbek string, even while API-backed lesson content uses the account language.
`androidResources.localeFilters` retains translations in the AAB but does not
ensure every translation is installed on each device. A direct APK contains all
the translations, explaining the channel difference.

Google documents this behavior and requires apps with independent language
pickers to disable language splits or download language resources on demand:
[Configure the base module — Handling language changes](https://developer.android.com/guide/app-bundle/configure-base#handling_language_changes).

## Verified reproduction

The downloaded signed Play AAB `hsk-ai-1.7.22-53-play-release.aab` has SHA-256
`a28eef5bc13ebdbbe893edaeb3d5c47ebba030af0b87e8209671fafb5e247743`.
Official bundletool 1.18.3, verified against the repository's pinned SHA-256,
showed `optimizations.splitsConfig: {}`: the default language split behavior.
`dump resources --resource=string/auth_welcome_greeting --values` showed all
three translations in that same AAB:

| Configuration | Value |
| --- | --- |
| Default | Xush kelibsiz |
| `ru` | Добро пожаловать |
| `tg` | Хуш омадед |

Generate a normal device-targeted set, without `--mode=universal`, from that AAB
with a device spec containing `supportedAbis: ["arm64-v8a"]`,
`supportedLocales: ["en-US"]`, `screenDensity: 320`, and `sdkVersion: 35`.
The generated set contained only:

```text
splits/base-arm64_v8a.apk
splits/base-master.apk
splits/base-xhdpi.apk
```

`aapt2 dump badging` on `base-master.apk` reported only `locales: '--_--'`.
`aapt2 dump resources` showed only the Uzbek default for
`string/auth_welcome_greeting`. The downloaded Direct 1.7.21 (52) APK reported
`locales: '--_--' 'ru' 'tg' 'uz'`.

This proves the resource loss in a Play-style installation. It does not by
itself establish which split APKs were installed on the photographed devices,
or explain the separate multilingual speech-transcription output.

## Fix and prevention

- Keep `android.bundle.language.enableSplit = false` so all supported UI
  translations are delivered together. Retain density/ABI optimizations.
- Verify the actual AAB's `LANGUAGE` split dimension is disabled, not merely
  that source XML translations or a universal APK contain the languages.
- Keep artifact-guard regression coverage for missing/default/enabled language
  splitting. Run the guard even when an AAB contains no native libraries.
- Test a normal device-targeted APK set for an unsupported system locale, then
  resolve representative Uzbek/Russian/Tajik strings from that installed set.
- A repaired AAB needs a new version code above 53 and Play distribution;
  changing the backend or direct APK does not repair existing Play installs.
  Do not reset the user's account language to the resource fallback.

The fix changes packaging only; it does not require lesson-content edits,
database migration, or changes to auth, grading or entitlement decisions.

## Verified repaired release artifact

The rebuilt 1.7.23 (54) Play AAB passed the actual artifact guard, including
all eight packaged native libraries' 16 KB checks. Its BundleConfig explicitly
contains `{"value":"LANGUAGE","negate":true}`. Repeating the same normal
en-US/ARM64/API-35 device-targeted generation produced a base-master APK whose
locales are `'--_--' 'ru' 'tg' 'uz'` and whose welcome resource contains the
Uzbek, Russian and Tajik values shown above. This directly reverses the v53
resource loss without a universal-APK override.

- Final release AAB SHA-256:
  `a1d28a242be10e7edee460bf5e1d1745eb45f373531318d60dd250b38c3b62a0`.
- Corresponding Play release APK SHA-256:
  `99536a5653f227305b3d36c19a3b1c23d873939b708861a41dbde9fa56b66fa9`.
- Both certificates match the existing repository-pinned release key; the AAB
  JAR signature verifies. All four Play release Firebase BuildConfig fields
  are nonempty; their values are not recorded here.

Artifact verification is not proof of Play Console publication or acceptance
on the photographed physical devices. Generated test split APKs use a local
debug signing key solely for emulator analysis; distribute the original
verified release-signed AAB through the existing Play release process.

## Installed upgrade regression

A fresh API 36 emulator reproduced the selected-RU/Uzbek-greeting mismatch
from the v53 en-US device APK set. Updating that installation to the v54
device APK set preserved the existing RU preference and rendered
`Добро пожаловать`. Switching to TJ rendered `Хуш омадед`; switching to UZ
rendered `Xush kelibsiz`. These were signed-out screens, with no learner
account created or modified. The device sets used a temporary debug signing
identity for local installation; the delivered AAB retains the release key.
