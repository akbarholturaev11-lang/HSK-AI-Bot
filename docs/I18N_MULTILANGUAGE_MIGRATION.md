# HSK AI multilingual localization: migration contract

Status: foundation / preparation. This document does **not** claim the runtime has migrated.
The goal is one logical source of truth for all learner-facing text (including lessons),
but NOT a giant JSON file and NOT a runtime-only remote translation service.

## 1. Preserve behavior while expanding languages

Existing live clients: Telegram Mini App (HTML/JS), Telegram Bot + FastAPI,
Android (Kotlin/Compose with direct and play flavours), desktop (Tauri macOS/Windows),
public website, push/notification templates and offline lesson/dictionary bundles.

Never change canonical Chinese text, pinyin, HSK 2.0 / HSK 3.0 lesson identities,
lesson order, answer keys, progression, grading, entitlement, subscriptions,
payment gates, or account language values as part of text migration.

Core learner-facing content is not just navigation labels: it includes
instructions, words/meanings, grammar, example sentences, dialogues,
quiz prompts, feedback, plans, mistakes, onboarding, limits, paywall copy,
notice templates, bot keyboard labels, and error/fallback states.

Dynamic LLM answers, user-generated content, server/provider error bodies and
third-party advertisements cannot be pre-translated: pass and enforce a normalized
target language and keep localized wrappers/errors. Do not invent translations.

## 2. Canonical taxonomy (target structure)

  localization/
    manifest.json                   # supported locale registry and aliases
    ui/{locale}/{namespace}.json     # key -> ICU-style message; one source
    content/{track}/{lesson_id}/
       source.json                  # stable IDs, zh, pinyin, question/answer identity
       {locale}.json               # only learner-readable translation fields
    notifications/{locale}.json
    validation/                    # key, placeholder, shape, language purity rules
    generated/                     # NEVER manually edit; build artifacts only

Namespaces include: common, auth, course, practice, tests, mistakes, voice,
assistant, profile, rating, payments, onboarding, notifications, bot,
public-site, desktop, android and accessibility.

A logical central store MAY be split into small reviewed files. Each string
must have a stable key or a stable lesson-content ID plus a field path. Every
message should retain meaning/context, rich-text safety class, and placeholders.
Avoid positional concatenation; use named placeholders and locale-aware numbers,
dates and plurals. Translation fallback must be explicit, logged, and measurable.

**Language codes:** public BCP-47 for Tajik is "tg" (Android resource folder
values-tg); the existing HSK AI server contract uses "tj". Use one explicit
adapter for this compatibility boundary; DO NOT blindly replace all "tj" in
API/DB code. Keep content Chinese separate from the user's interface language.

## 3. Stage 1 — complete inventory, no behavior change

- Run scripts/i18n_inventory.py and save its JSON report externally or as an
  audit artifact. It inventories known frontend / backend source surfaces and
  nested translatable JSON values with file paths.
- Classify entries as active user copy, administrator-only text, machine/log
  copy, Chinese learning source, translated content, and generated artifacts.
- Attach stable keys to UI strings and stable field paths to course content.
  Audit *the source producers* of generated JS, JSON and Android assets, not
  only copied runtime outputs.
- Find locale coverage, missing variants, wrong-language fallbacks, unsupported
  plurals, placeholder mismatches and accidental user-facing neutral fields.
- Do not mechanically translate whole course data or overwrite authored wording.
- Keep a freeze baseline for current uz/ru/tj and require product/content review
  before any new language becomes selectable.

Inventory is heuristic and MUST be followed by human review and end-to-end
checking; a regex hit is a candidate, not evidence of a live defect.

## 4. Stage 2 — adapters and incremental migration

- Introduce a canonical shared source catalog under localization/ui and
  localization/content, starting with the complete common/error/notification
  namespaces. Source assets remain the active fallback while migrating.
- Add a build validator for locale coverage and identical named placeholders.
  Preserve safe escaping and do not permit raw HTML from translations.
- Emit Android strings/plurals resources for each supported locale, respecting
  "direct" vs "play" flavour isolation and compiling packs offline.
- Emit a bundled client catalog for Mini App and desktop, with no mandatory
  network round-trip during startup. Prefer build-time extraction to extra
  per-string requests. Keep localization working when offline.
- Bot/backend use matching canonical locale dictionaries plus compatibility
  adapters; preserve user-account language preference and old API responses.
- Course translations have source IDs and locale overlays, versioned together
  with the base lesson. Quiz scoring must use source answer IDs rather than
  translated answer text; never reindex course progress.
- Migrate UI modules by surface/namespace, remove old inline literals only
  after runtime parity tests and snapshot checks. No mass search-and-replace.
- Android built APKs and desktop bundles need localized packs until updated;
  never remove legacy keys or lesson content while older clients rely on them.
- The admin panel may have a deliberately separate administrator locale
  policy, but must still be registered in the inventory.

Stage 2 is **not complete** merely because a new manifest exists. Completion
requires all live surfaces reading generated catalogs, non-regressing user
flows, and an empty reviewed list of in-scope unlocalized strings.

## 5. Acceptance gates before enabling additional languages

1. 100% translated keys and locale variants in every enabled UI namespace,
   reviewed by a human for the target language.
2. Every active lesson level/track has translated learner content, while zh,
   pinyin, learning objectives, answer IDs and progress behave identically.
3. Navigation, course/quiz, paywall, receipt review, notifications, error states,
   offline mode, accessibility labels, and login/logout pass tests in each locale.
4. Language switching across Bot, Mini App, Android and desktop is consistent,
   including "tj" <-> "tg" at the existing compatibility boundary.
5. Placeholder validation, safe rendering, text overflow/RTL where applicable,
   fallback metrics, and snapshots have automated coverage.
6. New languages appear in UI only after completeness gates pass. Draft/
   machine-generated strings must never be marketed as reviewed.
7. Validate Play vs direct payment-policy copy; do not accidentally expose
   external checkout copy in the Play build.

## 6. Verified initial defects and controlled patch

- Mini App foundation reload header used hardcoded Uzbek.
- Mini App retry was checking "tg" while runtime LANG is "tj".
- Memorize, recognition and pronunciation no-data messages used Uzbek literals.
- Keep bugfixes local to the existing language dictionary mechanism pending
  full catalog migration; do not add network dependencies to the lesson flow.
- Regression checks: tests/test_i18n_ui_regressions.py.

## 7. Known limitations of current preparatory commit

This commit does not complete extraction/migration of thousands of text
occurrences or translation of HSK data to new languages. The inventory tool
provides reproducible discovery, but generated/embedded content and runtime
responses still require manual verification. No new language is activated.
