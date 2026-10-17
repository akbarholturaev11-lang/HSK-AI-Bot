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

For each implementation commit, update the relevant milestone with:
**commit SHA, exact files, passing tests, known gaps and next action**.
Never claim tests were run unless CI/logs or local results confirm it.
Keep GitHub's branch current without force-resetting unrelated user work.
