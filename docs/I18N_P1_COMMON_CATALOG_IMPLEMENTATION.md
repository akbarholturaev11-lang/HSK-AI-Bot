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
overwritten. Browser bundles expose only `window.HSKAI_COMMON_I18N`,
do not make requests, and are **not yet imported into active page
rendering**. The Bot artifact is an inert Python constant; it does not
alter existing `TEXTS` selection, user language or notification paths.

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
