# HSK AI — local-first localization work branch

**Status:** local-first UZ/RU/TJ implementation is in progress on the integration feature branch; no main merge or production release.
**Active branch:** `codex/p3-main-integration-20261020` (centralization code `930d4f70`; 436 local P0 tests, all read-only workflow checks and 52 deterministic artifacts passed; new GitHub CI pending push. Current remaining code work/evidence: `localization/RESUME_NEXT_CHAT.md`).
**Main starting point:** `160a51d69f3324e3162375213ec61b5587b19533`.
**Source-of-truth decision:** edit translations once in GitHub; build **separate local artifacts**
for Android, Mini App, Desktop and Python bot/backend. No per-string translation API.

**Primary continuation checklist and phase/status ledger:** `localization/PLAN_SCHEMA_ORDER.md`.
This document is an execution plan, NOT a claim that the migration is done.
Previous architectural context: `docs/I18N_MULTILANGUAGE_MIGRATION.md`.
Surface register: `localization/surface_registry.json`.
Current locale manifest: `localization/manifest.json` (explicitly preparation-only).

## Non-negotiable invariants

- Keep existing `uz/ru/tj` UI/content and legacy API/DB language values working.
  Normalize display language `tj <-> tg` at one compatibility boundary;
  do not blindly rename DB/API values. Treat `zh-Hans` as **source learning content**,
  not the learner's UI language.
- Zero runtime per-UI-string backend/API calls. Android resources bundled in APK;
  desktop JS resources bundled in Tauri; Mini App localized JS/JSON published as
  **versioned static files** with cache (first download/revalidation still uses HTTP);
  bot and notification templates read from local Python artifacts.
- Do not promise full Mini App offline from HTTP caching alone. Confirm WebView
  behavior and separately design offline if required.
- Retain Chinese source, pinyin, audio source IDs, card IDs, quiz answer identities,
  order, achievements, course progress, leaderboard/XP, user history and old
  serialized lesson envelopes.
- **Pro content and assessment security:** public static assets are observable
  and can be copied. Audit the current public lesson JSON route before moving
  paid material into static packs; keep entitlement and grading on the backend.
  Never generate public complete exam answer keys.
- No new language is selectable before all active content and UI for that
  language is authored, reviewed, validated and regression tested.
- Preserve direct vs Play payment wording and flows, account authentication,
  trial/provisional Pro states, purchases, notifications and bot callback routing.
- Do not force-push/reset `main`, `codex/local-ai`, or `codex/cloud-ai`.
  This branch is isolated: do not auto-merge its work into `main`.
- Admin-only copy, user-supplied/LLM text and third-party content require
  separate classification; do not silently translate arbitrary input or logs.

## P0 — inventory and baseline freeze (first execution milestone)

1. Extend `scripts/i18n_inventory.py` to cover actual data producers:
   embedded HTML/JavaScript dictionaries, Compose literals, Python replies,
   notifications, Android flavors, generated dictionary/phrase assets, lesson
   overlays, exercises, accessibility metadata and dynamic error fallback.
   The current regular-expression scanner misses many JavaScript object values
   and deeply-generated source content. Track such gaps explicitly.
2. Produce machine-readable evidence: source path, line or JSON path, source
   type, requested locale, namespace, classification, migration state,
   placeholder variables and `translatable=false` exceptions.
3. Produce a **reviewable** inventory baseline in a bounded artifact outside
   build outputs. Report per-surface totals, coverage, missing locales,
   duplicated key intents, mixed-language and suspicious neutral fields.
   A scanner candidate is not proof of user-visible behavior.
4. Snapshot existing 3-language strings and sample lesson rendered outputs
   before any migration; preserve test fixtures for all 7 course level tracks.
5. Establish a test policy that rejects new unclassified *user-facing* literals
   without flagging Chinese text, pinyin, IDs, logs or admin-only messages.
6. Check the security implications of the existing anonymous static
   `/course_v3_data/{level}/lesson_*.json` endpoint before package design.

**Done only when:** a reviewer can locate every known UI/content source
group from `surface_registry.json`, review exceptions and run the report
repeatably. This is a necessary baseline; it does not yet prove 100% detection.

## P1 — source-of-truth format (first engineering milestone)

- Create `localization/ui/<locale>/<namespace>.json` with stable keys, a
  translation context and placeholders. Namespace ownership must be explicit.
- Define a stable `content_id`/field-path contract for lesson learner text,
  without reindexing existing progress, tests or answer IDs.
- Build lint for key completeness, placeholder equivalence, JSON/XML safety,
  locale-aware plurals, RTL support and accidental wrong-language fallback.
- Choose deterministic build output and content/version hash for each target,
  with a manifest for package compatibility and cache busting.
- Keep existing catalogs as fallback until feature-specific parity tests pass.

**Done only when:** a sample `common`/`errors` namespace can be edited once,
validated and deterministically emitted to Android, Mini App, Desktop and Bot,
without any new runtime per-string network request.

## P2 — incremental adapters and target migration

1. Android: generated `strings.xml`/`plurals.xml` for each supported locale;
   maintain `direct`/`play` overlays; eliminate duplicate Kotlin UI dictionaries.
2. Mini App: generated versioned static catalog; replace per-page dictionaries
   incrementally and preserve bfcache/startup, offline fallback and safe HTML
   escaping. Never add a network fetch for every string.
3. Desktop: switch `desktop/ui/js/i18n.js` to generated local bundles, with
   tested parity on Windows EXE and macOS DMG.
4. Bot/backend: replace scattered fixed strings with local resource reader;
   keep asynchronous notification format, original language preference, and
   previously stored human/campaign copy behavior intact.
5. Course translation: source JSON plus locale overlays, generated compatibility
   envelopes. Update generators, including reverse-builder word tiles, using
   locale-aware rules; retain answer keys and per-card IDs.
6. Dictionary/phrases: produce locale-specific cacheable static data without
   adding server-side dynamic translation work to read paths.

**Done only when:** each active UI surface reads its generated local catalog,
all 3 existing languages match frozen behavior, and lessons/entitlements are
independently validated. Do not delete legacy sources before client rollover.

## P3 — source-bound lesson locale overlays

Existing UZ/RU/TJ display translations are checked against Chinese context and
integrated through source-bound overlays after the existing account/lesson
access decisions. Original Chinese, pinyin, answer identity, grade and progress
remain protected. Current implementation and verification are tracked in
`localization/RESUME_NEXT_CHAT.md` and `localization/PLAN_SCHEMA_ORDER.md`.

## P4 — optional fourth language launch gate

All enabled levels, onboarding, subscriptions, failures, notifications,
accessibility, offline/cached states, bot and live client targets must pass
language completeness and human language review; test right-to-left if relevant.
No speculative language activation.

## Mandatory test matrix

| Gate | Minimum checks |
| --- | --- |
| Build | deterministic generators, schema, placeholder and escape validation |
| Language | uz/ru/tj snapshots, `tj/tg` conversion, device/account language sync |
| Mini App | app open, tabs, lesson=5, quiz/XP save, offline fallback, Pro/paywall, bot return; Playwright |
| Android | resource compilation and lint, login/onboarding, course cache after language switch, offline dictionary, direct/play separation |
| Desktop | macOS + Windows build/behavior parity, language switching, lessons, offline resources |
| Content | HSK 2.0/3.0 track lesson/card ID and answer parity, reverse-builder token order |
| Security | no client entitlement bypass, no public exam key, no new publicly exposed Pro package |
| Performance | baseline bundle sizes, static cache policy, zero per-string API calls and no startup regression |

## Initial implementation order

1. Improve inventory coverage and create frozen user-visible samples.
2. Create catalog schema/validators, with sample `common` + `errors` only.
3. Add deterministic generators that **do not yet replace existing runtime**.
4. Wire a small Mini App and Android slice behind parity tests.
5. Expand to Desktop, Bot, notifications and lesson overlays.
6. After every slice, compare against baseline and verify `main` remains untouched.

## Original audit hotspots (2026-10-17 baseline; current status is in RESUME_NEXT_CHAT.md)

- `scripts/gen_course_v3_from_seed.py` hardcodes `uz/ru/tj` when generating
  reverse-builder tokens and explanations.
- `app/main.py` provides a publicly readable static lesson-file route; verify
  content exposure and security before publishing new locale packs.
- `android/.../data/api/CourseDto.kt`, `.../core/i18n/LanguageCodes.kt`
  represent exactly three languages and require a **compatible** extension.
- `android/.../data/local/CourseCache.kt` keys map cache by course level; UI
  language synchronization needs a cached-map audit.
- `desktop/ui/js/i18n.js`, Mini App embedded dictionaries and
  `app/bot/utils/i18n.py` currently implement independent fallbacks.
- `app/bot/handlers/account_deletion.py` still has Uzbek hardcoded learner copy.
- `scripts/i18n_inventory.py` is a heuristic discovery mechanism, not proof of
  complete text coverage.

## Branch hand-off / first commands

Run from a clean checkout of **this branch**:

```sh
git checkout codex/p3-main-integration-20261020
python3 -m unittest tests.test_i18n_inventory tests.test_i18n_ui_regressions
python3 scripts/i18n_inventory.py --output /tmp/hsk-i18n-inventory.json
cd android && python3 tools/check_strings_translated.py
```

These commands are suggested validation steps, not assertions that they were
run against a checked-out repository in this preparation commit. Do not push
runtime changes to `main` just because the planning document exists.
