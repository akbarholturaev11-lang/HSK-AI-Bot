# P1 — local-first common catalog generator (implementation started)

**State:** P1 build-time foundation **IN PROGRESS**, not all screens
localized. P0 source security and device QA are still unresolved.
This implementation is isolated in Draft PR #179; no runtime
translation switch or additional language has been activated.

## Canonical source and immutable legacy baseline

Edit only `localization/ui/uz/common.json`,
`localization/ui/ru/common.json` and
`localization/ui/tj/common.json` for these **11 reviewed existing
desktop copy keys**. Strings were copied verbatim from the present
`desktop/ui/js/i18n.js` catalog (Uzbek, Russian, Tajik);
they have **not** received new independent linguistic approval.
Chinese/pinyin, lesson questions, payment policy, Pro entitlement
and existing active translation dictionaries are untouched.

Translation names are namespaced (e.g. `navigation.course`,
`lesson.continue`, `auth.expires`). Backend locale remains `tj`,
Android XML resource qualifiers use `tg`; the existing explicit
`LanguageCodes.kt` adapter remains authoritative for application
language selection.

## One command, six packaged target artifacts

```bash
python scripts/i18n_build_local_catalogs.py --write
python scripts/i18n_build_local_catalogs.py --check
python -m unittest tests.test_i18n_build_local_catalogs
```

The stdlib-only generator does not fetch from Gemini, OpenAI, Railway,
or any other service. It emits deterministic bytes at:

| Platform | Local artifact |
| --- | --- |
| Android Uzbek default | `android/app/src/main/res/values/hsk_common_i18n.xml` |
| Android Russian | `android/app/src/main/res/values-ru/hsk_common_i18n.xml` |
| Android Tajik | `android/app/src/main/res/values-tg/hsk_common_i18n.xml` |
| Mini App | `app/static/course_v3_data/hsk-common-i18n.js` |
| Desktop (macOS/Windows shared code) | `desktop/ui/js/generated/hsk-common-i18n.js` |
| Python Bot/backend | `app/bot/generated/common_i18n.py` |

Android names use a dedicated `hsk_common_` namespace so that
legacy resources and direct/Play purchase strings cannot be
overwritten. Browser bundles expose `window.HSKAI_COMMON_I18N` and
make **no per-string requests**. The Bot artifact is an inert
Python constant until consumed through the separately namespaced
`t("common.navigation.course", lang=...)` adapter; existing
`TEXTS`, subscription/notifications and user language behavior
remain unchanged.

`--check` is CI read-only; a source edit requires rerunning
`--write` and committing updated platform files. Tests enforce
source key set equivalence, placeholder-name parity, JSON duplicate
key rejection, plain-text HTML avoidance, deterministic bytes, source
drift detection and independently parsable Android XML. `auth.expires`
demonstrates named `{time}` placeholder preservation; Android
resources are marked `formatted=false` until a reviewed adapter
handles named substitution.

## Required subsequent implementation before any release

Do **not** mistake these 11 messages for complete platform migration.
Expand namespace catalogs only from reviewed existing labels; validate
plural grammar, HTML-escaping, placeholders, accessibility strings,
Android flavor differences and dictionary/lesson content separately.
Wire code to generated assets screen-by-screen, preserving legacy
fallthrough only until visual/API parity tests and account/cache
access control pass. Source-only CI is not a device QA substitute.

The old `localization/baselines/source_git_blobs.json` records
pre-migration bytes intentionally; do not overwrite its expected
hashes to conceal UI regressions. When an original source is migrated,
record that reviewed change explicitly with old/new byte evidence and
preserve immutable lesson/answer baseline guards. No new locale is
enabled until all surfaces have been completed and reviewed.

## Initial client integration (branch-only, not a release)

The following code is now implemented on the isolated development
branch; **it is intentionally not deployed or merged to main**.

- **Android:** the shared `MainScaffold.kt` main navigation reads
  generated XML `hsk_common_navigation_{course,practice,rating,profile}`
  in all three resource languages. New texts match old
  `nav_{course,practice,rating,profile}` values byte-for-byte;
  direct and Play share the same code and no payment resource changed.
- **Desktop:** `desktop/ui/js/i18n.js` loads the bundled local
  common JS and reads 11 matching keys, retaining the legacy
  three-language catalog as fallback. The same Desktop JS handles
  macOS and Windows.
- **Mini App:** the course page includes one versioned, local static
  JS file; the rating heading reads `navigation.rating` from
  the generated copy with the exact prior string as a fallback.
  No lesson fetch or translation API call was added.
- **Bot/backend:** existing `app.bot.utils.i18n.t()` can read
  `common.<namespace.key>` from its local generated Python catalog,
  accepting Tajik `tj` and compatibility `tg`. Existing Bot
  keys are not rewritten or overridden. No handler has been
  reworded just to demonstrate the adapter.

P0's immutable source-blob reference has **not** been rewritten.
Intentional, narrowly reviewed UI changes are pinned by exact old
and new Git SHA-1 in
`localization/baselines/reviewed_ui_changes.json`. The P0 guard
continues to fail any unexpected source drift or modification to
any lesson/answer JSON. A source-code test also validates that the
four Android navigation translations are identical to legacy strings.

**Remaining:** migrate all other reviewed screens and UX states,
including Android Compose text, Mini App pages beyond the rating
heading, desktop-only UI, Bot replies, scheduled notifications,
phrases and lesson content, under explicit language/answer/cache
validation. Only after **code completion** will live staging,
WebView/device, Mac/Windows and Free/Trial/Pro QA be run.
