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
| Full reviewed inventory/baselines (P0) | NOT STARTED | pending |
| Generated canonical catalogs + validators (P1) | NOT STARTED | pending |
| Platform runtime migrations (P2) | NOT STARTED | pending |
| Versioned lesson locale overlays (P3) | NOT STARTED | pending |
| Any new language enabled (P4) | NOT STARTED | prohibited until gates |

For each implementation commit, update the relevant milestone with:
**commit SHA, exact files, passing tests, known gaps and next action**.
Never claim tests were run unless CI/logs or local results confirm it.
Keep GitHub's branch current without force-resetting unrelated user work.
