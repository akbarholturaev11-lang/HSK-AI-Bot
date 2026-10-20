## Current integration handoff — 2026-10-20 (feature branch; external release QA open)

**Use `localization/RESUME_NEXT_CHAT.md` then `localization/P3_ACTIVE_HANDOFF.md` for the current branch/CI state.** Work only on `codex/p3-main-integration-20261020`; do not push/merge `main`, force-push, rebase or deploy production. Latest pushed code is `f62344838cf18884c1809e262469ee0f273bcacc`; `origin/main` `66ac3d4e94ead8a3c34d45910ffe60f988bf1cf5` is an ancestor (514 ahead, 0 behind).

GitHub P0 [`39438909149`](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39438909149) **SUCCESS** on exact code HEAD `f6234483`; local workflow-equivalent passed **370 tests**. Android `:app:compilePlayDebugKotlin :app:compileDirectDebugKotlin` passed. Read-only checks report 812 frozen sources / 746 lessons / 0 baseline blockers, 894 course UI keys and 55 common UI keys per locale, with 0 stale artifacts. This batch reused generated resources for three final exact-copy Android labels; account, access, grading, payment and course behavior are unchanged.

P3's 136 source-bound Chinese contexts / 408 UZ/RU/TJ values have agent-owned source-context QA recorded and remain display-only behind existing access checks; this is not native-speaker certification. Staging HTTP, authenticated account/access, old-client, offline and installed Android/WebView/macOS/Windows acceptance remain open. `main` and production remain untouched.

## Controlling P3 language QA decision — 2026-10-19

The owner delegates existing UZ/RU/TJ translation correctness and migration
to the engineering agent; **no manual/human translation-review prerequisite**.
Follow `localization/AI_CONTENT_QA_POLICY.md` for independent source-context
semantic review, fixes, duplicate/mirror sync, protected-source diff, local-first
content migration and regression tests. Historical references below to "human
review required" are legacy wording superseded ONLY for the linguistic
reviewer identity. They do NOT waive source SHA, safety, QA, CI or release
gates. The current 136-context catalog has been checked against its Chinese
source and grammar context, and its 408 UZ/RU/TJ values are integrated into the
existing access-gated display overlay. This is documented agent QA, not
native-speaker certification. Work on the feature branch while CI, security,
staging and cross-platform QA remain pending.

# HSK AI i18n — Plan / Schema / Execution Order

> **Canonical handoff for the local-first multilingual migration.**
> All future work on this feature must start here, then read
> `docs/I18N_LOCAL_FIRST_WORKPLAN.md`,
> `docs/I18N_MULTILANGUAGE_MIGRATION.md`, and
> `localization/surface_registry.json`.
>
> Status: **P0 source guards and P1 local catalogs implemented; P2 exact-copy adoption continues only where source and context match; P3 agent-owned review and the 136-context canonical catalog are source-bound and delivered display-only behind access checks. Mini App full lesson reads use signed, non-consuming authorization; the legacy public lesson-file route is retired. Exact-head GitHub P0 succeeded on `f6234483` (run `39438909149`; local workflow-equivalent: 370 tests); Android Play/Direct Kotlin compilation succeeded. Course catalog is 894 keys/locale; common catalog is 55 keys/locale; all 12 generated artifacts are current. Staging/platform acceptance remains open. Feature branch only.** Earlier dated entries preserve historical states and do not override this checkpoint.

## 0. Where to resume

- Repository: `akbarholturaev11-lang/HSK-AI-Bot`.
- Active integration branch: `codex/p3-main-integration-20261020`; the old `codex/i18n-local-first-foundation-20261017` work is already integrated.
- Latest pushed code: `f62344838cf18884c1809e262469ee0f273bcacc`. `origin/main` is `66ac3d4e94ead8a3c34d45910ffe60f988bf1cf5` and is an ancestor (514 ahead, 0 behind). Continue only on the feature branch; do not push/merge `main`, deploy, force-push or run live DB migrations.
- Exact-head P0 `39438909149` succeeded on `f6234483`; local workflow-equivalent passed 370 tests. Android Play/Direct Kotlin compilation succeeded. Read-only checks report 812 frozen sources / 746 lessons / 0 baseline blockers; 894 course UI keys and 55 common UI keys per locale, 0 stale generated artifacts. No backend workflow was triggered by this display-copy-only commit. Prior Mini App Chrome smoke passed in UZ/RU/TJ at 390×844 with no console or HTTP errors.
- Signed Mini App lesson content validates Telegram identity, canonical account and level, next/completed sequence, required HSK1 foundation and shared entitlement with `consume=False`; full JSON is no-store. The old public lesson route returns 404. Sales, foundation and skip-test have separate projections; skip-test is capped at six and rejects skip-ahead.
- **Next code pass:** reconcile remaining registered Mini App page-local dictionaries and static attributes with shared catalog keys, keeping only context-matched aliases and exact UZ/RU/TJ fallback values. Then run affected browser checks and P0. Staging HTTP, real account/entitlement, old-client refresh, offline and installed-client QA remain separate release gates.

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

### P0 — discovery and frozen baseline [SOURCE GUARDS IMPLEMENTED; route exposure review open]
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

### P1 — catalog and validation [IMPLEMENTED; current generators pass]
1. Define stable namespaced message keys, context/HTML-safety metadata,
   named placeholders, plurals, locale normalization and fallback rules.
2. Move a *small reviewed set* of common/error strings into source catalogs
   without deleting the existing runtime dictionaries.
3. Implement deterministic validation for completeness/placeholder parity,
   unsafe HTML, invalid JSON/XML and accidental language fallback.
4. Generate local target artifacts and verify byte-stable reruns.
**Exit:** change one source key, regenerate 4 local targets (Android,
Mini App, Desktop, Bot), prove no new runtime per-string API request.

### P2 — incremental UI adoption [IN PROGRESS; remaining context-specific UI surfaces and functional QA open]
1. Android: generated standard resources, then Kotlin-inline copy.
   Preserve `direct` and `play` payment strings and APK offline startup.
2. Mini App: adopt cached catalogs screen-by-screen; preserve deep links,
   bfcache, inline accessibility, quiz/paywall and error states.
3. Desktop: generated bundled i18n for paired macOS/Windows builds.
4. Bot/backend/notifications/public pages: local catalogs, with old API
   language fields and scheduled message fallback behavior preserved.
**Exit:** screenshots and baseline text parity for all 3 original languages,
mobile + browser + desktop flows tested.

### P3 — lesson localization overlays [PRIVATE CANDIDATES AND GENERATOR VERIFIED; runtime delivery gated on entitlement review]
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
| Full reviewed inventory/baselines (P0) | IN PROGRESS | 811 frozen sources / 746 lessons / 0 baseline blockers; route security, staging and real-client QA remain open |
| Generated canonical catalogs + validators (P1) | IMPLEMENTED | deterministic UZ/RU/TJ resources for Android/Mini App/Desktop/Bot; 892 course UI keys and 6 current generated artifacts |
| Platform runtime migrations (P2) | IN PROGRESS | Mini App uses local course catalog; remaining inline UI and Android/native, Desktop and Bot adoption are still under review |
| Versioned lesson locale overlays (P3) | IN PROGRESS | 136 contexts / 408 agent-reviewed locale strings; authenticated display-only runtime implemented; release QA pending |
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

### P0 eighteenth implementation slice — 2026-10-17 (source assessment fields in legacy lesson JSON)

- **Reason for further audit:** source inspection confirmed that `answer_tokens` in
  word-order exercises also contains solution-like structure distinct from
  `correct_index`. It is possible for future public locale packs to
  leak these arrays even if index keys are excluded.
- **Publish guard hardened:** `0659e4e9b919cec5b7de08e09c61fb323b5e49a6`
  added `answer_tokens`, `correct_tokens`, `solution_tokens` and
  `expected_tokens` to `scripts/i18n_public_bundle_guard.py`
  forbidden grading fields (camelCase/kebab normalized).
  `8173f8e178986b1e40752223fd3bfda1443519bf` tests these
  synthetic keys without leaking answer values. Existing public
  legacy lesson JSON is NOT remediated by this new-pack guard.
- **New all-source inventory:** `ec86b03ed6afb6d3281354f5eca13730b468037e`
  added `scripts/i18n_legacy_lesson_content_risk_audit.py`:
  scans seven tracks' `lesson_*.json` files, counts ONLY
  preclassified grading key names, and reports first and last
  source lesson per track with no Hanzi, pinyin, translations,
  options, answer values, tokens or user data.
  `941d3b8239b15d87727b72764b40ebcea0c66ce2` added
  mutation/secret-free output and 746-source regression tests.
  `5267aa05fd961d9acaa94e1028c7ffcc138ce630` integrated
  `public-lesson-source-risk.json` into P0 CI artifact.
  An initial standalone CLI import failed while the unittest path
  worked; `88daad0b2cbc4d23c094981c33b22eb529c871b6`
  corrected both package and direct-script imports.
- **Verified CI artifact:** [P0 run 39025089879](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39025089879)
  completed **SUCCESS**. Downloaded and examined artifact
  `12098177455`: 746 source lesson JSON files, **746/746
  include assessment-related field names**, with **6,449
  `correct_index` occurrences** and **704 `answer_tokens`
  occurrences**; exactly fourteen first/last track samples.
  The source report and test do NOT claim that all 746 URLs
  were HTTP tested or that each is paid. Existing separate
  [staging 24-status run 39018359239](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39018359239)
  confirmed anonymous HTTP 206 only for fourteen sampled first/last
  files, not all sources.
- **Permanent handoff result:** `localization/review/legacy_lesson_grading_field_summary_20261017.json`
  (`a00b0c3cec5c0cc7888218eb3d3fb12b3a777810`) stores
  source counts plus sampled field-name counts without answers.
- **Open gate:** actual authenticated Free/Trial/Pro entitlements,
  advanced paid-lesson classification, Mini App speculative
  no-consume fetches, A->B cache isolation and native/old-client
  migration validation. Do not make a public locale bundle out
  of raw lesson JSON. P0 IN PROGRESS, P1–P4 NOT STARTED,
  PR #179 Draft. No app runtime, production, billing, lesson or
  grading values changed.

### P0 nineteenth implementation slice — 2026-10-17 (WebView local state account-boundary inventory)

- **New source-only cache-scope registry:** `localization/review/miniapp_client_storage_scope_20261017.json`
  added in `46fcea3da1e592d5b348416ea3b4d8ce55fbc959`.
  It classifies 22 quoted-literal `localStorage`/`sessionStorage`
  operations across course Mini App and `course_v3_memorize.html`,
  grouped into 11 key classes; plus five dynamic key constructors.
  The registry distinguishes UX flags from progress/mastery and
  notes source-level user scope, not a confirmed account leak.
- **Important separate unscoped personal learning state:** the course
  page's `lessonResumeKey()` is level+order only and
  `lessonDataKey()` is a page-memory level+order cache; the
  memorization page reads/writes per-Hanzi mastery and errors under
  a single unscoped `hsk_memo` key. `lessonMasteryKey()` and
  `foundationCacheKey()` do use `localUserScope()`; the setup
  time key uses a different explicit Telegram user-ID suffix.
  `localUserScope()` reads `tg.initDataUnsafe` and is only
  client-side scoping, never server-proven authorization.
- **Read-only regression:** `scripts/i18n_miniapp_storage_scope_audit.py`
  (`b64a8752ff7e18af9a58d6922baa1c56d914d4f8`) compares exact
  reviewed literal operations, dynamic constructors and
  identity-scope flags without inspecting browser/user content.
  `tests/test_i18n_miniapp_storage_scope_audit.py`
  (`dbc7e88288ffcfdbd79a44b10d50b76bfcca48e3`)
  tests new-key drift, lost mastery scoping and memorization
  storage changes. `e3e11dd883cb888060f394b9875548d930b09807`
  adds both to the fast CI and archives
  `miniapp-storage-scope.json`.
  An initial run flagged a multiline setup-time constructor due
  to a scanner limitation; `9653d78d98e4e4cf90ec1de7359c91c2a896bb22`
  corrected it. [Fast P0 run 39026289977](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39026289977)
  finished **SUCCESS**, including all 5 new tests.
- **Detailed audit findings:** `docs/I18N_P0_AUDIT_FINDINGS.md`
  updated in `dc7156705930e290a8fc81cffb7bff1cdd1c3202`.
  This slice made no WebView/browser, Mini App runtime, lesson,
  progress, subscription, payment, Railway staging or production
  changes; branch only, PR #179 remains Draft.
- **Unclosed QA:** simulate two approved/disposable users on the same
  Telegram WebView origin and verify no account A resume/mastery/
  memorize history or in-flight authorized lesson cache appears
  under account B. Define safe key/version migration and cleanup
  before code changes. Existing 24 anonymous staging status-only
  results and 746 source grading-field findings still stand.
  P0 IN PROGRESS, P1–P4 NOT STARTED.

### P1 first code slice — 2026-10-17 (user-directed code-first implementation)

- **Sequencing:** user directed completing code on the isolated branch
  *before* manual server/device QA. P0 source security findings and
  screenshots remain open; P1 groundwork is proceeding **at branch-only
  build-time**, without activating runtime language switching, new
  locales, public course overlay endpoints, or merging to `main`.
  The isolated staging server is not used for this code slice.
- **Canonical common strings:** `localization/ui/{uz,ru,tj}/common.json`
  created in commits `3c4a2b70d1495e72be1da5d698bec92ab6b1da18`,
  `dc6c09e4a3433c19b10ca263779fe868a772467d`,
  and `1c2afe097638cf119cc5b571ab4ed25075df8e6b`.
  Exactly **11 common UI keys** were copied from existing three-language
  `desktop/ui/js/i18n.js` copy. They are baseline transcriptions,
  **not independently reviewed translations**. `auth.expires` has
  a named `{time}` placeholder for parity validation.
- **Generator implemented:** `scripts/i18n_build_local_catalogs.py`
  (`718239de3b0d85bce02bfcfb2ac8aa89a0e7de35`) produces **six**
  deterministic local artifacts: Android three language XML resources
  (`values`, `values-ru`, `values-tg`), Mini App static JS,
  Desktop bundled JS and local Bot Python constant. `--write`
  regenerates source-derived outputs, `--check` detects stale outputs.
  Requires only Python stdlib; no translation API, database, session,
  new dependency or runtime per-string network access.
- **Validation:** tests in
  `tests/test_i18n_build_local_catalogs.py` (`0749c9b15cc688706ff1688cda23b468702ca1de`,
  expanded by `d771f9d3885b479dc75ca32b2abd0c48a35529d3`
  and corrected by `f3296f09107ee5792384aab8d969caf879e40808`)
  verify source-to-existing Desktop parity, exact generated byte
  identity, placeholder preservation, unsafe plain text rejection,
  duplicate JSON key rejection, Android XML and Python syntax, and
  deterministic rebuild. `5697520e91daa0e7ab9e512e287881bdffacc508`
  adds the unit tests and build `--check` to dedicated P0 CI.
  The local Bot output sorting was corrected in
  `aeedae931163b3ccf410fcf24ba0968faa5e8550`.
- **Implementation guide:**
  `docs/I18N_P1_COMMON_CATALOG_IMPLEMENTATION.md`
  (commit `8847fc494cf0c620a494ff46c6df5faebaeed542`).
  Generated browser files are not yet imported into existing page
  rendering and generated Bot keys are not yet substituted for legacy
  `TEXTS` / existing Android resources. This is **P1 groundwork**,
  not a feature completion claim. Do not reset P0 immutable baseline
  hash registry to conceal expected future UI source edits.
- **Remaining:** expand beyond 11 common keys to complete UI coverage,
  validate language-specific grammar/escaping, adopt screen-by-screen
  in Mini App/Android/Desktop/Bot, establish documented old/new hash
  review for intentional UI source migration, and then execute real
  locale/offline/auth/lesson/Pro QA. P1 still IN PROGRESS; P2/P3/P4
  NOT STARTED. Production/runtime and `main` unchanged.

### P2 first branch-only UI adoption — 2026-10-17 (same-text fallbacks)

- **Desktop runtime:** `desktop/ui/js/i18n.js` now imports bundled
  `generated/hsk-common-i18n.js` and resolves the 11 reviewed common
  keys from the generated local catalog, retaining the original
  `messages[activeLanguage]` values as fallbacks (commit
  `0f71eb73a698d2ec186595558f68831ac9dcfe68`). The identical
  Desktop JS source is bundled for macOS/Windows; no HTTP per UI key.
  Generated browser JS includes a `typeof window` guard to remain
  safe under Node ESM tooling (`7b59c0d6864c887ac1d4ce4351bb988e87825b6f`,
  regenerated bundles `0f4616f9d9202907f07577cc37a72d38c32ef854`
  and `27e70e3b47c58e0b32a1e82bb5fabd35e19b26e8`).
- **Mini App runtime:** `app/static/course-v3.html` loads only the
  versioned local static common JS bundle. Its `rating` heading
  now prefers the generated `navigation.rating` translation with
  exactly the same legacy `uz/ru/tj` fallback string in place
  (`74792b04f9f729cd973255a9c488e76b8e9d0f27`).
  Added the script and helper on **existing physical source lines**
  so 60/125 tracked predicate source anchors and six prefetch
  call-site anchors remain stable. No lesson, quiz, billing, cache or
  language-switch code was modified.
- **Immutable baseline preserved:** P0 `source_git_blobs.json`
  remains unmodified. `scripts/i18n_baseline_guard.py` (commit
  `bee4a5116c443689d20c9d928f466cba4bc1741b`) accepts *only*
  explicitly reviewed exact new Git blob SHA-1 for
  `ui_catalog_origins`, never source lessons. The allowlist
  `localization/baselines/reviewed_ui_changes.json`
  (`71aa38b3d2644ed3223d889ecae1454ba30e6058`) pins
  old + new hashes and review reasons for precisely the two UI files.
  `tests/test_i18n_baseline_guard.py` (commit
  `4cf54a1fde9868011a8c1bacf0ea11860a8e6d2a`)
  proves arbitrary drift and attempted lesson waivers are rejected.
- **Adoption tests:** `tests/test_i18n_common_ui_adoption.py`
  (`28ac9a950f525b5b2b735dbb986343077a2e48cb`) checks exact
  reviewed hashes, local bundle imports, legacy fallback retention,
  no private lesson data in generated UI JS, and no per-string fetch.
  `222f8a9ed25a24bc7356e2d2350685f0e57ab6d4`
  wires this test to localization CI. Original Desktop catalog
  source-parity test now scopes only the `messages` table, not the
  added adapter mapping (`8989aed8d9a2b524ccad6af8beec332e788a1631`).
- **Status caution:** This is **partial code adoption**, NOT complete
  localization migration or QA acceptance. P0 security and device
  screenshot/access QA remains open; P1 and P2 IN PROGRESS.
  Bot/Android UIs have not been switched to generated keys yet.
  P3/P4 NOT STARTED. No deployment, production or main changes
  were performed in this slice, as user requested code-first workflow.

### P2 first slice follow-up — Android navigation + Bot local lookup

- **Android:** `9f3b7f75bd846e551312b8d40b5992ce9ac8ab4a`
  changes only the four `MainTab` navigation label resources in
  `android/app/src/main/java/com/pomp/hskai/core/navigation/MainScaffold.kt`
  to generated `hsk_common_navigation_*`. Source XML for Uzbek
  default, Russian and Tajik is byte-equivalent to pre-existing
  `nav_*` strings. Main-source Compose navigation is shared by
  direct and Play builds. No billing/payment label changed.
  `6bdf3f3b48b1466d212992f984a907b5a76dfcb9`
  adds Android XML / legacy parity assertions to P2 tests.
- **Bot:** `021620528ef2bd9ecddec6380f34c42ab5fd4df6`
  adds a namespaced `common.<key>` lookup to the existing Bot
  `t(key, lang, **kwargs)` function. Values are loaded from the
  generated *local Python constant* only, with `tg`→`tj`
  compatibility and original Bot Russian fallback for unknown
  locales. Non-common Bot keys continue using the original
  Gemini-aware legacy logic; payments/notifications unaffected.
  `b91f9cddd1e052e49a0af2c112d838d083681791`
  marks the generated folder a package.
- **Exact source-blob review:** the
  `localization/baselines/reviewed_ui_changes.json` manifest now
  also pins the old and new hashes of `app/bot/utils/i18n.py`
  (`f911721071f4c64fe0d1219e4c73e3d92b3d062a`).
  `ab532f14ecf0f66d8bad1b79175af3aef162023c`
  adds Bot runtime adapter tests and retains the original test
  for lesson/source hash integrity; no lesson blob exception exists.
- **Scope:** Android **four** navigation labels, Desktop 11 keys,
  Mini App one heading, Bot generated common-key lookup. This is
  NOT full locale migration and not a launch. All source changes
  remain Draft PR #179, not `main`. Device/HTTP manual QA is
  intentionally deferred until code completion by user request.
  P0 security unresolved; P1/P2 partial; P3/P4 NOT STARTED.

### P1/P2 continuation — 2026-10-17 (course catalog drift guard, new chat)

- **Current branch verified:** `codex/i18n-local-first-foundation-20261017`
  was at `c6cffdb1254e7fe41b9e1fd4858b102aa499523b` before this
  slice, a later commit extracting existing Tajik Mini App course UI
  strings into `localization/ui/tj/course.json`. The prior P0
  source audits and source-level staging findings are still present
  in the repository. PR #179 remains Draft against unchanged `main`.
- **Source check:** `localization/ui/{uz,ru,tj}/course.json` contain
  **86 keys per locale**, with identical key sets and named placeholder
  signatures; two keys contain `{n}`. No independent translation
  quality or device UI/online entitlement claim follows from this.
- **Source-only guard:** commit `31e8b2e9a35535c1ca880e761c14a74873b744d5`
  adds `scripts/i18n_course_ui_catalog_guard.py`. It validates
  JSON key uniqueness (including duplicate metadata keys), strict
  namespace/version/locale metadata, exactly 86 UI messages,
  safe plain string values without HTML, named placeholder counts
  across all three languages and absence of answer/grading fields.
  It emits a small metadata-only JSON report, never UI text or
  lesson/quiz answers.
- **Regression tests and CI:** commit
  `761184fc907476a12941119778a20b2516ff61ef` adds
  `tests/test_i18n_course_ui_catalog_guard.py` for real source,
  synthetic missing keys, placeholder drift, raw HTML, duplicate
  JSON keys and forbidden grading-field entries. Commit
  `8908867c5bfb7f4a30ccd9b3d6c0a431bfeada35` integrates
  the tests and `course-ui-catalog.json` source-only artifact in
  `.github/workflows/i18n-p0.yml`.
  [Fast P0 CI 39032399943](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39032399943)
  completed **SUCCESS**. No production runtime, lesson, locale
  activation, billing, secrets or server routes changed.
- **Current infrastructure blocker:** read-only Railway discovery
  shows that the previously used `hsk-ai-p0-qa` application
  service is **absent** from current Railway staging; the staging
  environment now has PostgreSQL only. Do not reuse old staging
  health/HTTP evidence as proof of today's server availability.
  Reprovisioning a cost-bearing staging application requires an
  explicit new operator decision, isolated credentials and no
  production secrets. No staging deployment was made in this slice.
- **Independent Android CI warning:** at prior HEAD
  `c6cffdb...`, Android CI run
  [39029757839](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39029757839)
  FAILED in two `VoiceScreenBackTest` emulator focus/root-view
  assertions; Backend and P0 source CI PASSED. Root cause vs
  locale code is not established. This Android release gate must be
  triaged independently; do not call Android fully green.
- **Open scope:** manually verify UI language switching across native
  apps, Telegram WebView account isolation, offline/cache behavior
  and Pro/Free lesson entitlement; legacy anonymous lesson URLs remain
  an unresolved P0 security finding. P1/P2 code adoption partial,
  P3/P4 NOT STARTED; `main` must not be merged.

For each implementation commit, update the relevant milestone with:
**commit SHA, exact files, passing tests, known gaps and next action**.
Never claim tests were run unless CI/logs or local results confirm it.
Keep GitHub's branch current without force-resetting unrelated user work.

### P1 course UI static targets — 2026-10-17 (branch-only, no runtime activation)

- Commit [`d7b157f2ebb5e62f6a32852573c2df8f98be2b2f`](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/commit/d7b157f2ebb5e62f6a32852573c2df8f98be2b2f)
  adds `scripts/i18n_build_course_catalogs.py`,
  `tests/test_i18n_build_course_catalogs.py`, six generated assets
  and the `.github/workflows/i18n-p0.yml` `--check`/test steps.
- Exact generated destinations: Android
  `android/app/src/main/res/values{,-ru,-tg}/hsk_course_i18n.xml`;
  Mini App `app/static/course_v3_data/hsk-course-i18n.js`;
  Desktop `desktop/ui/js/generated/hsk-course-i18n.js`; Bot
  `app/bot/generated/course_i18n.py`. Generated resources are **not**
  imported by the active course UI and do not change app language switching.
- Inputs are the already-present 86-key `localization/ui/{uz,ru,tj}/course.json`
  sources. The existing fail-closed course source guard runs before writing:
  all three locales must have matching keys/named placeholders, no duplicate
  metadata, no HTML and no grade/solution fields. Android resource names
  normalize camelCase to lowercase snake_case with collision detection,
  preserving `tj` for Bot and `tg` for Android.
- [Fast localization CI 39032942050](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39032942050)
  passed its **source-contract** job, including all new regression tests,
  `--check` deterministic byte comparison and existing P0 audits.
  Desktop contract/TTS-related jobs also passed at this commit.
  **Android full CI and backend targeted CI were still running at the
  time of this note**; never infer their outcome from P0 CI.
- Scope deliberately excludes live app adoption, course source JSON,
  quiz answers, XP, progress, auth, access, payments, server routes and
  public entitlement. Existing open P0 public-lesson route and account-cache
  isolation investigations are unchanged. P1/P2 remain partial; P3/P4
  remain NOT STARTED, and PR #179 stays Draft against `main`.
- **Next:** adopt one explicitly reviewed existing Mini App `course`
  string with exact fallback parity, then audit native-device offline and
  cross-account behavior before expanding; verify Android CI separately.

### P2 second UI adoption slice — 2026-10-17 (Mini App profile/settings)

- Branch-only implementation commit
  [`6e1c4de22a19e4bfa529ddf490cf90c41fb5202d`](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/commit/6e1c4de22a19e4bfa529ddf490cf90c41fb5202d)
  updates **only** `app/static/course-v3.html`,
  `localization/baselines/reviewed_ui_changes.json` and
  `tests/test_i18n_common_ui_adoption.py`.
- Mini App now statically loads the already-generated
  `/course_v3_data/hsk-course-i18n.js?v=20261017-course-v1`
  before its inline application script. The synchronous local
  `courseMessage(key,fallback)` only reads the window-bundled
  `HSKAI_COURSE_I18N[LANG]` table; **there is no new runtime per-label API**.
  No fallback locale or preference order changed.
- Exactly **four reviewed keys / five use sites** migrate to generated
  local values, with the **exact original inline expression retained**
  as fallback: `lang` (settings + language picker), `notif`
  (settings), `friends` (profile), `helpTitle` (help sheet).
  Existing Russian, Uzbek and Tajik source messages were compared
  byte-for-byte against current I18N values before replacement.
  Source file keeps **8,712 lines**, leaving previously reviewed
  60/125 predicate anchors and 6 lesson fetch call sites at their
  original physical lines.
- Updated reviewed Git blob allowlist now records Mini App SHA-1
  `4766abaa898616bbf54f5844206c3364c3e68d43`; no
  source lesson or answer-key checksum waiver was introduced.
- [Fast P0 CI 39033908596](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39033908596)
  finished **SUCCESS**, including **138 tests**. Deterministic course
  UI build check shows three locales, six generated assets, **zero
  stale outputs**. Lesson-fetch and Mini App storage source
  regressions report zero contract deviations.
- **Limitations:** static source and CI assertions are not Telegram
  WebView screenshots, cache/offline QA or real-account switching
  tests. Mobile browser must load one small versioned script asset
  (normal browser caching applies; it is not zero HTTP traffic).
  Public original lesson JSON and grading-field exposure remain
  an unresolved P0 review boundary. Android emulator/full CI and
  backend independent tests must be checked by their own job result.
  No production deployment, auth, billing, quiz, XP, progress, answer
  keys or new locales were changed in this slice.
- **Next:** continue incremental screens after separately verifying
  real-device/offline copies; keep `main`, `codex/local-ai`,
  `codex/cloud-ai` unchanged. PR #179 stays Draft.

### P2 third UI adoption slice — 2026-10-17 (practice, AI Voice and help)

- **Code commit** [`91e2961960afe62fc3f2ffff6b470b6754271614`](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/commit/91e2961960afe62fc3f2ffff6b470b6754271614) modifies precisely `app/static/course-v3.html`, `tests/test_i18n_common_ui_adoption.py`, and `localization/baselines/reviewed_ui_changes.json`. Follow-up test correction [`d4899aedcae966ca27a08abafba0d0847d96f52e`](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/commit/d4899aedcae966ca27a08abafba0d0847d96f52e) preserves the intended fixture line-count assertion with the file's existing trailing newline.
- **Exactly 24 *new* keys in 30 new usage sites, on top of four previously migrated keys in five sites (28 distinct keys / 35 total use sites)**. Selected `course` keys are `nav.mashq`, `mashqSub`, `grammar`, `pron`, `dict`, `dictSub`, `readyPhrases`, `readyPhrasesSub`, `recog`, `recogSub`, `pronSub`, `testCenter`, `testSub`, `mistakes`, `mistakesSub`, `voiceTitle`, `voiceSub`, `voiceStart`, `help`, `helpText`, `helpBtn`, `helpNoContact`, `nav.profile`, and `streak`.
- Existing `t.<key>` and literal profile-title strings remain **the exact fallback expressions**; no locale precedence, account preference, network request, API schema, live authentication, quiz marking, content JSON, notification scheduler, paywall, payment or entitlement changed. Course messages continue to be served as one bundled cacheable static JS asset already introduced by P2; nothing is fetched per UI key.
- Source-level comparison before writing validated **24 keys × 3 locales = 72 values** against the existing current Mini App I18N source. Physical source line offsets for previously audited Mini App lesson fetch, LANG predicates and WebView storage remain unchanged: the file's `split("\n")` retains 8,712 segments including the terminal empty segment. No change to any of the 746 source lesson JSON files or baseline lesson checksum exception.
- [**Local-first P0 CI 39046378923**](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39046378923) completed **SUCCESS** at corrected code commit `d4899aed...`: **139 Python regression tests passed**, all source audits passed; 86 course keys per locale, 6 generated course UI targets with **0 stale files**. The first code commit's test run failed on a source line-count assertion (trailing newline vs Python `splitlines()`), corrected in `d4899aed...`; do not misclassify this as an app runtime regression.
- Full device, Telegram WebView, screenshots, offline/cache, account switching and Free/Trial/Pro authenticated flows are **not** confirmed by these source tests. Existing legacy anonymous lesson JSON access remains an open P0 security risk to audit separately. Android full CI/Backend CI must be read independently; no production deployment or `main` merge authorized.
- **Next:** select another strictly reviewed UI-only slice, extend exact-copy parity tests, then perform device/auth/cache release gates before any wider activation. PR #179 remains Draft against `main`.

### P2 fourth UI adoption slice — 2026-10-18 (Mini App map, sheet, tour/nav)

- **Code commit:** [`0bf8e353bf972ef61a32b65510014fe428e843ea`](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/commit/0bf8e353bf972ef61a32b65510014fe428e843ea).
  Changed only `app/static/course-v3.html`,
  `tests/test_i18n_common_ui_adoption.py`, and the Mini App
  approved SHA in `localization/baselines/reviewed_ui_changes.json`.
- Adopted existing statically bundled `courseMessage(key, legacyFallback)`
  in **7 explicit view uses for six additional keys**
  (`unit`, `lessons`, `cont`, `repeat`, `stage`,
  `completeOf`) within course map, node badges, and lesson
  sheet. The tab labels and onboarding tour now use dynamic
  `courseMessage("nav."+screen, T().nav[screen])` lookups for
  all five existing `nav.course`, `nav.mashq`, `nav.voice`,
  `nav.rating`, `nav.profile` labels. The tour and tabs do
  not introduce new route choices, branches or data loading.
- **At this commit** 37 distinct course catalog keys have at
  least one selected local Mini App use (the prior 28 plus six
  explicit keys and three newly adopted navigation keys); the
  generated JSON input continues to contain 86 keys for each
  of three locales. New migration verified 11 source keys
  × 3 languages = **33 byte-identical fallback values**, with
  physical `course-v3.html` line count unchanged at
  8,712 newline-split segments. Existing lesson JSON, quizzes,
  correct-answer grading, consent/auth, progress, server
  entitlement, payment and trial flows are unchanged.
- [**Fast localization P0 CI 39086777956**](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39086777956)
  **SUCCESS:** 140 Python regression tests passed; three
  locales / six generated course assets; **0 stale outputs**.
  Desktop, lesson TTS and persistent local TTS workflows also
  passed on this code commit. Android full CI and Backend
  targeted CI were still **in progress when this note was
  written**; their conclusions must not be inferred.
- **Deferred gates:** native/WebView visual testing, local
  airplane mode and fresh-file/cold-start behavior, account
  switching, payment/access and user-authenticated
  deep-link/sheet flow verification. The pre-existing anonymous
  lesson JSON risk remains P0-open. No `main` merge,
  production deployment or new per-string HTTP requests.
- **Next:** finish reviewed non-gating presentation keys and
  document missing strings for future locale expansion;
  keep PR #179 Draft and unrelated protected work unchanged.

### P2 fifth UI adoption slice — 2026-10-18 (exercise labels, profile rating)

- **Implementation commit:** [`18949d7e2b3bcdf48692484374570d0610b6e689`](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/commit/18949d7e2b3bcdf48692484374570d0610b6e689) changes only `app/static/course-v3.html`, `tests/test_i18n_common_ui_adoption.py`, and the reviewed Mini App source blob entry in `localization/baselines/reviewed_ui_changes.json`.
- **Eleven additional display-only static keys / 23 call-sites:** `buildSent` (1), `dialog` (1), `listen` (2), `matchPairs` (1), `say` (5), `check` (2), `next` (2), `rightAns` (1), `you` (6), `league` (1), and `xp` (1). Mini App course source now uses **48 distinct catalog keys** including previously approved dynamic navigation labels out of the **86 source keys per locale**. Other source catalog keys are intentionally staged, not all wired.
- All 11 keys were verified against the **original inline I18N values in three locales** before editing (33 exact fallback equality checks). Only `T().<key>` and specifically inspected `t.you/t.league/t.xp` display reads were wrapped with `courseMessage(key, legacyValue)`; no feedback correctness predicates, answer indices, score updates, voice recording gates, trial/pro/paywall/entitlement decisions, lesson JSON, TTS routes, server requests or progress storage were changed. The large HTML retains its **8,712 physical newline segments** so prior audit line anchors remain stable.
- [**Localization P0 CI 39087302655**](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39087302655): **SUCCESS** at the implementation commit, including **141 source-regression tests** and generator checks (3 locales, 6 generated artifacts, **0 stale**); independent Desktop and TTS workflows also passed. Android full CI and Backend targeted CI were **still in progress** when this note was written, so no claim of complete device/backend validation.
- The UI translations remain packaged in cacheable static JS; lookup performs **no extra per-string network call**. Source CI is not a substitute for real-device WebView, offline/cold-cache, paid/free/trial, multilingual UI visual, or authenticated account-switch QA; unresolved P0 legacy anonymous lesson content route remains outside this slice. No deployment or protected-branch merge.
- **Next:** stage remaining course UI keys by risk (simple labels vs trial/billing/assessment); map hard-coded UI text not yet in any catalog; verify all device/entitlement gates and then continue Android/Desktop adoption. Keep PR #179 Draft.

### P2 sixth UI adoption slice — 2026-10-18 (plan/trial/paywall display only)

- **Code:** [`09db876ea7f566891c203b1b909871188c0c2bf5`](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/commit/09db876ea7f566891c203b1b909871188c0c2bf5). Only `app/static/course-v3.html`, `tests/test_profile_limit_ui_contract.py`, `tests/test_i18n_common_ui_adoption.py` and `localization/baselines/reviewed_ui_changes.json` changed. The reviewed source git blob SHA was updated to the actual new source bytes.
- **9 additional keys in 11 UI sites:** `planTitle`, `planBody`, `planPay`, `planFree`, `trialOn`, `trialFail` (2), `trialCta` (2), `paySub`, `subscribe`. Reads use synchronous `courseMessage("key",existingValue)` with the **unchanged legacy original** fallback. All 27 locale/label pairs matched current source inline `I18N` for Uzbek, Russian and Tajik. Existing `course-v3.html` keeps exactly 8,712 `split("\n")` segments and source fetch anchors.
- **Recounted actual coverage from source**: **57 of 86** course UI catalog keys have active Mini App lookup sites, counting 5 dynamic `nav.*` keys from tab/tour; 29 keys not yet adopted. This is key coverage of the *course* catalog, **not overall app localization completeness**.
- Existing `isPaidUser()`, `TRIAL_STATE.eligible`, `trialEligible()`, `isLimitPaywallContext(ctx)`, server calls, trial activation, payment CTA actions, entitlement, lesson/grading, and progress persistence have **not** changed. The new bundle was already introduced in an earlier P2 slice; no new per-key HTTP requests or third-party dependencies.
- **CI root-cause fix**: earlier [Backend targeted CI 39087395995](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39087395995) failed because `tests/test_profile_limit_ui_contract.py` demanded the *obsolete exact* `var nickname=esc(PROF.name||t.you)` source expression. This code was intentionally changed in the previous localization slice to `var nickname=esc(PROF.name||courseMessage("you",t.you))`. The current test now explicitly expects the new expression and thus still protects preservation of user nicknames and fallback. The failing step was `Run advertisement placement, AI localization and default preset regressions`. Backend CI verdict on **this new commit** must be checked separately; fixing the stale expectation alone does not prove the entire backend green.
- Added `test_miniapp_reviewed_plan_trial_and_paywall_display_copy` to validate 9 count constraints, exact 3-locale text, line count and unchanged trial/limit gating branches. Source-contract and independent Android/Desktop/Backend CI must determine pass/fail on the new head; actual Telegram WebView/phone, new-locale, cold-cache/offline, account and payment QA remains outstanding. No production deploy or `main` promotion.
- **Next:** audit the remaining 29 unused course catalog keys, especially riskier grading and subscription/trial messages; expand reviewed non-gating display adoption and catalogue UI copy not represented by course keys. Keep PR #179 Draft and protect unrelated branches.

### P2 seventh UI adoption slice — 2026-10-18 (feedback and trial countdown)

- **Implementation commit:** [`9c097d2af79eeb39152c2799fc96e1e990f895b9`](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/commit/9c097d2af79eeb39152c2799fc96e1e990f895b9). Changed exactly `app/static/course-v3.html`, `tests/test_i18n_common_ui_adoption.py`, and the approved Mini App source SHA entry in `localization/baselines/reviewed_ui_changes.json`.
- **Seven additional reviewed UI keys / 21 display uses**: `correct` (9 references to top-level `T()`), `wrong` (6), `trialLeft` (1), `trialLeftHours` (1), `trialLeftSoon` (2), `lockedLesson` (1), `payTitle` (1). Three-locale byte-exact agreement with inline legacy `I18N` was verified for all 7 source values, including intact `{n}` placeholders for trial countdown. The per-feature `t.correct`/`t.wrong` strings owned by the mistakes review screen were **intentionally not replaced**.
- This migration changes **only presentation label reads** to the synchronous `courseMessage(key, oldValue)` lookup; the original fallback remains. In particular `c.correct_index`, `Flow.correct`, `Flow.graded`, `rememberLessonMistake`, countdown date arithmetic (24-hour/under-one-hour logic), `ctx==="lockedLesson"`, trial eligibility, checkout and paid/free entitlement predicates are unchanged. The Mini App HTML remains at **8,712 newline-split segments**; no source lesson files or external calls changed.
- Prior tests expecting those display keys to **never** go through the local catalogue were updated to instead reject dangerous key lookups (`answer_key`, `correct_index`, `payment_status`, `is_paid`); the new focused regression checks exact selected view-site counts, source label parity in all three locales, countdown placeholder consistency and unchanged grading/access branches.
- [**Localization CI 39088888703**](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39088888703) **SUCCESS**: **143 regression tests passed**, 86 source keys per locale, 6 generated course targets, **0 stale files**. Desktop and two local TTS workflows also passed. Android and Backend CI for this new commit were running when verified; do not infer their verdicts.
- **Current coverage** counted from actual active use sites: **64 of 86** Mini App course UI keys; **22 keys remain**. This is not whole-project UI localization coverage. Real Telegram WebView, cache/offline, cold-start, account switching and graded/paid user experience require manual QA. Previous Android CI [39088005015](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39088005015) failed **two existing VoiceScreenBackTest emulator root-window focus assertions**; this is an independently unresolved Android release gate (not established as an i18n regression). Existing public anonymous lesson JSON access audit remains unresolved.
- **Next:** audit remaining 22 nonwired source keys and untranslated hard-coded presentation fields, but do not infer they are safe to auto-wrap; some are feature-local `t.*` with different semantics. No `main` merge or production deployment, PR #179 remains Draft.

### P2 eighth UI adoption slice — 2026-10-18 (profile UI source extraction)

- **Implementation:** [`152dc7628a717c1b8d3a59028d774bb470cad835`](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/commit/152dc7628a717c1b8d3a59028d774bb470cad835) changed 16 files in the designated Draft PR branch: three canonical `localization/ui/{uz,ru,tj}/course.json` catalogs, six generated static local bundle/resource files (Mini App, Desktop, Bot Python, Android XML x3), course guard/build scripts, associated generator/guard/adoption tests, `app/static/course-v3.html`, and reviewed UI source SHA manifest. Added exactly **7 actual new source text keys**: `profile.free`, `profile.trial`, `profile.today`, `profile.overall`, `profile.pro`, `profile.answers`, `profile.note`. These map byte-for-byte to the three existing hard-coded `profileCopy()` locale dictionaries.
- `profileCopy()` now constructs a `legacy` copy and returns the same seven display fields by synchronous `courseMessage("profile.*", legacy.*)` lookup. **Existing visible content and original fallbacks are unchanged**, including Free/Pro badge semantics, account/subscription selection and accuracy score calculation. The 8,712 newline-split source line positions are unchanged. No new network-per-label API or lesson/grade/entitlement changes.
- Course source guard and generator unit tests were updated from strictly **86** to strictly **93** keys; they continue to reject duplicate keys, missing locales, invalid placeholders and forbidden grading answers. Six generated resources were rebuilt deterministically with no generator source-data mutation; native `-tg` qualifier continues to map to canonical source `tj`.
- **Cache correctness:** follow-up commit [`4f86e333a6f7ec51fb4f231935e4a08953bb8e73`](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/commit/4f86e333a6f7ec51fb4f231935e4a08953bb8e73) changes the Mini App course static bundle query from `20261017-course-v1` to `20261018-profile-v2`, with the matching source contract test and exact reviewed source blob. No new runtime request type.
- **Verified before cache-version follow-up:** [Local-first localization CI 39089629426](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39089629426) **SUCCESS, 144 regression tests**, 93 keys across 3 locales, six generated targets, zero stale. Desktop and local TTS checks passed for that commit. The cache-version follow-up has its own new CI run and must pass before final release approval.
- **Recount from actual use sites:** **71 of 93** canonical course UI catalog keys are referenced by Mini App runtime (including dynamic nav family); **22 existing keys remain non-adopted**. These remaining keys need individual semantic review: some are unused legacy copy or scoped submodule `t.*` labels with different meaning. No blind global replacement permitted. This is *course UI catalog* progress, not whole-project localization.
- **Release gates remain open:** authenticated Telegram WebView and device screen QA, offline/cold-cache language-switch QA, account switching, Free/Trial/Pro and HSK2/HSK3 content flows, public lesson JSON exposure audit, and Android Voice emulator focus failures from earlier runs. Production and `main` untouched; PR #179 stays Draft.
- **Next:** separately audit uncollected inline screen strings (profile/onboarding, dictionary, training) and prioritize another low-risk source extraction before touching graded lesson language overlays.

### P2 ninth UI adoption slice — 2026-10-18 (course picker, word display)

- **Implementation**: 5 actual newly extracted text keys `coursePicker.title`, `coursePicker.version`, `coursePicker.level`, `coursePicker.note`, `coursePicker.confirm` copied **byte-for-byte** from existing `coursePickerCopy()` Uzbek/Russian/Tajik inline literals. Mini App uses `courseMessage("coursePicker.*", legacy.*)` on each key; the existing course selection, progress, switching and unlock logic stays untouched. Also adopted **3 previously authored** exact locale-matching keys: `newWord`, `lessonDone`, `later` at their display sites. Physical `app/static/course-v3.html` newline segments remain 8,712.
- Source catalog expanded **93 to 98** keys/locale; regenerated **6** deterministic static files (Mini App JS, Desktop JS, Bot local Python, Android XML UZ/RU/TJ including old Android `-tg` locale adapter). Schema guard and two generator/guard test contracts updated to expect precisely 98 keys. Browser cache-busting static source URL changes from `20261018-profile-v2` to `20261018-picker-v3`; no per-label API.
- **Intentional exception**: Existing Russian lesson completion **subtitle** `lu.lessonP` is `Отличная работа! Следующий этап ждёт.`, while `course.lessonDoneSub` source says `Отличная работа. Следующий этап ждёт.`. To preserve exact existing visible copy, this key was **not activated**, and its canonical wording needs explicit editorial reconciliation before future adoption. No silent correction or grading semantic change.
- Source tests added for exact picker old/new locale copy parity and unchanged legacy fallbacks on word and done labels; existing guarded paywall/assessment constraints remain. **Local-first P0 CI, Android, backend, Desktop and device release gates must be verified on the final commit**; this paragraph is an implementation record, not a CI success claim.
- **Expected key adoption** on final branch code: **79 of 98** Mini App course catalog keys referenced at runtime (including five dynamic nav keys), **19 remain** for separate per-site review. This number is *not the whole app* localization coverage. No production deploy, merge or protected branch changes. PR #179 stays Draft.

### P2 tenth UI adoption slice — 2026-10-18 (login and blocked-account copy)

- [**Code commit `dbcdcb1a518654202fd436049d7b3c50e96053a2`**](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/commit/dbcdcb1a518654202fd436049d7b3c50e96053a2) adds exactly **6 UI copy keys** to each canonical `localization/ui/{uz,ru,tj}/course.json` catalog: `authGate.title/body/btn` and `blockedGate.title/body/btn`. All 18 authored strings match the existing localized `authGateCopy()` and `blockedGateCopy()` inline text **byte-for-byte**.
- Both functions retain their locale-keyed literal maps as fallback and only wrap three returned **display** fields with synchronous `courseMessage("namespace.field",legacy.field)`. Original `showAuthGate`, `showBlockedGate`, bot link, support action, auth gating, blocked status, API calls, account data, payment and entitlement checks are unchanged. The audited HTML preserves **8,712 newline-split segments** and all prior line-anchored guards.
- The approved Mini App bundle link changes from `20261018-picker-v3` to `20261018-gates-v4` to avoid stale cached JS; no per-label server lookups. The strict key guard and dependent tests expect **104** keys (up from 98), with six generated static outputs rebuilt from the same source: Mini App JS, Desktop JS, Bot local Python, Android `values`, `values-ru`, `values-tg`.
- Added `test_miniapp_login_and_blocked_gate_copy_from_local_assets` checking all six lookup sites and exact UZ/RU/TJ fallback parity, no access flow edits and current static asset version. [**Local-first localization CI 39102977978**](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39102977978) **SUCCESS**, **146 Python tests passed**, 104 keys for 3 locales, six generated targets and **0 stale files**. Desktop and both TTS checks also passed at this commit; Android full CI and Backend targeted CI were still running at time of last check and require independent confirmation.
- Source-driven recount: **85/104 active Mini App course UI keys**, **19 remaining**. Some unadopted keys are not actually read by current runtime, while `done` occurs in feature-local scoped dictionaries and differs in meaning. `lessonDoneSub` continues to have a different Russian source-vs-legacy exclamation-mark spelling; no forced adoption or silent copy change. **85/104 describes one course UI catalog, not project-wide translation completeness**.
- Browser/mobile authenticated/offline cache testing, account switching, subscriptions, device E2E and content security audit are not proven by source CI. No production deploy or `main` merge. PR #179 remains Draft; next work should audit standalone onboarding/settings/notifications screen strings and reduce duplicated runtime literal maps only once device and fallback compatibility are verified.

### P2 eleventh UI adoption slice — 2026-10-18 (Settings and notification confirmation)

- 8 new display keys were copied **byte-for-byte** from current settings mini-app inline UZ/RU/TJ dictionaries: `notificationsOff.title/body/keep/off` and `pinyinSettings.h/all/nw/off`. The course canonical source expands from **104 to 112 keys/locale**. Existing `App.confirmNotifOff` and `App.pinyinSheet` display copy through `courseMessage("...",legacy.value)` without altering current fallback texts.
- Generated 6 identical-contract static artifacts from this canonical source: Mini App and Desktop browser JS, Bot local Python, native Android default, `values-ru`, and `values-tg` XML. Strict key count and regression tests updated to 112; new focused test validates 8 lookup uses, original text in 3 locales, notification/pinyin side-effect anchors and browser asset version.
- Browser JS version query updated from `20261018-gates-v4` to `20261018-settings-v5` to avoid stale Mini App UI bundle. The underlying static download remains a single cacheable asset with **no network request per string**.
- Scope safety: actual `notifOn` toggles, `App.applyNotif(false)`, `/api/v3/notify` POST, `hsk_v3_pinyin` localStorage values, progress, grading, course level, permission, login and payments are unchanged. Source HTML remains 8,712 newline-split segments and original fallback text is still embedded.
- **Recounted catalog adoption anticipated:** 93/112 Mini App course UI keys used (five dynamic `nav.*` included), 19 pre-existing inactive source keys still deferred. This is NOT total product translation coverage. Notification schedule information body (`notifTimesHtml`), additional settings and onboarding remain separately authored; they are not implied to be migrated by this slice.
- [Draft PR #179](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/pull/179) retains unmerged status; final HEAD CI, authenticated Telegram WebView/offline language switching, entitlement flows, UI screenshots and Android app build QA remain distinct release gates. **Do not claim passing CI until verified on the new commit**. No `main` or production change.

### P2 twelfth UI adoption slice — 2026-10-18 (notification timing and avatar)

- **Source**: five new reviewed UZ/RU/TJ user-facing copy keys `notifTimes.head`, `notifTimes.item0`, `notifTimes.item1`, `notifTimes.item2` and `avatarEdit.note` extracted **byte-for-byte** from the current `notifTimesHtml()` and `App.avatarEdit()` inline sources. Existing legacy locale literals are retained as synchronous `courseMessage(...,fallback)` inputs. Nothing in the notification timing, notify toggle, avatar link, Telegram auth, permissions, payment or lesson logic was changed.
- **Catalogs**: source schema guard expands from **112 to 117 keys/locale**; 6 generated files have been updated (Mini App + Desktop JS, Bot Python, Android UZ/RU/TJ XML). Cache query `hsk-course-i18n.js?v=20261018-notif-v6` guarantees a new static asset is considered after deployment, with no new per-string HTTP requests.
- **Contract tests**: added exact 3-locale fallback-value comparison and five runtime call-site assertions, pinned HTML line segments to 8,712 and retained notification POST/avatar source anchors. Updated guard/generator tests to expect 117 keys. CI status MUST be verified on the code commit; this note is not a CI-passed claim.
- **Projected use-site coverage** after this code commit: **98 of 117** course UI catalog keys active, 19 old inactive keys remain with semantically different or unused original copies. This is not whole-project UI localization.
- **Release status**: [PR #179](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/pull/179) remains Draft. Device/WebView smoke, offline and cold-cache, locale switches, free/trial/paid login states and release authorization are outstanding. No `main` merge or production deployment. The repository graph report predates this feature branch and needs a local `graphify update .` when running in a checked-out worktree.
- **Next**: audit other non-gating onboarding/Settings text, and distinguish unused course catalog keys from active UI copy before renaming or activating them.

### P2 thirteenth UI adoption slice — 2026-10-18 (course and practice recovery screens)

- Seven literal UI labels were copied exactly into each of `localization/ui/{uz,ru,tj}/course.json`: `courseLoadError.title/body/btn` (3), `practiceAuthRequired.body/retry` (2), and `practiceGateError.body/retry` (2). All 21 new locale values match the three current `app/static/course-v3.html` inline dictionaries exactly.
- The three existing screen/render functions now return display text through `courseMessage("...",legacy.X)`, retaining the original in-code fallback. This does not change `showCourseMapFailure` branching, access verification `validatePracticeGate`, server-side quota/entitlements, `location.reload()`, course reload action, Telegram login, payment, scoring or progress mutation.
- Strict source catalog guard and generator regressions advance from **117 to 124 course UI keys per language**. Six deterministic local output resources regenerated for Mini App JS, Desktop JS, Bot Python and Android XML (UZ/RU/TJ). The HTML references `hsk-course-i18n.js?v=20261018-errors-v7` to invalidate stale browser cache, with no per-string network requests.
- Added a focused unit regression covering exact call-site usage, per-locale string parity, source physical 8712 newline segments, retry triggers and access decision paths; source audit checksum updated. Existing semantic-safety exception for `lessonDoneSub` remains unchanged. This is a static text migration; do not mistake it for completion of authentication/checkout QA.
- **Release gates:** CI success must be established separately on this new commit. Automated static tests are not a substitute for real-device Telegram WebView, offline/cache switch, valid/error auth states, Free/Trial/Pro and Android build/manual smoke. PR #179 remains Draft, `main` and production are untouched. Local `graphify update .` is required from a full checkout to refresh the graph after changes.

### P2 fourteenth UI adoption slice — 2026-10-18 (HSK level picker)

- Eight per-locale strings were copied **byte-for-byte** from the `App.levelPicker` legacy inline UZ/RU/TJ `sub` dictionaries to `localization/ui/{uz,ru,tj}/course.json`: `levelPicker.hsk1`, `hsk2`, `hsk3`, `hsk4`, `nhsk1`, `nhsk2`, `nhsk3`, and `title`. Runtime returns the same description/title values through `courseMessage("levelPicker.X",legacySub.X)` with exact static fallback.
- Strict catalog expands from **124 to 132 keys per locale**, without changing lesson content, grading, native locale alias, saved level, HSK 2.0/3.0 track, `App.pickLevel`, `loadLevel`, paywall, auth or payment. The source HTML still contains **8,712 newline-split segments**, preserving existing audit anchors.
- All six static generated resources (Mini App JS, Desktop JS, Bot Python, Android XML default/ru/tg) updated consistently. Guard/generator tests now require 132 reviewed source keys; source-regression test checks the eight use sites, three locale literal-value matches and unchanged routing/selection invariants. Mini App static script version increments to `20261018-levels-v8` to avoid stale cache, without additional per-string requests.
- **CI and device caveat:** the preceding commit [`0f7177dd`](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/commit/0f7177ddf81785aa99b05a8b548da2927e86c8fa) passed localization, backend, desktop and TTS jobs but Android CI failed two `VoiceScreenBackTest` Android emulator root-window focus tests; it did not change Voice implementation. These two emulator regressions are an outstanding Android release gate until reproducibly verified. **CI on this new code commit must be checked separately**; HTML source guards are not actual Telegram WebView/mobile/paid/offline QA.
- Expected source-level active coverage after this change: **113 of 132** course UI keys referenced in Mini App (five dynamic navigation labels included); the pre-existing **19 unadopted/semantically nonmatching keys remain**. This ratio is the course UI catalog only, *not* whole-product i18n completeness. No production deployment or `main` merge; PR #179 remains Draft.
- **Next:** audit remaining onboarding/Settings language duplicates, then run full manual multilingual device/Telegram WebView/cache and entitlement regression gates before any rollout.

### P2 fifteenth UI adoption slice — 2026-10-18 (beginner intro and grammar tutor)

- Added 10 byte-identical original UZ/RU/TJ UI labels from `GRT()` and `BST()`: grammar tutor `teacher/structure/negation/next/done/intro`, beginner intro `kicker/voiceOn/voiceOff/replay`. Local static lookup keeps the original dictionaries as fallback, with no change to grammar parsing, beginner flow, scoring, audio toggles, state persistence, access or payments.
- Canonical course UI catalogs expand 132→142 keys per locale. Six generated static resources and contract tests updated; browser JS asset version `intro-v9`; no per-label server fetch. HTML physical lines remain 8,712.
- Source regression verifies 10 lookup uses and 3-language parity. CI and real Telegram WebView/Android/offline/Free-Pro gates must be verified separately before any release. PR #179 stays Draft, `main` and production unchanged. Graphify update requires checked-out workspace.

### P2 sixteenth UI adoption slice — 2026-10-18 (one large 30-key finish/streak batch)

- One contiguous **30-key** reviewed catalog batch spanning four existing UI dictionaries and two standalone strings: `partSections.{w,p,s,r,d,x}` (6), `levelUp.{cont,lessonH,lessonP,cpH,cpP,acc,combo,levelH,levelP,opened,xpH,xpP,lvl,bonusXp,chest}` (15), `levelStats.{xp,acc,time}` (3), `streakDisplay.{one,few,many,cont}` (4), `writerLoading` (1), and `nextLessonOpen` (1). Locale copy comes directly from existing inline source without modifying UZ/RU/TJ visible messages; all 90 locale/key pairs are reviewed.
- Canonical course UI source expands **142→172 keys per language**; Android three XML resources, Mini App and Desktop static JS, and Bot local Python generated consistently (6 assets). Existing source guard and generator regression test expected counts updated to 172. Source-only regression added validating exact source fallback values, a reviewable 30-label family, two next-lesson CTA occurrences, one writer loading use, guarded flow source invariants, and 8712 HTML newline-split segments.
- The source keeps original dictionaries as fallback and wraps *display-only* values with `courseMessage(key, fallback)`, with no per-key network requests; browser JS resource URL updated `intro-v9` → `finish-batch-v10`. `Flow.graded`, `c.correct_index`, checkpoint bonus, level reveal, streak arithmetic and states, course navigation, entitlement, account or payments were not intentionally changed.
- Explicitly **not** adopted: prior `lessonDoneSub` source value (Russian punctuation does not match current runtime `lu.lessonP`), unrelated source keys or course/lesson content translation overlays. This newly authored `levelUp.lessonP` is exact current runtime text, not a silent alteration of `lessonDoneSub`.
- This is a source/CI checkpoint, **not** confirmation of runtime WebView/offline/cold-cache/device/account switching/paywall QA. Keep PR #179 Draft, `main` and production unmodified. Check the exact new-commit CI verdict before promotion; Android emulator focus failures in older runs require independent reproducibility checks.

### P2 sixteenth slice stabilization — 2026-10-18

- CI root cause from 30-key source batch: [P0 run 39127812243](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39127812243) had **1 failing source regression**, `test_existing_three_locale_172_key_contract`, because `levelUp.cpH` introduces a new `{n}` placeholder beyond `trialLeft` and `trialLeftHours` while the guard test still expected count 2. Source string and generator contracts were correct; this is a stale test expectation, not observed runtime damage.
- [Fix commit `de2cdeac`](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/commit/de2cdeacfe84707711ddd50c811251c19fd37629) changes **only** `tests/test_i18n_course_ui_catalog_guard.py`: asserts 3 placeholder keys **and exact identifiers** for all three locales. The resulting [P0 run 39128025783](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39128025783) is **SUCCESS with 152 tests**, strict 172 keys × 3 locales, six generated assets, zero drift. Desktop and two TTS runs were also SUCCESS on this SHA; separate Android and Backend workflow conclusions must be checked live.
- Actual Mini App source lookup coverage recalculated at the passing code commit: **153 of 172 keys**, 19 source keys remain unmatched or intentionally not adopted due to context/locale differences. Continued work should prioritize larger **20–40 exact-safe UI source label batches**, then cross-client true runtime adoption and versioned local lesson-content overlays, subject to proper device/paywall/auth and content-security release QA.
- Repo handoff: `localization/NEXT_CHAT_HANDOFF.md` is the canonical continuation pointer; **PR #179 remains Draft**, `main` and production untouched. Keep branch history intact; graphify update needs a checked-out workspace (not available via this GitHub connector-only transaction).

### P2 seventeenth UI slice — 2026-10-18 (31-key onboarding)

- Added 31 reviewed byte-exact onboarding UZ/RU/TJ field translations under `onboarding.*`. Course UI sources become **203 keys per locale**, generating 6 local resources unchanged in format for Mini App, Desktop, Bot and Android UZ/RU/TG.
- The Mini App onboarding displays values from static `hsk-course-i18n.js?v=20261018-onboarding-v11` where available, with all original inline translations retained as local offline fallback. No account/HSK track/billing/Pro/trial/grade/progress logic change.
- Regression guards verify all 93 legacy labels, generated resource parity, reviewed source SHA, strict key count and source flow anchors. CI on new SHA, device WebView, Android/Desktop/Bot runtime use, offline/cold-cache and security assessment remain separate gates. PR #179 Draft and production/main unchanged.

### P2 Android runtime onboarding adoption — 2026-10-18

- Native `OnboardingCopy` UZ/RU/TJ text matched the generated Mini App source **for 23 of 30 mapped onboarding fields**; these 23 are now loaded from existing `hsk_course_onboarding_*` Android XML by app-selected language via isolated Configuration context (tg for Tajik). Original Android text remains the fallback; seven unmatching fields intentionally remain legacy.
- Added precise Android source/resource mapping regression. No account/checkout, HSK track, consent, notification, XP, grading, progress or API behavior modified. Do not infer Android build/device QA success until CI and manual locale-switch/offline tests complete.

### P2 eighteenth UI adoption slice — 2026-10-18 (25 onboarding values)

- Onboarding level choices 9 and study goals 10 were copied exactly per UZ/RU/TJ from current Mini App `LV20/LV30/GOALS` display dictionaries; six native Android onboarding notification primer labels were copied from `OnboardingCopy`. 25 keys per language added to `course` source (203→228), yielding 6 static outputs.
- Onboarding option values prefer preloaded cached JS only for display with original text as fallback. Native Android notification titles/buttons use existing app-language XML adapter and original constructor text as fallback. No per-string HTTP, no account/paywall/progress/HSK selection IDs/callbacks/payment edits. Cache `onboarding-options-v12`.
- Regression tests check 25 UZ/RU/TJ parity pairs and source/runtime call sites; HTML source reviewed Git hash advanced. CI and device QA must be verified on new SHA, no implicit release. Keep main untouched and PR #179 Draft.

### Android native onboarding option adoption — 2026-10-18

- Android `LevelChoices` adopts seven existing exact-safe HSK description XML resources and `GoalChoices` adopts all ten goal title/description XML resources. Original native locale lists/maps remain fallbacks; the selected HSK/goal IDs and state callbacks are unchanged. Android-only beginner wording remains untouched by design.
- App-language-pinned `Configuration` reads (tj/tg compatibility) with no per-string API. Added source/native three-locale parity regression. Android CI and actual language/offline/mobile QA still need independent confirmation; no main merge or production deploy.

### P2 nineteenth UI batch — Test Center 49 static copy labels (2026-10-18)

- Extended `course` UI catalog from 228 to **277 key/locale** by moving exactly 19 Test Center hub labels, 17 exam runner labels, 3 exam section titles, 6 placement UI labels, 3 HSK 3.0 placeholder labels and 1 personal-level badge; **147 UZ/RU/TJ source/display values** preserved, all six generated outputs synchronized.
- `app/static/course_v3_test.html` loads a cacheable static catalog before its inline runtime; `L`, `EM`, `EM.sec`, `PT`, `HSK30_SOON` and `MINE_T` prefer static values and use the unmodified inline literals as fallback. No network-per-text, and no change to exam questions, answers, server grading/access, payment, progress, XP, or placement algorithm.
- Review manifest pins the new source Git blob. Added exact locale parity, runtime lookup and gated test-source invariants; P0 CI now includes test file and updated 277-key strict contract. This is source adoption, **not** device Telegram WebView/offline or paid/free release QA. PR #179 stays Draft; main/production untouched.

## Recognition: exact-copy 10-label UZ/RU/TJ UI adoption (2026-10-18)

- Recognition display dictionary `L` prefers local static generated course UI copy with existing literals as fallback. Central `course` UI catalog counts **287 keys per locale**. Six generated outputs include offline Android, Desktop and Mini App/Bot source artifacts; strict reviewed Git source SHA and regression added. This is UI text routing only — no change to grade, word source, free daily-gate, Pro, ads or APIs. Test on real devices before merging.

## Mistakes + Pronunciation display UI runtime adoption (2026-10-18)

- Reviewed 53 Mistakes display labels (including cats/sources nested groups) and 22 Pronunciation labels, exact UZ/RU/TJ string parity, 287 → **362** locally bundled course UI keys per locale, six deterministic generated platform outputs. Both pages preload one local JS bundle and retain every original inline literal as fallback. Locale/placeholder/contract/Node runtime regression added to P0, source Git blobs pinned; user data, server scoring, audio/STT, Pro, progress and daily access not modified. PR #179 Draft; device QA and fresh CI confirmation required.

### Android UI resource-name normalization collision correction (2026-10-18)

- Original `mistakes.sub` and existing unrelated `mistakesSub` both collapse to `hsk_course_mistakes_sub`; changed the new Mistakes display-only family to `mistakesPage.*` for all 53 labels to preserve the generator's fail-closed uniqueness invariant without changing existing shipped resource names. Four original localized placeholders (`reviewCount`, `reviewCat`, `progress`, `resCleared`) raise expected placeholder-bearing keys from 3 to 7. All locale/display values and Mistakes original `L` fallback unchanged; source Git blob review updated, generated outputs and CI tests regenerated.

## Voice + Memorize limit + Dictionary UI adoption (2026-10-19)

- Centralized 65 exact display-only UZ/RU/TJ strings: Voice 47, Memorize paywall sheet 4, Dictionary practice cards 7, Dictionary character-memory headings 7. The `course` UI catalog rises from 362 to **427 keys/locale**, and six offline/local platform resources are regenerated deterministically. New static JS preloads and synchronous hydration retain original inline fallback. Dictionary keeps all 3 locale dictionaries hydrated for instant language switches. Source HTML Git blob SHAs are explicitly reviewed and Python/Node regression is in P0. No audio, grades, gating, paywall, voice sessions, dictionary search/index or course content logic changed. PR #179 Draft, no `main` merge; device QA is still required.

## Ready Phrases and public Apps Download local-first adoption (2026-10-19)

- Centralized 15 UI-only Ready Phrases labels and 79 flat public Apps Download labels, exact original UZ/RU/TJ literal parity; catalog now **521 reviewed keys per language**, six generated static platform resources. Both pages preload one same-origin cacheable JS catalog with byte-identical old inline fallback; download page loads both scripts with `defer` in deterministic DOM order. Nested download installation instructions and referral arrays remain original. Added strict source blob review, source parity and Node runtime regression to P0. No changes to phrases search/corpus/storage, download state/release API/installer routes, subscriptions or user entitlements. PR #179 Draft, test on devices before release.

## Subscription UI-only exact-source adoption (2026-10-19)

- Adopt 102 simple top-level per-locale subscription display strings from current inline I18N dictionary, UZ/RU/TJ byte-equivalent, into local `subscriptionPage.*` keys. Source catalog 521→**623** per locale, 19 total named-placeholder keys. JS bundle loads synchronously before original inline dictionary and is read once across all 3 languages; all literals retained as synchronous fallback. The change is text-only, never backend entitlement, pricing, referral, payment, receipt, plan calculation, region, secure data, navigation or API behavior. Strict source Git SHA pins, Node runtime parity, CI and 6 generated platform outputs required; real checkout paths need manual QA before merging.

### Subscription nested UI exact-source adoption (2026-10-19)

- Original nested benefits, focus, payment/country display labels and plan naming strings: +79 UZ/RU/TJ text values, total **702 course catalog keys per locale**. Source keeps all original arrays/IDs, locale fallback and literal values, while resolving bundled static resources synchronously. No changes to plan prices, billing, verification, receipt, bank details, entitlements, referrals or server requests. Added Node/frozen-SHA regression, updated strict catalog test counts, and regenerated all 6 Mini App/Desktop/Bot/Android local resources. Requires P0/Android/Backend CI and real manual checkout path QA before PR merge.

## Dictionary 29 remaining display labels: local-first exact-source adoption (2026-10-19)

- 20 main Dictionary static strings, 7 fast stroke writer static labels and 2 standard stroke writer status strings adopt UZ/RU/TJ local generated course keys (731 per locale), preserving inline literal fallback. Main dictionary counts and stroke label functions unchanged. HTML physical line count remains 1898; source SHA review and Node offline/override source regression, six deterministic generated resources, P0 CI updated. No word/search/level/filter/audio/storage/user state changes. Real WebView/desktop/Android QA still required prior to merge.

### P2 Main Course Voice embedded UI exact source adoption — 2026-10-19

- In `app/static/course-v3.html`, 60 `VOICE.LD` labels + 3 `VOICE.LIVE_TEXT` labels (63 keys × UZ/RU/TJ) now use `courseVoiceInline.*` bundled static course UI resources when available, retaining all exact original inline literals and three-language fallback when resource is absent. Load once before module; no per-label server traffic. Catalog **794 keys per locale** and six platform bundles deterministic.
- Added source/fallback/Node runtime regression, Android resource collision protection, strict frozen source SHA review and 20-placeholder signature contract (including `courseVoiceInline.turnOf`). Original Voice mic, Live, STT, TTS, playback, API, AI prompts, grade, saved mistakes, limits/Pro and progress remain unchanged. `course-v3.html` line count 8712 preserved. Device and emulator QA still required; PR #179 remains Draft, main/production untouched.

### P3 source-bound display overlay contract proof (2026-10-19)

- Narrow private in-memory overlay schema: explicit whitelist for simple display text only (13 path templates). SHA-256 of full source lesson JSON plus `level`, `lesson_id`, `part_no`, required to apply overlay. Strict locale parity for UZ/RU/TJ, no fallback to wrong language, stale lesson and unreviewed/answer path rejection. Two real HSK 2.0/3.0 first lessons used as CI test data (51 and 43 display maps). **No shipped lesson, static public pack, route, auth, token order, scoring, entitlement, storage or cache change**. Next: audit all seven tracks and access boundaries before designing actual authenticated/packaged lesson overlays; keep P3 runtime NOT STARTED.

### P3 first-and-last source overlay readiness audit (2026-10-19)

- Added read-only `scripts/i18n_lesson_overlay_readiness_audit.py` and P0 regression over **14** first/last lesson source files across **7** tracks. Each reviewed display source is still version-bound with SHA-256 and validated UZ/RU/TJ locale parity; grade/answer contents and reverse-builder tokens are deliberately excluded from report values. **13 source samples valid, 1 deliberately blocked**: `nhsk2/lesson_73.json` grammar examples contain 9 three-locale empty `translation` objects. Overlay contract rejects blank data, so real P3 migration cannot proceed across all sample lessons until the source content is separately authored/reviewed. CI emits count-only `p3-overlay-readiness.json`, not a static locale pack. No source lesson, clients, access, server or grading was changed. Full 746-file audit and real-device/authenticated transport QA remain open.

### P3 all-course structural overlay inventory (2026-10-19)

- A new **read-only full scan** covers all 746 existing lesson files across seven tracks; source identities, reviewed UZ/RU/TJ display-map completeness, assessment/reverse-builder exclusion, and in-memory SHA-256-bound overlay parity are analyzed without changing lesson content. Only safe issue names and lesson numbers are logged for blocked cases. The CI artifact `p3-all-lesson-readiness.json` is structural, NOT a language bundle or private test-answer leak. Prior first/last 14-file baseline test remains unchanged. Runtime P3 remains NOT STARTED; inspect actual CI results and unblock human translation/Pro/transport reviews before rollout.

### Verified P3 full inventory & separate human translation queue (2026-10-19)

- The all-course P0 report (`b447aac`) finds **746 source files; 698 structurally ready, 48 blocked; 272 all-empty UZ/RU/TJ reviewable display maps**. Blockers are **only in `nhsk2`**. No missing/partially-empty locale-key map shapes were found by this path-whitelist audit. There are **2,094 validated in-memory overlays**, 324 intentionally excluded reverse-builder cards and 7,153 grading field occurrences counted, never serialized as grading values. `localization/reviews/p3_nhsk2_locale_gaps_20261019.json` tracks safe lesson-number/field counts for human translation review. It is a snapshot, not a production payload. Keep P3 runtime NOT STARTED until all locale values are authored, source-bound caches secured, and API entitlement/assessment protections verified with device QA.

### P3 content-editor pointer queue (2026-10-19)

- Added a fail-closed, report-only generator for **exact JSON pointer paths** to missing reviewed display translations across all seven HSK 2.0/3.0 source directories, plus each source's Git blob SHA-1. CI validates all 746 sources against the verified **48 nhsk2 lesson / 272 empty map** human summary and emits artifact `p3-locale-gap-pointers.json` (816 per-locale missing text cells), never lesson/answer values. Strict tests cover safe whitelisted pointers, changed source SHA, missing/partial maps, and report redaction. Production course content, scoring/Pro flows and P3 runtime remain unchanged; editors must manually author and verify UZ/RU/TJ strings in approved source before release.

### P3 editor-draft structural validation boundary (2026-10-19)

- Private editor drafts contain original lesson file path + Git blob SHA1 + exact display JSON pointer + all 3 manually authored UZ/RU/TJ text values; fail on stale source, noncanonical track/file, previously nonblank display maps, unsupported locale, answer/grade/reverse-builder pointer, malformed text or unexpected fields. CLI emits no lesson values and never edits source; optional private in-memory deep-copy preview exists for editor review, never published. Schema and running instructions: `localization/reviews/P3_EDITOR_DRAFT_SCHEMA.md`. P0 regression covers all negative cases. Passing structural validation does NOT mean translations were authored, human-reviewed or approved; P3 runtime is not enabled. Content auth, old/new client QA and 48/272/816 gap remediation remain open.

### P3 multi-editor local draft coverage validator (2026-10-19)

- Add no-side-effect batch validator over a private folder of approved-editor JSON drafts, using exactly the existing source SHA/pointer/locale rules. Supports incremental work or strict `--require-complete` 272/816 structural coverage, rejects duplicates, symlinks, stale SHA and drafts inside the Git checkout. Output is only safe counts/status, never values; even complete structural validation does NOT authorize translation publishing, lesson runtime, Pro entitlement or shipping. Original 746 lesson JSON and client/server behavior remain identical. See `localization/reviews/P3_EDITOR_DRAFT_SCHEMA.md`; CI regression module `tests.test_i18n_editor_translation_batch` added.

### P3 editor-preview full-tree invariance attestation (2026-10-19)

- Add separate private in-memory integrity verification after editor draft
  structural validation, before any content integration. Compare a proposed
  lesson preview to the exact pinned original JSON: restore **only** the
  explicitly approved previously blank UZ/RU/TJ maps and type-compare the
  entire remainder, rejecting any grading/correct_index, builder answer,
  option order, Chinese/pinyin, lock/Pro, unexpected key or unreviewed
  translation mutation. Return only structural counts; never return or
  publish translated strings/source answers through this proof. Tested
  with positive/adversarial synthetic payloads in P0, no runtime adapter,
  no lesson source writes. Human translation approval/entitlement/manual
  QA still pending; P3 runtime NOT STARTED.

### P3 HSK 3.0 Level 2 lesson-16 human worksheet pilot (2026-10-19)

- New private-only CLI `scripts/i18n_grammar_editor_workspace.py`: safely select a canonical existing lesson and ONLY original already-empty UZ/RU/TJ grammar-example display maps. Produce an editor worksheet with Chinese grammar-example sentence/pinyin and original Git blob SHA, plus separate blank editor draft with six JSON pointers for nhsk2 lesson 16 (18 human-translation cells). Files stay outside checkout (private 0700/0600), no overwrite/answer/Pro disclosures to public CI or CLI. Blank draft must FAIL existing validator until authored. P0 tests include real lesson-16 coverage, safe synthetics and source immutability. Do not mistake worksheet setup for translation quality approval or completed content; runtime remains NOT STARTED.

### P3 duplicated _grammar course-card mirror discovery (2026-10-19)

- Root `nhsk2/lesson_16` has six blank main grammar translations AND six duplicated blank runtime `_grammar` card translations. Extended **private only** editor worksheet with an informational `mirrored_paths` array per root pointer; fail-closed on mismatched `_grammar` original `zh` or locale map. The human editor still authors only six UZ/RU/TJ triples; no duplicate strings should be translated separately. The existing source-bound in-memory preview intentionally does NOT touch mirrors; real integration must be a separate authorized atomic sync with full grade/Pro/client checks. New synthetic tests check mirror discovery + mismatched mirror fail-closed. No source lessons, P3 runtime, Pro/payments or main branch changed.

### P3 grammar/card mirror-safe preview attestation (2026-10-19)

- `scripts/i18n_editor_grammar_mirror_integrity.py` extends private reviewed grammar translations to source-verified `_grammar` card display mirrors on a detached in-memory copy only. All other fields including scoring, `reverse_builder`, Chinese/pinyin, Pro/locked flags, grades and source identity are compared type-sensitively and cannot change. Duplicated/mismatched mirror original data fails closed. On `nhsk2` 16, six source translation maps and six mirrored maps use the same 18 UZ/RU/TJ editor strings. Never export source/preview/answers. P0 tests exercise real source and synthetic adversarial mutations. Human language approval and runtime/auth/device QA remain open, with P3 runtime NOT STARTED.

### Source-wide `_grammar` mirror audit: 746 numbered HSK lessons (2026-10-19)

- The read-only `scripts/i18n_grammar_mirror_source_audit.py` scans all seven tracks, counting original grammar groups, `_grammar` display duplicates, matching and blank mirror translation maps, and structurally divergent/orphan/duplicate mirror cards. Report only contains safe filenames, issue names and counts; original Chinese, pinyin, localized strings, answer options, scoring and Pro metadata are **never serialized**. Integrated with `tests.test_i18n_grammar_mirror_source_audit` and P0 report generation. This is a pre-integration audit, not a replacement for mirror-aware private in-memory preview verification or auth/device QA. If new divergence is found, remediate separately before any source translations are applied.

### Seven-track duplicate grammar source audit — do not retranslate exact contexts (2026-10-19)

- New `scripts/i18n_grammar_translation_reuse_audit.py` creates a redacted report for human editorial batching: groups originally blank UZ/RU/TJ grammar-example display maps by exact Chinese source, pinyin, grammar `no`, title, `title_zh` and rule. It emits only source file locations, indexes and counts. 20th nhsk2 lesson's 12 examples are exact repeats of 16 (6), 17 (3), 18 (3), so those three draft sources can be re-used as an **unapproved private editor draft** for lesson20 with its own Git blob SHA. The audit reports count of distinct contexts to target human-review effort; human linguistic signoff, source integrity, Pro safety and manual QA remain mandatory. No source modification, no runtime integration.

### P3 safe grammar translation reuse generator (2026-10-19)

- Audit baseline: 746 lessons, 272 original blank grammar maps, 136 distinct exact contexts, 136 source repeats, 136 additional blank `_grammar` card mirrors, no divergence. Only 408 independent locale texts may need authoring, but 816 target locale placements remain.
- New `scripts/i18n_editor_translation_reuse.py` converts SHA-validated private source drafts into a private target draft only after exact Chinese/pinyin/title/rule/grammar-no equality, conflict checks, all target gaps covered and protected full-source in-memory mirror integrity. Lesson20 can reuse 36 locale cells from 16/17/18. Editor content and preview must never be exposed as static/browser assets; no content integration or runtime changes. Tests in `tests/test_i18n_editor_translation_reuse.py` and P0.
