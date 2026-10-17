# HSK AI i18n — Plan / Schema / Execution Order

> **Canonical handoff for the local-first multilingual migration.**
> All future work on this feature must start here, then read
> `docs/I18N_LOCAL_FIRST_WORKPLAN.md`,
> `docs/I18N_MULTILANGUAGE_MIGRATION.md`, and
> `localization/surface_registry.json`.
>
> Status: **PREPARATION ONLY**. This file documents architecture and execution
> order; it does not mean client locales or course content have been migrated.

## 0. Where to resume

- Repository: `akbarholturaev11-lang/HSK-AI-Bot`.
- Isolated development branch: `codex/i18n-local-first-foundation-20261017`.
- Branch was cut from `main` at `160a51d69f3324e3162375213ec61b5587b19533`.
- **Do not silently merge into main during setup.** Any later merge requires
  the repository's testing rules and an explicit implementation scope.
- Baseline languages: `uz`, `ru`, `tj`; Android/BCP-47 Tajik is `tg`.
- Read `AGENTS.md`, `AI_RULES.md` and `PROJECT_MEMORY.md` before editing.
- **Next concrete action:** make the source inventory reliable, establish
  frozen baseline snapshots for all 3 existing languages, and run their tests.
  Do **not** start by activating a fourth language or replacing all HTML at once.

## 1. Architecture / schema

```text
                         AUTHORING / BUILD-TIME ONLY
                    GitHub repository: localization/
              ┌───────────────────────────────────────┐
              │ manifest.json                         │
              │ ui/{locale}/{namespace}.json           │
              │ content/{track}/{lesson_id}/source.json│
              │ content/{track}/{lesson_id}/{locale}.json
              │ notifications/{locale}.json            │
              │ validators + deterministic generators  │
              └──────────────────┬────────────────────┘
                                 │ validate + generate
              ┌──────────────────┼────────────────────┐
              ▼                  ▼                    ▼
        Android APK         Mini App web        Desktop Tauri
       /res/values*       versioned static      bundled JS/JSON
       packaged/local       cached assets      packaged/local
              │                  │                    │
              └──────────────────┼────────────────────┘
                                 ▼
                      Bot / backend templates
                       local Python catalogs
                   (server process, NOT per-string API)

  Course content is separate from UI text; entitlement, exam marking,
  progress, account-language sync and purchases remain server-authoritative.
```

The folders `ui/`, `content/`, `notifications/` in this diagram are the
**target layout**, not proof that those source files currently exist.
The active legacy dictionaries must continue to work until migration tests pass.

### What stays local

| Surface | UI delivery | Course translations |
| --- | --- | --- |
| Android | resources bundled into APK; no UI translation endpoint | retain authorized lesson snapshot/cache; future versioned locale overlays |
| Mini App | versioned, cacheable static JS/JSON, no per-string dynamic fetch | level/locale versioned data; protect access and avoid public Pro dump |
| Desktop Windows/macOS | translations bundled in the Tauri build | local authorized cache + compatible lesson data |
| Bot/backend | local Python catalog at deployment | server can render messages, enforce access and assessment rules |

**Cost invariant:** translating UI does not call Gemini, OpenAI, or another
translation service on every opening/label rendering. Downloading a static asset
once is still HTTP; cache revalidation and updates can still generate requests.
Do not claim full Mini App offline without independently testing WebView caching.

### Locale boundary

- UI display uses proper BCP-47 language tags (e.g. Tajik `tg`).
- Existing backend account and lesson API must keep `tj` until an explicit
  backward-compatible migration is implemented.
- `zh-Hans`/Chinese and pinyin are lesson source, not a replacement fallback.
- Establish one normalized fallback policy before changing live adapters;
  existing client fallbacks currently differ. Do not silently change user copy.

### Content safety / schema

- Keep stable lesson/card/option/answer IDs, Chinese, pinyin and correct-answer
  identity separate from translated prompts, meanings, feedback and word tiles.
- Any local overlay belongs to exactly one source lesson revision; reject
  mismatched bundle versions instead of silently pairing incompatible decks.
- `reverse_builder` uses locale-specific tokenization and distractors. Simply
  adding a locale key to old JSON does not make generated exercises correct.
- Existing public `/course_v3_data/{level}/lesson_*.json` routes need an
  exposure review before releasing new public language/course bundles.
- Do not embed private full exam answer keys, new paid/locked content or
  sensitive entitlement data into publicly fetchable language packs.
- Backend always decides Pro/free/trial access and checks answers/results.

## 2. Required execution order

### P0 — discovery and frozen baseline [NEXT; not completed]
1. Extend `scripts/i18n_inventory.py` beyond regex-only root HTML paths:
   generated sources, nested JS, Android Compose/strings/flavors,
   Desktop, Bot, notifications, phrases, lesson text and accessibility.
2. Classify each hit: active UI, learning content, admin-only, logs/IDs,
   dynamic text, and intentionally non-translatable.
3. Freeze the baseline for three locales; capture render/API fixtures for
   HSK 2.0 and 3.0 (including quiz and reverse-builder).
4. Record risks, missing strings, wrong-language fallbacks, file paths,
   placeholder shapes and cache ownership. Separate verified bugs from
   heuristic candidates.
5. Validate manifest aliases and the public course content exposure boundary.
**Exit:** complete reviewable file/locale/source coverage report and repeatable
baseline tests, not a 100%-coverage claim from a regex scan.

### P1 — catalog and validation [BLOCKED ON P0]
1. Define stable namespaced message keys, context/HTML-safety metadata,
   named placeholders, plurals, locale normalization and fallback rules.
2. Move a *small reviewed set* of common/error strings into source catalogs
   without deleting the existing runtime dictionaries.
3. Implement deterministic validation for completeness/placeholder parity,
   unsafe HTML, invalid JSON/XML and accidental language fallback.
4. Generate local target artifacts and verify byte-stable reruns.
**Exit:** change one source key, regenerate 4 local targets (Android,
Mini App, Desktop, Bot), prove no new runtime per-string API request.

### P2 — incremental UI adoption [BLOCKED ON P1]
1. Android: generated standard resources, then Kotlin-inline copy.
   Preserve `direct` and `play` payment strings and APK offline startup.
2. Mini App: adopt cached catalogs screen-by-screen; preserve deep links,
   bfcache, inline accessibility, quiz/paywall and error states.
3. Desktop: generated bundled i18n for paired macOS/Windows builds.
4. Bot/backend/notifications/public pages: local catalogs, with old API
   language fields and scheduled message fallback behavior preserved.
**Exit:** screenshots and baseline text parity for all 3 original languages,
mobile + browser + desktop flows tested.

### P3 — lesson localization overlays [BLOCKED ON P1, after safe UI slice]
1. Split authored source from translation overlays by stable ID/version.
2. Update course generators (including locale-specific reverse-builder tiles),
   dictionary/phrases and compatibility lesson-envelope emitters.
3. Test each lesson track, answer IDs, score, XP, progress and cache behavior.
4. Do not alter access consumption/prefetch logic; do not leak private exams.
**Exit:** old clients still read compatible lessons, new clients read the
validated local overlay, with no entitlement/answer regression.

### P4 — launch additional languages [BLOCKED UNTIL COMPLETE COVERAGE]
- Human review and 100% active-surface coverage for that language.
- UI, onboarding, Bot, subscriptions, errors, notifications, all active
  lessons, accessibility and offline states checked.
- RTL/formatting and CJK/Chinese source rendering tests when relevant.
- Enable in `manifest.json` **only after** green validation and release QA.

## 3. Tests and no-regression rules

- CI: source completeness, placeholders, deterministic generated artifacts,
  locale code aliases, client build/lint and source/overlay version checks.
- Mini App E2E: entry, `?lesson=5`, `?tab=course|mashq|profile|rating|voice`,
  quiz grade, XP save, localStorage fallback, subscription/paywall, bot return.
- Android: 3-language resources, language-switch cache, offline dictionary,
  onboarding, direct vs Play payment separation.
- Desktop: macOS/Windows parity and bundled copy, no UI text HTTP roundtrip.
- Content: all 7 active `hsk1-4/nhsk1-3` source tracks, stable lesson IDs,
  reverse-builder tokens, exam secrecy and no new public Pro dump.
- Security: do not modify auth, provisional Pro, trial, payment status,
  paid entitlement or user course counters as part of UI translation.

## 4. Status log / handoff protocol

Update this section **only when verified** by repo diff and tests.
Do not mark implementation complete based on the plan being written.

| Milestone | Status | Evidence |
| --- | --- | --- |
| Isolated branch from main | DONE | branch exists |
| Local-first architecture decision | DONE | plan + `PROJECT_MEMORY.md` |
| Surface source registry | INITIAL | `localization/surface_registry.json` |
| Full reviewed inventory/baselines (P0) | IN PROGRESS | supplemental source audit + git-blob baseline created; manual review, runtime screenshots and full scope still pending |
| Generated canonical catalogs + validators (P1) | NOT STARTED | pending |
| Platform runtime migrations (P2) | NOT STARTED | pending |
| Versioned lesson locale overlays (P3) | NOT STARTED | pending |
| Any new language enabled (P4) | NOT STARTED | prohibited until gates |

### P0 progress (evidence at the time of this update)

- Supplementary read-only scanner: `scripts/i18n_source_audit.py`
  (nested UI files, Python Bot copy, Android direct/play resource parity,
  JSON placeholders, file SHA-256 and registry anchors).
- Scanner regression tests: `tests/test_i18n_source_audit.py`.
- Source byte freeze: `localization/baselines/source_git_blobs.json`.
  It snapshots 746 current HSK 2.0/3.0 lesson JSON files plus
  8 legacy content files, 54 UI catalog source files
  and 3 generator/audit sources from baseline commit
  `160a51d69f3324e3162375213ec61b5587b19533`. This proves *file identity at baseline*, not semantic correctness.
- Verified P0 CI report: `docs/I18N_P0_AUDIT_FINDINGS.md` (source scanner
  2,681 paths; 70,813 recognized locale maps; 7,951 **review candidates**;
  Android 24 parity pairs; 811 frozen files matched; 0 baseline blockers).
  Automated detection is incomplete and does not verify translation quality.
- Frozen 3-language JSON source samples from lesson 1 of all 7 tracks:
  `localization/baselines/lesson_locale_samples.json`. The independent guard
  `scripts/i18n_lesson_samples.py` checks 7 lesson identities, Chinese titles,
  first-word Chinese/pinyin, selected translated subtitles and first-word
  meanings (21 locale-specific sample pairs) with a CI regression suite.
  **These are authored-source samples, not UI screenshots or rendered API output.**
- P0 remains **IN PROGRESS**. Do not activate a new language; screenshot,
  device/offline, manual translation and access-security review is outstanding.

### P0 second implementation slice (verified localization CI)

- Commit `fbd31e6898966b3a8ac41c3001bbd4bb3b4f3c77`: frozen 7-track
  `uz/ru/tj` source samples + guards, with lesson identity, Chinese, pinyin
  and sample text comparisons.
- Commit `80554cb4d337d56b8c761f401e3239398836fe61`: review queue classifier (provisional, not proof of
  actual translation defects), unit tests and CI JSON artifact.
- `docs/I18N_P0_AUDIT_FINDINGS.md` records the measured CI queue:
  7,951 candidates across 2,681 sources; 21 selected 3-language source
  sample pairs match exactly. See GitHub Actions run `38998775540`.
- Manual review and runtime screenshots remain pending; milestone **P0 remains
  IN PROGRESS**, and P1 runtime wiring is not authorized by this milestone.

### P0 third audit slice — 2026-10-17 (localization CI step verified; P0 still open)

- **Code changes (isolated branch only):**
  - `69105affaadf922a6ec4fb8d859436873de39ab1` and
    `14d66730941510b9f81e1913f08546a54bb8dab0`:
    new read-only `scripts/i18n_p0_contract_audit.py` plus
    `tests/test_i18n_p0_contract_audit.py`. Validate current `uz/ru/tj`
    and `tj -> tg` declarations, inspect the exact lesson route signature,
    and inspect all seven lesson source directories for **structural**
    answer-like fields. Output includes paths/counts only, never answer values.
  - `161c128b59b7ec0b2d41031bf5376f403ce45531`:
    add P0 guard to `.github/workflows/backend-ci.yml`, archive the
    `hsk-i18n-p0-contract.json` artifact.
  - `a383e8f86f82a95252d0dd825a57eaac5e8ac567`:
    fix Telegram message-vs-media-caption positional-argument classification
    and cover previously unscanned ready-phrase producer/source paths.
  - `30b43d142a92cafcab24b5ca55f6fe30a452f231` and
    `89c80ed1284525bfd083ff17bbb44ebabebf7129`:
    regression coverage for captions, file-name false positives and phrase inventory.
  - `eec01bb140c3861d4b26ffda80a8f409ca6c1715`:
    align `localization/surface_registry.json` patterns and verified source anchors.
- **Verification:** [GitHub Actions run 38999948668](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/38999948668)
  passed its `Test multilingual inventory and Mini App locale regressions` step,
  including the new script's 746-file P0 command. The full
  `Backend targeted tests / targeted-tests` job also **concluded SUCCESS**
  (GitHub Actions run 38999948668). This is **not** native-device testing,
  a complete security audit or approval to migrate clients.
  Latest automated source audit: **2,684 scanned files**, **71,125 detected
  locale maps**, **7,954 review candidates**, **0 parse/read errors**;
  frozen baseline **811 checked / 0 blockers**, seven-track source samples
  **0 deviations**. Review queue: 87 candidate-bearing source files, 75 shown.
- **Security observation:** `app/main.py` serves lesson JSON through
  `/course_v3_data/{level}/{filename}` without a handler-level dependency;
  global middleware, production access and paid-content exposure remain to be
  investigated. Do **not** change entitlement/payment in this P0 slice.
- **Fallback observation:** current Android `AppLanguage.DEFAULT = RUSSIAN`
  while `localization/manifest.json` has `default_locale = uz`. Do not silently
  align these until runtime language/account preference precedence is verified.
- **Open P0 gates:** manually classify remaining candidate strings, review
  complete public lesson payload/answer confidentiality, capture 3-language
  *rendered* UI and quiz snapshots, and test real WebView/native offline,
  Android direct/play, Desktop macOS/Windows and account-language fallback.
  The prior scanner totals (2,681 files / 7,951 candidates) are historical;
  updated figures appear above and in the CI artifact after phrase coverage
  expansion. **P1/P2/P3/P4 remain NOT STARTED**; no runtime clients or new
  languages were changed.

### P0 fourth implementation slice — 2026-10-17 (Android XML and lesson answer-shape guards)

- **New source-only audit:** `scripts/i18n_android_resource_audit.py`
  (commit `e0df6734a9a32a8ed7958a9286c7c74456051dda`)
  parses actual Android XML from each `main/direct/play` source set and checks
  existing `values-ru` / `values-tg` for matching string keys, printf and
  named placeholders, plural quantities, string-array lengths, and
  `formatted` flags. Reports only key names and token signatures — **never
  translated values**. `tests/test_i18n_android_resource_audit.py` added in
  `e4e207c93fe885c5af77d4a289a3b29c58c3567d`.
- **CI:** `f614bbc07487102a1ae43a41c53abba6172c990d` added
  `/tmp/hsk-i18n-android-xml-audit.json` to the localization audit artifact.
  [GitHub Actions 39000462115](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39000462115)
  **completed SUCCESS**; measured **24 XML comparison pairs, 0 review
  findings**. This is XML contract checking, not Android UI/runtime verification.
- **Existing lesson assessment shape audit enhanced:**
  `90f164e36d4e0e2c09a5599096cacdfb576eedfc` and regression tests
  `bf71e1ea37e0532ba6eed88cc97ecb2a815836ac` now report missing/
  invalid `correct_index` positions against same-card options, including
  current locale-keyed option lists. The archived P0 report measured
  **6,449 answer-like field occurrences** in 746 lesson files (6,445 in
  section cards, 4 elsewhere), with **0 option-index structural findings**.
  This is a significant public-content review target, not confirmed
  authorization bypass; global middleware and deployed access remain unknown.
  Do not publish answer values, change quiz grading, or mutate lesson JSON. In [CI 39000552111](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39000552111),
  localization-specific tests completed **SUCCESS**, and the overall
  `Backend targeted tests` job also completed **SUCCESS** (confirmed
  from GitHub Actions job result; no native/device test implied).
- **Manual source review:** account-deletion bot flow
  (`app/bot/handlers/account_deletion.py`) contains user-facing Uzbek-only
  confirmation and callback text without per-locale lookup; this is a
  confirmed source-level localization gap, unlike heuristic audit candidates.
  Runtime translation is **not** changed at P0. Existing static lesson JSON
  includes `correct_index` fields; `app/main.py` has a static lesson
  endpoint without handler-level auth. Inspect middleware, actual deployed
  access and course material before releasing any newly generated public
  translation packs.
- **Limitations:** XML audit does not validate string semantics, native
  formatting/lint, accessibility or real hardware; the lesson audit checks
  option-index *shape*, not answer correctness, stable ID grading or progress
  behavior. Device/WebView/desktop screenshots, live offline behavior, manual
  locale review, security/entitlement and remaining P0 review queue are
  **still open**. P0 IN PROGRESS; P1/P2/P3/P4 NOT STARTED.
- **Branch discipline:** changes are pushed only to
  `codex/i18n-local-first-foundation-20261017` / PR #179 Draft. Do not
  merge into `main` or reset `codex/local-ai` and `codex/cloud-ai`.

### P0 fifth audit slice — 2026-10-17 (Bot/Desktop catalogs and source fallback precedence)

- **Read-only catalog tool:** `scripts/i18n_catalog_contract_audit.py`
  (commit `fe1f6e8cfffa51daba3716a5c558fe6439f1728b`) parses Python
  Bot i18n dictionaries using `ast.literal_eval` (without importing
  application/runtime modules) and scans the existing Desktop JS catalog
  as source text. It compares the three legacy locales for missing keys,
  named placeholder signatures, and HTML tag-count differences. Also
  records Bot dictionary merge order, duplicate definitions and overrides.
  The matching regression suite was added in `2da4bec180e8ab700c188026a34a94496dd535a6`.
- **CI:** `988e690389ffdcd04ea13d46a2a8e350f6b9ba00` runs the audit
  and archives `hsk-i18n-catalog-contract-audit.json` along with previous
  P0 reports. [GitHub Actions run 39005975851](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39005975851)
  passed its localization-specific test step. Results were read directly
  from the archived CI artifact: Desktop messages **797 keys in each
  uz/ru/tj locale**, Bot effective `TEXTS` **253 keys each** and
  `COURSE_I18N` **92 keys each**; **0 missing keys, 0 named-placeholder
  mismatches and 0 HTML tag-count drift** in these catalogs. The nine
  individual Bot source tables are also internally parity-consistent.
- **Bot override evidence:** `ONBOARDING_TIP_I18N` replaces the existing
  `referral_trial_access_unlocked` `TEXTS` key for each of three
  languages (**3 source overrides**). This is visible in the code's
  `setdefault(...).update(...)` order; confirm intended policy before
  editing the translation source. No runtime changes made.
- **Fallback review added:** `7e7bf7220e504a9b0df58418c9e2d95dcd79afe7`
  and regression tests `9a10e479356af88243a0b3e52b696928c0ee53f9`
  report default source locale by surface. Existing fallbacks differ:
  Mini App course **ru**, Mini App subscription **uz**, Desktop **uz**,
  Bot **ru**, Android **ru**, proposed localization manifest **uz**.
  Mini App course can later replace its initial query-language choice with
  a valid account-language response. This is source-level evidence,
  **not** proof that a particular user sees incorrect copy.
  [CI run 39006142928](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39006142928)
  completed **SUCCESS** for the localization test step **and** the overall
  `Backend targeted tests` job. This does not certify client runtime,
  production access controls, or translation semantics.
- **Additional entitlement exposure source review:** `app/main.py`
  registers `/course_v3_data/{level}/{filename}` and returns
  `static_json_response(...)` without handler-level authentication or
  entitlement checks. The installed `BlockedUserApiMiddleware` in
  `app/services/blocked_user_guard.py` explicitly only guards `/api/`
  requests, so **that middleware does not protect the static lesson route**.
  JSON source includes `correct_index` fields. Other reverse proxies,
  deployment access and any real-world request outcomes are not verified;
  public paid-content/assessment exposure is a P0 security blocker for any
  new publicly readable locale pack. Do not modify active payment/auth/grading
  flows as part of this source-only audit.
- **P0 remains IN PROGRESS:** Mini App per-page dictionaries need
  authoritative key/placeholder classification and rendered screenshots;
  verify language/account state precedence on device, Telegram WebView
  offline static cache, Desktop Windows/macOS behavior, Bot callback language,
  static JSON entitlement/answer exposure, and manual review candidates.
  Do not enable new languages, rewrite live clients, or merge this PR.
  P1/P2/P3/P4 remain NOT STARTED.

### P0 sixth implementation slice — 2026-10-17 (Mini App page-local catalog inventory)

- **Source-only Mini App inventory:** `scripts/i18n_miniapp_catalog_audit.py`
  (commit `b68aa4d034f5bbdcb2ee78a0658726c472277a76`) with regression
  tests `tests/test_i18n_miniapp_catalog_audit.py`
  (`dc365513922c4df0fcfc403fe7b550307ccebf95`). It safely scans
  selected literal JS maps without rendering, executing JS, downloading
  locale resources, or changing any UI/lesson/payment logic. Nested objects,
  list entries, named placeholders, HTML tag counts, and duplicate
  literal properties produce reviewable key-path metadata, never translated
  text, payment data, quiz answers or user state.
- **CI:** `7107dff7f081032b1550fd34b244f8e75305860e` added read-only
  `hsk-i18n-miniapp-catalog-audit.json` to the existing backend P0 CI
  artifact. [Run 39006879202](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39006879202)
  completed SUCCESS for its initial four-catalog slice. First measured
  **339 leaf keys per locale** across course (86), course track-switcher
  (32), subscription (190), and onboarding (31), with no missing
  keys, placeholder drift, or HTML tag-count drift.
- **Expanded coverage:** `f8ee81f5de4beddc0cb71da2e00becc505f013d7`
  and regression maintenance
  `efb6f96e16889173595a753faa725dab8b7e4e0e` and
  `1db9483104f2fb3c581fd2f6441c6bac77868e1c`
  inspect **18 verified embedded dictionaries** spanning course,
  test center, mistakes, pronunciation, recognition, onboarding, voice,
  subscription, HSK dictionary and ready phrases. CI artifact from
  [run 39007054885](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39007054885):
  **578 leaf keys in each of uz/ru/tj**, 0 missing key paths,
  0 named placeholder mismatches, 0 HTML tag-count mismatches,
  0 value-type mismatches. HSK dictionary contains three
  `function(...)` value keys (`countAll`, `countResults`, `strokes`)
  in each language (9 source values) which require migration-specific
  handling; they are **not confirmed translation defects**.
- **Scanner precision:** `731ef349f0d9da8756f136edf82b3e376eb6baf3`,
  `5ec4c9b75e1c788a7c5584db3f75d676730cdb0e` and
  regression `1cc6c6d7d0dda76e4566fe35fb69b0e6eeea65c7`
  distinguish legacy formatter functions from ordinary dynamic expressions
  and test callable argument signatures without evaluating functions.
  [Run 39007233003](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39007233003)
  is the verification target; check final CI conclusion before declaring pass.
- **Registry:** `6155b669e83172af8c58a55ece71ad0d46bedcc4` adds
  missing course onboarding, AI voice, pronunciation, recognition,
  memorization and ready-phrases page anchors to the Mini App registry.
- **Known CI adjustment:** first expanded CI
  [run 39007010367](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39007010367)
  failed solely because the audit test incorrectly demanded more than 10
  keys in every catalog; some legitimate page catalogs have 2–7 keys.
  This overly strict test assertion was fixed in `1db94831`. The
  subsequent localization CI step passed in run 39007054885.
- **Legacy formatter verification:** CI artifact from
  [run 39007233003](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39007233003)
  confirms `countAll(n, level)`, `countResults(n)` and `strokes(n)`
  each appear in uz/ru/tj (9 source function entries) with **0 parameter
  signature mismatches**. This does not certify the output translations.
- **Residual Mini App hotspots:** `6a1023cf186e68593de5fd974bb9e02821615468`
  and regression `fbce628576dfaf2048ac5daf46c477430b80c550`
  add read-only counts and line locations to the Mini App report. In
  [run 39007408199](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39007408199),
  the localization test/audit step and the full `Backend targeted tests` job
  both completed **SUCCESS**. Across 11 selected
  HTML pages: **11 inline localized t/tr object calls, 126 LANG branches,
  54 JS locale-object declarations, 59 markup attribute candidates**.
  These are heuristic source pattern occurrences (not errors), may include
  already audited dictionaries, and do **not** prove 100% copy coverage.
  The concentration of 125 LANG branches in `course-v3.html` and nine
  inline locale calls in `course_v3_memorize.html` should be prioritized
  for manual classification before generated catalogs.
- **Still open:** these 18 selected literal dictionaries are not *all*
  Mini App UI copy. Other inline ternaries, runtime-composed strings,
  localized callback copy, HTML attributes, static asset caching, actual
  WebView language changes, device screenshots and linguistic QA are not
  certified. Existing static course JSON exposure, entitlement controls
  and course/quiz privacy remain review blockers.
  **P0 IN PROGRESS; P1/P2/P3/P4 NOT STARTED. No runtime changed.**

### P0 seventh implementation slice — 2026-10-17 (fast CI + future public pack leak guard)

- **CI coverage defect verified:** previously the `.github/workflows/backend-ci.yml`
  pull-request path filter included `app/**` and `tests/**` but **not**
  isolated changes to `localization/**`, `scripts/i18n_*.py`, Desktop UI
  or Android source resources. Such diffs could silently skip the P0 checks
  unless another tracked file also changed.
- **Isolated, cost-conscious mitigation:** commit
  `1fe5ca00b0776465a05af60f352ec942d34e4be5` adds
  `.github/workflows/i18n-p0.yml`, a separate Python 3.11 **stdlib-only**
  P0 workflow covering the above source paths plus app/static, bot,
  service and API code, without pip installation or production runtime
  dependencies. It keeps the existing full Backend targeted tests as a
  separate check; the fast workflow scans source snapshots and archives
  all read-only P0 JSON reports. It is triggered by pull requests and
  explicit manual dispatch, **not** by every push without an open PR.
- **Future publicly distributed bundle guard:** commits
  `922dafe2cbd59ccc17b78f636fe5550296027918` and
  `630e47fb6c883afa9998cc08afe98aadeda72523` add
  `scripts/i18n_public_bundle_guard.py` and
  `tests/test_i18n_public_bundle_guard.py`. This checks known **proposed**
  JSON output roots under `app/static/i18n`, `app/static/locales`,
  `app/static/course_v3_data/locales`,
  `localization/generated/web` and `localization/generated/miniapp`
  for key names used as private grading/assessment answers.
  Mixed-case variants are normalized; generic learner-facing UI labels
  `correct`, `answer`, `solution` are permitted.
  Source content values are NEVER emitted into reports.
  The guard fails its CI step on forbidden keys or unreadable JSON.
  **This is NOT a proof that existing public legacy lesson JSON is protected**,
  and does not inspect JS bundles or arbitrary unlisted output roots.
- **CI integration:** `210bcab9569256f3fc9529e93ac6bdca281507de`
  executes the new security unit tests and scans candidate output roots
  in the fast P0 workflow. [Fast CI 39008015762](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39008015762)
  completed **SUCCESS** for unit tests and read-only audits.
  Its `public-pack-security.json` artifact reports
  `status=NO_PACKS_YET`, `checked_json_packs=0`, `findings=[]`.
  This **must never be described as having validated actual generated
  language packs**. Synthetic regression fixtures prove the guard blocks
  `correct_index`, `answerKey`, malformed JSON and allows ordinary
  translated answer labels. The separate full backend CI for the last
  workflow edit should be independently checked before claiming it passed.
- **P0 unresolved security blockers:** existing public lesson
  `/course_v3_data/{level}/{filename}` route without a handler auth
  dependency, answer indices in legacy JSON, reverse-proxy/deployment
  behavior unverified. The new guard only prevents a subset of **future
  known-path JSON** leaks; it does NOT remediate this legacy exposure.
  Formal human review of the current entitlement boundary is still needed.
  No client runtime, payments, account data, lesson source or grading
  logic changed. P0 IN PROGRESS, P1/P2/P3/P4 NOT STARTED.

### P0 eighth implementation slice — 2026-10-17 (reviewed Mini App branches + CI deduplication)

- **First source-classified copy/logic slice:** `ec6ba1f58af3a202799ce6e44ff2766c1759db08`
  adds `localization/review/miniapp_course_hotspot_triage.json` with
  **21 specifically reviewed source line anchors** in
  `app/static/course-v3.html`. These are NOT 21 unique ternary
  expressions, and not exhaustive: prior broad source scan found 125
  `LANG` branch *occurrences* on that page. Grouped categories include:
  accessibility labels, loading/access state copy, review/error/assessment
  copy, lesson-example glosses, time/count formatting, profile text,
  locale adapter `tj -> tg`, Russian plural selection, and TTS
  language selection. The latter three are **runtime language logic,
  not plain translatable text**; they must not be mechanically replaced
  with static dictionary strings. No learner copy or app runtime was changed.
- **Regression:** `21c91aa2c147d796f61754cf5f5001de892b6b3a`
  aligned anchors to exact source lines. Test
  `tests/test_i18n_miniapp_hotspot_triage.py` added in
  `71d127c74b4fa515459bf94089afda4b29f5a9f3` enforces the
  21 reviewed line/anchor/category contract, catches source drift, and
  explicitly distinguishes copy classes from locale/grammar/TTS logic.
  `4681df1b5c66659cfc7fcf3e325f8d13e4d013dc` added this
  test to the dedicated P0 workflow.
  [Fast CI 39008283996](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39008283996)
  concluded **SUCCESS** with this new source triage test included.
- **Reduced superseded CI work:** `0b002834f27bae17fc49731d465cdf27fa252e48`
  and `e3244675cbc755b88401d756e2d1cad91d2aeaba` add scoped
  `concurrency` groups and `cancel-in-progress: true` to both
  Backend targeted tests and Local-first P0 workflows. New PR commits
  can cancel obsolete runs **of the same PR**, without cancelling
  checks of another PR. Such cancellation is expected, not a
  test failure. Re-check the latest, non-cancelled workflow conclusion
  before claiming it passed.
- **P0 remains open:** only 21 specifically named course source lines
  were classified in this slice; all remaining Mini App inline branches,
  other platform callbacks/attributes, manual translation quality,
  actual runtime locale/cache/device behavior, and public Pro/exam
  source entitlement safety are still awaiting review.
  P1/P2/P3/P4 NOT STARTED; neither `main` nor runtime client code
  was modified.

### P0 ninth implementation slice — 2026-10-17 (complete explicit course LANG-line triage + memorize inline review)

- **Source-level classification completed for one finite scanner rule:**
  `ca2ff5ca0db0205f9afc09e2277ad62136dcc2a5` extended
  `localization/review/miniapp_course_hotspot_triage.json` from
  **21 to 60 unique physical source lines**, capturing **all 125**
  occurrences of the specific `LANG ==/=== 'uz'|'ru'|'tj'`
  predicate pattern currently found in `app/static/course-v3.html`.
  `ab582405d2095a18e230473d38f2afa88fb4b081` also froze
  the matching predicate count for each reviewed line.
  Classification includes UI/error/assessment, XP/rating/referral,
  quiz/lesson text, accessibility, time/quantity formatting, plus
  non-text locale/grammar/TTS behavior. All 60 source anchors and
  125 predicate occurrences were checked against the current source.
  This is **not** a claim that all page strings, indirect locale maps,
  or each predicate's rendered outcome is human-approved.
- **Fail-closed source regression:** `5b839c701c604cf15c454af4bee7b266fc0ad758`
  revised `tests/test_i18n_miniapp_hotspot_triage.py` to compare
  the exact set of reviewed line numbers and per-line predicate counts
  against source scanning, and to reject new unreviewed explicit
  `LANG` predicates. Distinguishes brand/invariant and locale/grammar/
  TTS logic from translation copy. Avoid mechanical conversion of
  logical branches to mere strings.
- **Memorization inline strings reviewed separately:**
  `38124cee50345906abc58d88e23d49c6ffe1f07c` adds
  `localization/review/miniapp_memorize_inline_triage.json`
  classifying **all nine currently matched** `t({uz:...})` inline
  message expressions in `app/static/course_v3_memorize.html`.
  Eight are static learner-facing UI actions/status labels.
  The remaining question includes the canonical Chinese character
  `H` in each of three language variants. Future P1 migration must
  preserve that dynamic input using a named `{hanzi}` parameter,
  without modifying quiz distractors, card IDs or answer selection.
  `6cffbc9fc8950ceeebe5745b99abd5a430101583` added
  source-location and interpolation tests.
  `25e907237d83750cb834bc7766c711d9779edad7` runs these in
  the dedicated localization P0 CI.
- **Verified:** [fast P0 run 39008932889](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39008932889)
  completed **SUCCESS**, including source triage tests and all
  read-only P0 audits. Latest full Backend targeted CI conclusion
  must be checked independently; do not infer Android, Desktop or
  actual WebView tests from this source-only workflow.
- **Remaining P0:** the 60/125 and nine/9 scopes are only these two
  explicit code patterns, not full localization coverage. Remaining
  Mini App inline/object/HTML copy, Bot/notification manual review,
  actual 3-language rendered and offline UI, and existing public
  course JSON entitlement/answer-key exposure still block P0 closure.
  P1/P2/P3/P4 NOT STARTED; no production runtime, accounts, payments,
  lesson JSON or grading changed, and PR #179 remains Draft.

### P0 tenth implementation slice — 2026-10-17 (exam/lesson static-delivery threat boundary)

- **New AST-only audit:** `scripts/i18n_route_boundary_audit.py`
  (`f6c00f2f2ea5dfa78a58b25e61fa1f3d11322bbb`) inspects exactly three
  public course JSON route patterns in `app/main.py` plus
  `GUARDED_PATH_PREFIX` in `app/services/blocked_user_guard.py`.
  It emits only named paths, policy booleans and issue codes.
  No app import, database, live HTTP, lesson text or correct answers.
- **Security regressions:** `tests/test_i18n_route_boundary_audit.py`
  (`3044e2cf0149a5bcf7e9a997b854cd7ba9cac579`) verifies
  private exam route **404 without FileResponse**; detects unsafe
  route-policy relaxation and loss of seven-track/`lesson_*.json`
  validation. The current legacy lesson exposure is a **review blocker,
  not a test failure**, because production permissions and client
  compatibility are unverified. The top-level public curriculum JSON
  map route is a separate content-classification target.
- **CI:** `a1f00c63a4a43c38141ea0ca2393e7e9731e4f2a`
  runs the new tests and archives `static-route-security.json` under
  the isolated `Local-first localization P0 guards` job. The
  [run 39010834743](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39010834743)
  completed **SUCCESS** and its downloaded artifact was inspected:
  `status=SOURCE_REVIEW_REQUIRED`; lesson `serves_file=true`,
  `handler_dependency=false`, filename/track checks present,
  middleware only `/api/`; exam `explicit_404_return=true`,
  `serves_file=false`. Report contains two source-level review
  findings: existing public lesson JSON and top-level curriculum maps.
- **Client compatibility confirmed from source:** `app/static/course-v3.html`
  `lessonDataUrl`/`loadLessonData` call bare `fetch` on
  `/course_v3_data/{track}/lesson_*.json`, with N1 content revision
  and special `cache:"no-store"`; it does **not** pass
  `X-Telegram-Init-Data` on this fetch. The **exam** flow uses
  `/api/v3/exams/start` and `/complete` with initData separately.
  Do not put a new authentication requirement on the old static URL
  alone, as legacy Mini App lessons can break.
- **Proposed migration gate, not a runtime modification:**
  `docs/I18N_P0_LESSON_DELIVERY_SECURITY_DESIGN.md`
  (`c95a77c7e9d882bc6b06d4e3ecf00a9be575831a`) records a
  controlled QA identity/entitlement matrix, gated versioned lesson
  delivery, compatible client rollouts, private cache policy, and
  eventual closure of unintended public exposure. No API is yet
  implemented and **no live billing/access claims are made**.
- **Still blocking P0:** deployment/proxy and true anonymous Free/Pro
  fetch experiments, older native/desktop client audit, UI/offline
  screenshot evidence, translation QA and entitlement-controlled
  lesson bundle design. P1/P2/P3/P4 NOT STARTED. No runtime, grading,
  payments, lesson data or user state changed. PR #179 Draft.

### P0 tenth follow-up — seven public curriculum maps classified by structure

- **Map shape guard:** `2ce1dccfbf56fbc757ac6dcb2090537b853e3c1a`
  extends `scripts/i18n_route_boundary_audit.py` to inspect seven
  current public top-level curriculum maps without emitting their text.
  It checks that `units[].lessons[]` remain navigable and rejects any
  newly added private assessment answer keys in these source maps.
  `63225c21c5d7235b61e5df4e7b77eebf11c85802` adds synthetic leak
  tests plus existing-source regression.
- **Verified in source and CI artifact:** [fast P0 run 39011261505](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39011261505)
  completed **SUCCESS** and the actual `static-route-security.json`
  was inspected. All seven track maps held **746 lesson-navigation
  entries** (hsk1=63, hsk2=72, hsk3=109, hsk4=181,
  nhsk1=103, nhsk2=73, nhsk3=145) and **0 private assessment key
  occurrences**. This narrows the source risk: these top-level map
  files are not the same as the underlying 746 lesson JSON bodies,
  which do contain practice answer indexes.
- **Not established:** maps still include translatable metadata,
  lesson structure and baseline progress fields; downstream API
  overlays and actual user-facing Pro semantics need independent review.
  A map with zero answer keys is **not automatically safe to publish
  every paid lesson/translation**. The legacy direct lesson route
  remains P0's priority entitlement/privacy blocker.
- **Assessment-key naming variants:** `1a414f59301c12f31f6520544b5392e090af73f4`
  normalizes camelCase, snake_case and kebab-case assessment field names,
  and `b9890cb22591ee08c78c8031824ea522176c88d6` adds regression
  fixtures containing `correctIndex`/`answer-key` variants.
  [Fast P0 run 39011475458](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39011475458)
  concluded **SUCCESS**. This hardens future public map leak detection;
  current source maps still have no matching assessment keys.
- No production behavior, published assets, lesson data, source
  translations, progress or payments changed. P0 IN PROGRESS.

### P0 eleventh implementation slice — 2026-10-17 (Android/Desktop/Mini App transport matrix)

- **Cross-client source audit:** `scripts/i18n_client_lesson_compat_audit.py`
  (`d6408b7fc8c3cbabfe0162d4d649496d2fcac992`) compares the
  present three clients and server delivery paths without importing
  application modules, using native devices, accessing tokens, or making
  HTTP requests. `tests/test_i18n_client_lesson_compat_audit.py`
  (`230db4bcb0d7f03ae967ebc211aa467fef757628`) exercises
  fail-closed mutations of the native endpoint/auth contracts and
  Android offline cache boundary. CI integration
  `5de7fe968615a390ea0ba970778beb5536a1e206` archives
  `native-lesson-compatibility.json`.
- **Verified code distinction:** the Mini App `lessonDataUrl()` currently
  fetches a raw unauthenticated `/course_v3_data/{level}/lesson_*.json`
  URL; native Android Retrofit instead calls
  `api/v3/android/course/lesson/{lessonOrder}` with Bearer auth and
  Android service inherits `DesktopCourseService.lesson()`.
  Rust/Tauri Desktop UI calls `desktop_lesson_data` through the
  bridge and `authenticated_get_json` with Bearer auth. The
  **native backend** checks sequential unlock, applies
  `LessonAccessService.status(..., consume=True)`, and marks lesson
  API replies `Cache-Control: no-store`. These are source contracts,
  NOT proof of deployed Free/Trial/Pro behavior.
- **Android offline safety observed:** after a successful authorized
  lesson reply the Room `LessonCacheEntity` stores its validated
  envelope. Cached fallback is only used for network `Offline` or
  `Timeout`, never a server-authored 401/403/limit denial; Room DAO
  has a logout clear operation. Play/direct share the main-source
  lesson transport; released APK versions and device behavior not
  yet proven.
- **Validation:** `14f57acb033f2bfba174b7f40b4d5b41976e4a41`
  corrected the scanner's N1 revision and Offline/Timeout source
  patterns; `3202231e4b9ee07bcca189b67c77c46896b178fd`
  adjusted its deliberately broken-cache negative fixture. An
  earlier CI failed this *fixture* assertion only, not the product
  runtime; [P0 run 39012530053](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39012530053)
  subsequently completed **SUCCESS** including the new audit and
  unit tests. Its source-only report must be kept separate from
  live HTTP/QA claims.
- **Updated migration design:** `docs/I18N_P0_LESSON_DELIVERY_SECURITY_DESIGN.md`
  (`01eaa17c1d51d47f72b7bd99a5f296ccddf5d20a`) records the
  existing authenticated native code paths and Android cache policy,
  narrows the immediate remediation priority to Mini App, and adds
  explicit anonymous/Free/Trial/Pro/blocked/expired/offline QA matrix.
  No production code, old URL routing, Pro entitlement rules,
  TTS, lesson content, Play checkout or progress changed.
- **Cache reset chain expanded:** `b4231e2229f301c8a0ef4b0975bb600a2bbaa07d`
  extended native checks to `HskAiApplication.kt` and
  `MainActivity.kt`: explicit Android sign-out and
  `AuthState.Unauthenticated` both invoke
  `app.clearLocalData()`, which calls
  `courseRepository.clearCache()` and both map/lesson DAO
  clear methods. A deliberately removed logout call is a
  regression test fixture (`6949c4463646ccd570a847af60593edf3e453915`,
  corrected in `c3c18c5809d7469ef43fb722e622c6fe1af3b11d`).
  The first fixture did not actually alter its target and caused
  a P0 test failure; the corrected
  [fast P0 run 39012928501](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39012928501)
  completed **SUCCESS**. This is source-level regression,
  not proof of rapid real-device multi-account logout behavior.
  [Security design](../docs/I18N_P0_LESSON_DELIVERY_SECURITY_DESIGN.md)
  now includes an A->B account cache isolation QA case.
- **P0 remains IN PROGRESS:** audit all potentially released client
  variants, execute access matrix against a controlled staging
  deployment, inspect edge/CDN policy and mixed-account caches,
  and prove locale/offline behavior on devices. Legacy public
  lesson JSON exposure remains a blocker. P1/P2/P3/P4 NOT STARTED,
  branch only and Draft PR #179 unchanged.

### P0 twelfth implementation slice — 2026-10-17 (Mini App non-consuming fetch call sites)

- **New concrete migration blocker:** Mini App's `loadLessonData()` is
  **not** solely a user-intended paid lesson request. There are six
  direct caller expressions in `app/static/course-v3.html`:
  (1) `primeSalesValueContent` HSK1 lesson 3 paywall preview;
  (2) `warmLessonPreviewAudio` pre-Continue TTS preparation;
  (3) `prefetchNearbyLessons` idle current/next lesson prefetch;
  (4) `startSkipTest` client-generated skip material;
  (5) `startFoundationFromMap` Starter 0 prerequisite;
  (6) `startLesson` after `reserveLessonStart(l)`.
  A wholesale replacement with `consume=True` authorized GET would
  spend Free/Trial quotas for background activity and could break
  skip-test/foundation/sales flows.
- **Source intent registry:** `3febda7c1807dced841a02bc57a1bddaa7a87db0`
  created `localization/review/miniapp_lesson_fetch_calls.json`
  with all six exact source lines, intent/policy distinctions and
  additional indirect entrypoints (warm preview, idle prefetch,
  paywall) for a future reviewed migration. No texts, quiz answers
  or account details are copied into the registry.
- **Fail-closed regression audit:** `cced9eb30596ea9f035d01dd41c2a80c7ebea46a`
  adds `scripts/i18n_miniapp_lesson_fetch_audit.py`.
  `1889e5356c2b85c772ea6184a4633f3ae27a5d63` adds tests
  checking six source anchors, missing/new prefetch caller,
  lesson reservation order and source-line drift; `8aba458faad19a1beb09207d2e3f0e885570c7d5`
  integrates the stdlib-only test/audit into dedicated P0 CI
  (`miniapp-fetch-intents.json` artifact).
  [P0 CI 39013692471](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39013692471)
  **SUCCESS** for this full source/test slice.
- **Cache identity review:** source `LESSON_DATA_CACHE` and
  `lessonDataKey()` are level/order keyed in page memory, and
  persistent `lessonResumeKey()` has no `localUserScope()`,
  while `lessonMasteryKey()` does. This is NOT proof of cross-account
  exposure. Test WebView same-device A->B login, in-flight response
  expiry, bfcache and revision invalidation before any protected
  lesson caching.
- **Security design updated:** `b9be3b0727e976efca6fbccab36a0ce2d633dfb2`
  appended typed public-safe preview, non-consuming authorized
  read, foundation, skip-test and deliberately started lesson policy
  recommendations to
  `docs/I18N_P0_LESSON_DELIVERY_SECURITY_DESIGN.md`.
  This is only a design: **no new APIs**, no client loader rewrite,
  no quota, payment, lesson, test, progress or TTS behavior changed.
- **Next release blocker:** obtain QA account-state, background-consumption
  and old installed client evidence before approving a secure Mini App
  content route. P0 IN PROGRESS, P1/P2/P3/P4 NOT STARTED, PR Draft.
  
### P0 thirteenth implementation slice — 2026-10-17 (staging access QA harness; OFFLINE by default)

- **Explicit staging-only anonymous-route probe:** `scripts/i18n_staging_anon_route_probe.py`
  (commit `fcd4fc8b7cec31f5998129f9437251f799e0fce5`) plans **15**
  anonymous GET status checks: seven `/course_v3_data/<level>.json`
  maps, seven `lesson_01.json` paths and one private exam URL.
  It **never reads response bodies** or emits learner texts, secrets
  or quiz answers. Production/unconfirmed/insecure hosts are refused,
  redirects are blocked, and `--execute` with exact HTTPS staging host
  confirmation is required before any HTTP requests.
- **Regression safety:** `tests/test_i18n_staging_anon_route_probe.py`
  (commit `a7debfec81a46b945202b709cf6f8f2b67cf5566`) covers the
  default zero-request behavior, production host rejection, body-free
  status-only checks, absence of authorization headers, exam 404
  regression signaling and transport failure classification.
- **CI is OFFLINE:** `2c791067a0aeb0c2a2a2b9a3f1da2a9a574e4a8c`
  adds these tests and archives the dry-run plan; it NEVER executes
  the real network probe. [P0 run 39014283200](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39014283200)
  completed **SUCCESS** and its artifact ZIP was inspected:
  `status=NOT_EXECUTED_STAGING_TARGET_REQUIRED`,
  `performed_requests=0`, `planned_requests=15`, `findings=[]`.
  **No real staging HTTP result is claimed; zero findings means
  only that the plan did not run.**
- **QA runbook:** `docs/I18N_P0_STAGING_ACCESS_RUNBOOK.md`
  (commit `43cb73e5daa303393c04f1bd24166dfa57f5e0d9`)
  describes controlled staging execution with disposable test users,
  anonymous/public route checks, Free/Trial/Pro/pending/blocked
  entitlement scenarios, non-consuming background fetches and
  Mini App/Android account A→B offline cache isolation.
- **Railway read-only environment discovery:** `patient-friendship`
  has staging and production environments. **Staging has ONLY a
  successful `Postgres-Iy93` database; it has NO deployed HSK AI
  backend service and NO HTTPS app domain.** Production separately
  runs HSK AI from the GitHub `main` branch and PostgreSQL.
  The source-only probe therefore remains unexecuted; do not
  redirect tests to the production service. This was read-only
  Railway inspection, with no secrets accessed or deployment changed.
  Operator approval is required for any paid/cost-bearing staging
  backend creation, isolated database wiring and QA credentials.
  The discovery is recorded in
  `docs/I18N_P0_STAGING_ACCESS_RUNBOOK.md`
  (commit `df31c4f6538257885471dad4805f8fab6d89ecb5`).
- **Still blocked:** no usable staging application server and
  no disposable QA users were selected/authorized. No live HTTP requests, lesson consumption,
  source runtime changes, login sessions, secrets or device QA.
  P0 IN PROGRESS, P1/P2/P3/P4 NOT STARTED; PR #179 Draft.

### P0 fourteenth slice — 2026-10-17 (isolated Railway staging QA boot)

- **Staging-only startup entrypoint:** `app/staging_qa.py` initially added
  in `df83951c06513db4a4dc843fa95008a4eed7c0ec` and subsequently
  corrected in `9eaf2da37e676689f8462bf8253047d329e7dfe4`.
  This imports the production FastAPI route graph but substitutes a QA
  lifespan which **does not start Telegram polling, reminder/notification
  schedulers, campaign sends, lesson seeding or cleanup background
  workers**. It uses a deliberately fake Bot token, not the real bot.
  The normal `app.main:app` startup remains unchanged.
- **Fail-closed environment guard:** `scripts/i18n_staging_boot_guard.py`
  (`655dc71d52481a89960e1ce8ee82265ba058efcf`) refuses non-staging
  Railway environments, inherited real BOT_TOKEN, paid AI credentials,
  wrong DB host and missing QA-mode confirmation. Driver-only
  PostgreSQL URL normalization (`87a8a0902347bbbf9a2db1096953a4aa451563cd`)
  adapts Railway's native Postgres URL to SQLAlchemy asyncpg without
  altering the host/user/database. `tests/test_i18n_staging_boot_guard.py`
  (`41272648cdef4efbc7495ddf8466d42d8241dd6e`, extended in
  `e08ef58a99a6e1fcef6876fddbc4aff3c14caa8e`) exercises guard
  failures and source invariants.
- **CI validation:** `9fb670839c88aa2c76ed244c1202e09f4acde20d`
  integrates guard tests into fast P0 CI. `f03969f6516d0dc99d030dba91ef5b02a0ce830b`
  adds full-dependency ASGI import smoke-test to Backend targeted CI
  without database connection or lifespan startup. For that commit,
  [P0 CI 39016160568](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39016160568)
  and [Backend CI 39016160563](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39016160563)
  completed **SUCCESS**; ASGI import smoke passed.
- **Railway isolation:** staging project `patient-friendship` contains
  independent staging PostgreSQL `Postgres-Iy93`. New dedicated service
  `hsk-ai-p0-qa` was staged with source
  `akbarholturaev11-lang/HSK-AI-Bot`, PR #179 branch pinned to
  `f03969f6516d0dc99d030dba91ef5b02a0ce830b`. Explicit
  service variables reference **only** staging Postgres, disable paid
  AI/push/OAuth and use an inert bot username; no production
  secrets were copied. Startup command points to `app.staging_qa:app`,
  sleep mode enabled, `/health` probe configured. Staged changes were
  reviewed as creation-only, then committed to staging (not production).
- **Deployment error recovered:** the first staging startup failed
  because `PUBLIC_SITE_URL` and `MINI_APP_BASE_URL` were blank,
  violating public-site canonical HTTPS URL validation. The staging-only
  values were first set to an inert .invalid origin and then to
  `https://hsk-ai-p0-qa-staging.up.railway.app`. No production
  variable was changed.
- **Safer fake token:** `094d9a69592a58a17a089ba3f406a0ad173a93e2`
  replaces a predictable dummy Telegram token with a **cryptographically
  random per-start fake token** in the staging-only entrypoint.
  `c73ee00891e7be6fa8eca59d5b54e29c24c36fe4` updates tests.
  [Fast P0 CI 39016794297](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39016794297)
  completed **SUCCESS**; Backend import smoke for the randomized
  token also completed SUCCESS in run 39016794371.
- **Actual Railway staging outcome:** isolated service
  `hsk-ai-p0-qa`, staging Postgres `Postgres-Iy93`, Railway-managed
  domain `https://hsk-ai-p0-qa-staging.up.railway.app`.
  The latest staging deployment `cf4e66c5-8134-40e5-9f78-68b07b26b244`
  builds exactly commit `c73ee00891e7be6fa8eca59d5b54e29c24c36fe4`
  and reports **SUCCESS / Online**. Railway startup logs confirm
  `Application startup complete` and internal `GET /health`
  **200 OK**. `app.staging_qa:app` skips Telegram polling/schedulers,
  uses isolated Postgres and no production Bot/AI secrets.
- **Still blocking P0:** no external anonymous HTTP route scan was
  executed (current execution environment cannot resolve the staging
  domain); no disposable Free/Trial/Pro/blocked auth fixtures or
  Mini App/Android WebView QA yet. User-authorized staging compute is
  now running and may incur Railway usage charges; sleep is enabled.
  P0 stays IN PROGRESS, P1/P2/P3/P4 NOT STARTED.
  No production or main changes; PR #179 remains Draft.

### P0 fifteenth implementation slice — 2026-10-17 (live anonymous staging boundary)

- **Status-only staging proof:** [one-shot run 39017607269](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39017607269)
  reached staging and recorded **15 GET-status checks**: seven
  static navigation maps returned HTTP 206, seven direct lesson JSONs
  returned HTTP 206, and the private exam route returned HTTP 404.
  The artifact was downloaded and parsed; zero response bodies,
  tokens, payments or answer keys were read.
- **Expanded native authorization contrast:** commit
  `b9394c537947ebca7c05ab606a05f8538ab9606a`
  adds anonymous `GET /api/v3/android/course/lesson/1` and
  `GET /api/v3/desktop/course/lesson/1` probes; commit
  `8f8fa41a000ebe18e09e8e86d5ca0d37d2c51fb3`
  updates offline negative tests and expected counts to **17**.
  `09dc71d3c13bb827575b459219de3bf3af339622`
  re-ran the exact staging-only status probe through the path-restricted
  GitHub Action, with no production domains, API credentials or bodies.
- **Measured expanded outcome:** [staging CI 39017842475](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39017842475)
  **SUCCESS**, status-only JSON artifact ID `12095930491`
  independently parsed. **17 requests, 7/7 legacy lesson 206,
  7/7 navigation maps 206, Android API 401, Desktop API 401,
  private exam probe 404, exactly seven legacy access review findings.**
  This confirms **staging** anonymous legacy partial-content exposure
  and denial of these two sampled native anonymous API calls.
  A response from a first lesson is not proof of live paid bypass.
- **Evidence and reporting:** `localization/review/staging_anonymous_http_results_20261017.json`
  initially created at `da9c27387a3778cfbd0c8832b9c8e7e2b21f8983`
  and updated to the 17-route result at
  `6bbd705f2f03d55bcfa24400bdde3229afa745ff`.
  `docs/I18N_P0_STAGING_ACCESS_RUNBOOK.md` updated in
  `d26e8e241e422d4d4bea8993845e0742d2af1493`,
  `docs/I18N_P0_AUDIT_FINDINGS.md` in
  `c05978c552b3e7a1d65759b6ac61fda2a5b8203d`.
  These replace outdated "staging unreachable" claims with
  measured HTTP evidence and explicit untested dimensions.
- **P0 blockers remain:** anonymous and authorized *premium lesson*
  payload classification; disposable Free/Trial/Pro/blocked users;
  quiz/grading and quota policy; Mini App preview/warmup/prefetch
  no-consume rules; cache isolation; old native clients; edge/CDN.
  Only plan an authenticated migration with verified backwards
  compatibility, do not blindly lock the public route, and **do not
  merge runtime or payment changes to main**. P0 IN PROGRESS,
  P1-P4 NOT STARTED. Staging service and production untouched in
  this slice.

### P0 sixteenth slice — 2026-10-17 (live late-course anonymous HTTP sampling)

- **Source verified seven actual late-course filenames:** `hsk1/lesson_63.json`,
  `hsk2/lesson_72.json`, `hsk3/lesson_109.json`,
  `hsk4/lesson_181.json`, `nhsk1/lesson_103.json`,
  `nhsk2/lesson_73.json`, `nhsk3/lesson_145.json`.
  Every corresponding GitHub track directory has consecutive
  `lesson_N.json` files; this is *source existence* only.
- **24-status audit implementation:** `ca9694e5da5c53a042a72191b6d69503827b8157`
  added exact last-lesson `late_legacy_lesson` cases and a separate
  `anonymous_late_lesson_success_count` report field.
  `e0726c169ae827645cf9e0be0821ad2d249de257` expanded the
  offline/negative tests; fast P0 CI passed on that source revision.
  `faa9629c422404d88da1ba05ffc12e9f3d1692c2`
  explicitly re-ran the restricted staging-only GitHub workflow.
- **Confirmed actual staging statuses:** [run 39018359239](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39018359239)
  completed **SUCCESS**. Its archived JSON artifact `12095103604`
  was downloaded and independently parsed: **24 anonymous GET
  status-only requests**, 7/7 first-lesson 206, 7/7 last-lesson 206,
  7/7 map 206, Android API 401, Desktop API 401, exam 404.
  The status-only script read **no lesson/answer bodies**, used no
  Telegram/Pro tokens, and produced **14** exposure review findings.
- **Updated evidence:** `b4b8cf64906ef73a1cb03c7aa3f53fb78368c181`
  updated `localization/review/staging_anonymous_http_results_20261017.json`;
  `17706db1f829a63bf4138bc1fc4619efa3a5e9b0` updated the
  staging QA runbook;
  `1a5090190e024850f665cb68242237821a2fa4a7` updated
  `docs/I18N_P0_AUDIT_FINDINGS.md`.
- **Security implication:** the sampled anonymous staging legacy
  content exposure extends beyond initial HSK lessons into late
  lessons. **Not established** that an individual late lesson
  is paid or that production allows the same request; do not
  classify this as a verified Pro payment bypass. Existing native
  API 401 and private exam 404 status observations remain valid.
- **Open gates:** disposable authenticated Free/Trial/Pro users,
  real quota and entitlement status tests, Mini App background
  prefetched-content redaction, cache account-switch isolation,
  old client compatibility and controlled migration strategy.
  No runtime route, lesson content, payment, production or main
  change occurred. P0 IN PROGRESS, P1-P4 NOT STARTED.

### P0 seventeenth implementation slice — 2026-10-17 (Mini App reservation-vs-content boundary)

- **Auth/lesson-start source contract:** `18a2d5d55da7259087484a174bb5700f8c8baa58`
  adds `scripts/i18n_miniapp_reservation_boundary_audit.py`. It
  checks the *actual* nested `v3_course_lesson_start` handler in
  `app/api/miniapp_entitlements.py` with Python AST and the
  `app/static/course-v3.html` call boundary without importing the
  production app or touching a database. It guards Telegram initData
  verification, no-identity **401**, user lookup, lesson bounds,
  next-in-sequence **403**, `LessonAccessService.status(..., consume=True)`,
  transaction commit and the Mini App's reservation-before-JSON
  order. Source-only reviews still explicitly flag:
  `loadLessonData()` uses an independent **public static JSON GET**,
  and `reserveLessonStart()` returns client-side allowed when
  `INIT_DATA` is unavailable. The guarded start route is not a
  substitute for authenticated content delivery.
- **Source regression tests:** `0a65c40c554eb75b451d5a0d628fb4cda9dbc40a`
  adds `tests/test_i18n_miniapp_reservation_boundary_audit.py`
  with seven cases for current source and negative mutations
  (removing 401, `consume=True`, next-lesson gating,
  reservation sequencing or direct JSON fetch). `b3548b22fedaa69130f33fa82a7ef749bdbbb100`
  integrates both the read-only JSON report
  `miniapp-reservation-boundary.json` and tests in fast P0 CI.
  [P0 run 39022062198](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39022062198)
  completed **SUCCESS**.
- **Synthetic, HTTP-level contract:** `55758779a09604302dde196c98997cabcabbb454`
  adds `tests/test_i18n_miniapp_reservation_asgi.py`,
  constructing an isolated FastAPI router with a **synthetic**
  Telegram HMAC test fixture and mocked DB, progress, user
  and entitlement services. Five tests verify: no token or
  forged initData gives 401 **without opening a DB session**;
  a valid synthetic signature passes exactly one
  `consume=True` invocation; out-of-order lessons return 403
  without consumption; a mock quota-denial returns 403.
  The fake service does not actually spend user quota.
  `399b0c0d6ccc59b95c6b565d1e22f1cd62f34884`
  invokes this test in Backend CI.
  [Backend run 39022244643](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39022244643)
  completed **SUCCESS**, including the new ASGI tests.
- **Known P0 issue confirmed but NOT fixed:** 24 staging
  anonymous GET-status probes already show both the first
  and final lesson files per track return HTTP 206, while
  anonymous Android/Desktop content APIs return 401.
  The Mini App's authenticated start check does not authorize
  subsequent static JSON download. A transition must separate
  speculative/non-consuming previews, skip tests and
  foundation content from intentional quota-consuming lesson
  starts. Test Free/Trial/Pro/blocked users, paid lessons,
  quota snapshots and WebView account-switch cache isolation
  on isolated disposable staging fixtures.
- **Safety:** no production source behavior, lesson bodies,
  answers, billing, bot token, DB rows, production Railway
  or `main` changes. PR #179 remains Draft.
  P0 IN PROGRESS; P1-P4 NOT STARTED.

For each implementation commit, update the relevant milestone with:
**commit SHA, exact files, passing tests, known gaps and next action**.
Never claim tests were run unless CI/logs or local results confirm it.
Keep GitHub's branch current without force-resetting unrelated user work.
