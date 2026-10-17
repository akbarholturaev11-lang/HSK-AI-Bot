# P0 local-first localization — audited snapshot (2026-10-17)

**Status: P0 IN PROGRESS. This is automated discovery, NOT a declaration of
full multilingual coverage or UI/lesson correctness.** No client runtime,
account/paid access rules, grading or deployment was changed.

## Reproducible evidence

- Isolated branch: `codex/i18n-local-first-foundation-20261017`
- Frozen source baseline from main: `160a51d69f3324e3162375213ec61b5587b19533`
- Audit tool: `scripts/i18n_source_audit.py`
- Baseline tool: `scripts/i18n_baseline_guard.py`
- Existing inventory: `scripts/i18n_inventory.py`
- CI evidence: [GitHub Actions run 38997894997](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/38997894997)
  with downloadable `hsk-i18n-p0-audit` artifact.
- Baseline reference: `localization/baselines/source_git_blobs.json`

The audit is deterministic and read-only: no network calls to translation
services, no UI strings fetched dynamically and no lesson asset mutations.

## Quantitative results (automated, reviewed as scanner output)

| Audit measurement | Count |
| --- | ---: |
| Source paths scanned by new P0 scanner | **2,681** |
| Embedded JSON locale maps found | **70,813** |
| Locale maps missing at least one of uz/ru/tj, in detected schema | **0** |
| Named-placeholder mismatches in detected JSON locale maps | **0** |
| Candidate literals to classify; NOT confirmed defects | **7,951** |
| Python message candidates | **469** |
| JS catalog candidates | **6,775** |
| HTML attribute candidates | **104** |
| Legacy scanner candidates included in P0 output | **603** |
| Parse/read errors | **0** |
| Android resource parity pairs checked | **24** |
| Missing or orphan Android resource names among checked pairs | **0** |
| Present source registry surfaces | **10** |
| Registry anchor paths missing | **0** |

**Limits:** the scanner sees 3-language objects that match its heuristics;
it cannot prove a page renders the right language, that every visible string is
classified, that every phrase is translated accurately, or that native client
offline and Pro gating behavior is correct. JS value detection is deliberately
broad and produces duplicates and non-visible candidates. Python handler
candidates include admin/operator text, so they must be classified before
prioritizing learner-visible migration. The 24 Android comparisons check
resource-name parity, not native plurals, style, grammar, or layout fit.

## Frozen source files (checked, 0 byte-level blockers)

| Stable baseline asset class | Files |
| --- | ---: |
| HSK 2.0 + HSK 3.0 lesson JSON | **746** |
| Legacy content JSON | **8** |
| UI catalog/source files | **54** |
| Generator and audit sources | **3** |
| **Total** | **811** |

Lesson file counts by track:
`hsk1=63`, `hsk2=72`, `hsk3=109`, `hsk4=181`,
`nhsk1=103`, `nhsk2=73`, `nhsk3=145`.

This proves recorded files match their Git blobs. It does not imply their
Chinese text, lesson semantics, answer keys or natural-language translations
have been manually audited.

## Highest-priority review queue

1. **Mini App source dictionaries.**
   `app/static/course-v3.html` alone produced 2,217 broad candidates;
   `app/static/subscription.html` produced 502; examine all active
   screen-local copy, hidden fallbacks, HTML attributes, `?lang` handling
   and old-client compatibility before migrating.
2. **Desktop dictionary.**
   `desktop/ui/js/i18n.js` produced 2,396 broad candidates from its
   three existing language dictionaries. Identify stable shared keys,
   placeholders and render parity. This is NOT 2,396 missing translations.
3. **Python bot/backend handlers.**
   Of 469 message candidates, many are in admin modules: e.g.
   `app/bot/handlers/admin.py`, `app/bot/keyboards/admin_discount.py`
   and `app/bot/handlers/admin_partner.py`. Distinguish learner messages
   from admin operations; fix known Uzbek-only account deletion messages
   only after capturing exact callback/registration behavior.
4. **Course generators and exercise tokens.**
   `scripts/gen_course_v3_from_seed.py` still loops over three hardcoded
   locales to build reverse-builder tiles/distractors. Adding a fourth
   translation key without extending this generation is unsafe.
5. **Static asset entitlement boundary.**
   Existing `app/main.py` route serves
   `/course_v3_data/{level}/lesson_*.json` anonymously. Audit exposure
   and any sensitive correct answers before publishing locale bundles.
   Never put private exams or new locked content into general public assets.
6. **Runtime language and cache.**
   Android `CourseCache` map is keyed by level, not UI language;
   inspect language-switch behavior. `tj` is still the backend language
   value while Android/HTML should use BCP-47 `tg`. Browser HTTP cache
   by itself does not prove Mini App offline capability.

## P0 follow-on: learner-text samples and prioritized review queue

The isolated branch now includes `scripts/i18n_lesson_samples.py`,
`tests/test_i18n_lesson_samples.py`,
`localization/baselines/lesson_locale_samples.json`, and
`scripts/i18n_review_queue.py` with its tests.
This is **still a source-level audit**, not proof of running UI translations.

- For **all seven course tracks** (hsk1–4 and nhsk1–3), the first lesson's
  Chinese title, first word/pinyin, card type, ID and section counts were
  frozen alongside exact `uz/ru/tj` subtitles and first-word meanings.
  Result: **7 lessons x 3 languages = 21 source sample pairs; 0 differences**.
  The full 746-file byte baseline remains the broader historical guard.
- CI [run 38998775540](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/38998775540)
  archived the source samples and review queue in the
  `hsk-i18n-p0-audit` artifact, which is retained temporarily by GitHub.
  The localization-specific test step passed.
- The read-only queue presents the **75 highest-priority of 86 source files**
  containing scanner candidates; its source classification is tentative.
  All 2,681 sources remain in the complete raw audit.
- Actual preliminary file-level queue totals from CI:

| Provisional area | Source files scanned | Candidates to classify |
| --- | ---: | ---: |
| Learner frontend (Mini App, Android, Desktop) | 416 | **7,037** |
| Bot / learner messaging | 60 | **197** |
| Admin or operator | 28 | **691** |
| Lesson source content | 800 | **18** |
| Generated/packaged dictionary and phrase data | 1,063 | **0** |
| Lesson/source generators | 114 | **0** |
| Backend unknown | 200 | **8** |
| **Total** | **2,681** | **7,951** |

Zero *heuristic literal hits* in packaged data and generators does **not**
mean those resources lack language-specific text or are ready for new languages.
Their nested localized maps, hardcoded locale loops and generated outputs need
separate review. Candidates include repeated strings, identifiers and
non-learner text, so do not label them all as defects.

Priority file samples from the ranked artifact:
`desktop/ui/js/i18n.js` (2,396 candidates),
`app/static/course-v3.html` (2,217),
`app/static/subscription.html` (502), followed by Mini App test,
onboarding, ads, voice and dictionary screens.

**Still pending:** reviewed candidate disposition, browser/native screenshots,
full offline/WebView tests, API rendered lesson snapshots, public lesson
entitlement/security audit and new-language coverage gates.

## Next P0 acceptance gates (not completed)

- Source-by-source classification of the review candidates: active
  learner UI, study material, administrative-only, generated, logs/IDs,
  dynamic LLM/user copy and genuinely non-translatable.
- Freeze *rendered* three-language UI samples and a lesson/quiz output
  baseline, not only source Git blob identifiers.
- Check Mini App deep links, bfcache/cache headers and actual WebView
  offline behavior; Android/desktop runtime screenshots and native builds.
- Review backend/Pro/public lesson JSON exposure and protected exam keys.
- Decide normalized fallback and locale conversion policy with
  backward-compatible tests; document untranslated plurals/RTL concerns.
- Only then begin P1 common/error catalog and deterministic target
  generators. Keep feature PR draft, and do not enable new language choices.

## CI learning

The first run of the new frozen-baseline guard had **four test errors**
because the test fixture declared seven track counts (six zeros) while the
Python `Counter` omitted absent keys. Missing source files were also
mistaken for track-count mismatches rather than reported review blockers.
The guard was corrected in
`364db231ba42e2c9c354ec416f257ffb62373e3e`.
The subsequent localization CI step passed and its baseline artifact
reported 811 checked files and zero blockers. Keep this regression guard
rather than hiding or rewriting the failing test.

## Additional P0 evidence — source scanner corrections and compatibility guard (2026-10-17)

The first audit's **2,681 source paths / 7,951 broad literal candidates**
are a historical snapshot, not refreshed totals after scanner coverage expanded.
The refreshed report from [CI run 38999948668](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/38999948668)
is archived under `hsk-i18n-p0-audit`. The entire `Backend targeted tests`
job **passed** (not just its localization step). Measured P0 source results:

| Current expanded P0 scan | Verified count |
| --- | ---: |
| Scanned source files | **2,684** |
| Detected localized JSON maps | **71,125** |
| Broad review candidates (not confirmed defects) | **7,954** |
| Candidate-bearing source files | **87** |
| Highest-priority files included in review queue | **75** |
| Parse/read errors | **0** |
| Frozen baseline sources / byte-review blockers | **811 / 0** |
| Seven-track, three-language lesson source sample differences | **0** |
| Lesson JSON files inspected by structural route guard | **746** |

These numbers are automated evidence, **not** UI translation-completeness,
runtime authorization or translation-quality certifications.

### Source-level findings and corrections

- Existing `python_message_candidates` used positional index 1 for all
  `send_*` calls. For `send_photo`, `send_document`, `send_video` and
  `send_animation`, index 1 is usually a *media object/path*, not a caption.
  Index 2 carries an optional positional caption; `answer_photo` and
  `answer_video` use index 1. Scanner argument selection now distinguishes
  these cases, with regression tests; this reduces misleading media-path hits
  and captures previously omitted user-facing captions. Counts may shift.
- `scripts/ready_phrases/phrases.json` and
  `scripts/build_ready_phrases.py` were absent from the expanded P0 scan
  globs. Both now have coverage and registry references. Nested Android assets
  and Desktop JSON sources also have expanded matching patterns.
- The new `scripts/i18n_p0_contract_audit.py` validates manifest/registry
  compatibility, forbids accidental P0 runtime-language activation, and reports
  structural answer-like fields from the seven HSK 2.0/3.0 course tracks,
  without serializing any lesson text or correct answers.
- The `/course_v3_data/{level}/{filename}` FastAPI handler in
  `app/main.py` returns static lesson JSON and has no direct signature-level
  dependency. This is **a security review finding, not proof** that a learner
  can bypass subscriptions; check global middleware, deployed routes,
  the contents of public lesson JSON and separate exam APIs.
- `AppLanguage.DEFAULT` in Android is `RUSSIAN`, while the planning
  manifest's default is `uz`. This is **an unresolved precedence mismatch**,
  not proof of wrong language in the active app. Inspect account-selected,
  device-selected and unknown-locale fallback behavior before migration.

### Validation scope and remaining blockers

Localization CI now runs `tests.test_i18n_p0_contract_audit` and the
read-only 746-source lesson route/structure report in addition to existing
frozen-byte, placeholder and 7-track sample guards. This cannot replace
review of literal candidates, actual rendered copy, Android resources after
compilation, Telegram WebView caching, direct/Play payment parity, or
Windows/macOS desktop behavior. No Pro/free/trial, auth, grading, progress,
APK, Mini App runtime, or lesson source data was altered.

**P0 remains IN PROGRESS.** No P1 generated catalog or target-runtime
migration is implemented. Refer to `localization/PLAN_SCHEMA_ORDER.md`
for the exact commit sequence, verified tests and next gates.

## P0 fourth source review — Android XML and lesson assessment shape (2026-10-17)

The preparation branch has a new read-only Android XML audit:
`scripts/i18n_android_resource_audit.py`, regression
`tests/test_i18n_android_resource_audit.py`, and backend CI artifact
`hsk-i18n-android-xml-audit.json`. Unlike the existing name-only Android
scanner, it parses XML, inventories `string` / `plurals` /
`string-array`, and compares existing ru/tg resources from each
`main/direct/play` source set for placeholder types/positions and
plural/array shape without emitting translation text.

**Measured result:** [CI 39000462115](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39000462115)
concluded **SUCCESS**, with **24 compared resource pairs and 0 XML
structural/placeholder review findings**. This does not validate translation
quality, Android lint/rendering or Android direct/Play billing behavior.

The existing `scripts/i18n_p0_contract_audit.py` also checks current
`correct_index` bounds against list or locale-keyed option arrays in all
seven lesson tracks. Issues are structural only: no answer values, words,
pinyin, questions, or user data appear in the emitted report. Regression
tests cover valid and out-of-range options without touching grading.
[CI 39000552111](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39000552111)
passed the localization-specific unit/audit step and the overall
`Backend targeted tests` job concluded **SUCCESS**. This is not a
native-device test, production authorization test or full P0 approval.

**Confirmed source-only hardcoded copy finding:** user-facing messages
in `app/bot/handlers/account_deletion.py` are Uzbek constants, including
verification and confirmation callbacks. No runtime locale lookup is used
by these handlers. This is a specific learner-message gap, not an
automatic claim that every scanner candidate is a defect. P0 leaves
the deletion/ownership flow unchanged pending localized bot message
fixtures and correct user-language lookup tests.

**Confirmed static exposure review target:** the GitHub Actions P0
artifact reported **6,449 answer-like field occurrences** in 746 source
lesson files: 6,445 at `$.sections[].cards[].correct_index` and four
in other card groups; **0 out-of-range option-index findings**.
Course lesson JSON contains `correct_index` keys, and `app/main.py`
defines a direct static lesson route with no handler-level dependency.
Actual unauthenticated availability, globally applied middleware,
Pro exposure and private exam grading need independent checks. Do not
publish newly generated paid bundles or exam keys while unresolved.

**Remaining:** rendered 3-language UI/quiz and notification baselines,
WebView/offline/device testing, manual candidate triage, full course
entitlement review and verified language fallback precedence.
P0 remains IN PROGRESS; no changes to live client strings, lesson data,
access control, payments, or account state have been made.

## P0 fifth audit — Bot/Desktop source catalog parity and divergent fallbacks (2026-10-17)

A deterministic read-only script `scripts/i18n_catalog_contract_audit.py`
extracts the current Python Bot literal translation tables using `ast`,
without importing or executing the bot, and inventories the present Desktop
JS messages object. It checks locale key sets, named placeholders, HTML tag
counts, Bot merge order and duplicate definitions. It produces no translation
values, learner content or credentials.

**Measured [GitHub Actions 39005975851](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39005975851)
artifact:** Desktop has exactly **797 keys per each of uz/ru/tj**; effective
Bot `TEXTS` contains **253**, and Bot `COURSE_I18N` contains **92** keys per
locale. Across the nine Bot source tables, final Bot catalogs and Desktop,
**0 missing localized keys, 0 named-placeholder drifts and 0 HTML tag-count
drifts** were reported. The existing Bot `ONBOARDING_TIP_I18N` overrides
the `TEXTS` key `referral_trial_access_unlocked` in all three languages
(3 recorded overrides). These are source parity checks, not proof that
all UI strings are translated or rendered correctly.

**Confirmed source-level fallback inconsistency** (not an established
user-visible bug): Mini App course uses **ru** as its initial unknown-language
fallback, while Mini App subscription and Desktop use **uz**. Bot's
`t(..., lang="ru")` and Android's `AppLanguage.DEFAULT = RUSSIAN`
use **ru**. The preparation manifest proposes **uz**. Course can
subsequently use the authenticated account's supported language when it
arrives. This observation requires an explicit precedence contract and
runtime tests before localization adapters are switched.

The fallback evidence was added to the same read-only P0 audit
(`7e7bf7220e504a9b0df58418c9e2d95dcd79afe7`) and real-repository
regressions (`9a10e479356af88243a0b3e52b696928c0ee53f9`),
[CI run 39006142928](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39006142928).
The localization-specific tests and the complete `Backend targeted tests`
job both concluded **SUCCESS**. No native-device or live-production check is implied.

This slice did **not** change UI copy, callbacks, Android source resources,
lesson JSON, user locale preference, auth, payment, access policy or runtime
delivery. The planned shared source-of-truth catalogs and all runtime
migrations remain **NOT STARTED**. P0 review and device QA continue.

**Source-level static lesson route security addendum.** In `app/main.py`,
the GET route `/course_v3_data/{level}/{filename}` calls
`static_json_response` for any matching lesson path and does not have
handler-level user/entitlement dependencies. The application's
`BlockedUserApiMiddleware` (`app/services/blocked_user_guard.py`)
explicitly guards only paths beginning with `/api/`, and forwards the
other requests untouched. Therefore **the blocked-user middleware is not
a gate on this lesson JSON route**. The source JSON also includes
`correct_index` values. This is stronger source evidence of a potential
content/answer exposure, but not a live-production HTTP/edge-control test.
New public language packs must not introduce additional locked lessons or
private exam answers until authorized delivery is designed and tested.
Existing access/payment behavior remains unchanged in this audit.

## P0 sixth audit — Mini App embedded catalog inventory (2026-10-17)

Read-only `scripts/i18n_miniapp_catalog_audit.py` scans selected verified
literal `uz/ru/tj` maps, including nested object and array keys, without
executing JavaScript or capturing actual strings. A CI artifact records key
paths and signatures only. The
[expanded run 39007054885](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39007054885)
completed the Mini App localization test/audit step successfully.

| Selected Mini App page and catalog | Keys in each language |
| --- | ---: |
| Course `I18N` / `TRACK_UI` / `HSK30_BOOK_COPY` | 86 / 32 / 5 |
| Subscription `I18N` | 190 |
| Test center `L` / `EM` / `HSK30_SOON` / `PT` | 19 / 20 / 3 / 6 |
| Mistakes `L` | 53 |
| Pronunciation `L` | 22 |
| Recognition `L` | 10 |
| Onboarding `L` | 31 |
| Voice roleplay `L` | 47 |
| Dictionary `UI` / `practiceLabels` / `memoLabels` / `messages` | 23 / 7 / 7 / 2 |
| Ready phrases `UI` | 15 |
| **Total across 18 selected catalogs** | **578** |

Each has three locales. **No missing key paths, named-placeholder drift,
HTML-tag-count drift, or value-type drift** was detected. The dictionary
`UI` contains legacy `countAll`, `countResults`, and `strokes`
localized JavaScript functions (3 in each language). These 9 dynamic
values are deliberate formatter functions, not plain strings. A follow-up
scanner revision classifies their parameter signatures separately rather
than silently converting or dropping them. Its validation reference is
[run 39007233003](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39007233003).

**False-positive test corrected:** run 39007010367 failed an incorrect
test threshold requiring over ten keys per catalog. Small real catalogs
with 2–7 keys make that assertion invalid. The subsequent CI step
passed after relaxing the test in commit `1db94831`. This was a
test-fixture issue; the Mini App runtime was not altered.

**Not covered:** most inline language ternaries, dynamic/runtime-generated
copy, all other page-local maps, rendered screenshots, language switching
and cache invalidation, semantic translation quality, paid/locked course
payloads, and authorization/assessment security. This remains **P0
IN PROGRESS**. No production UI/lesson/auth/payment code changed.

### Mini App residual source-hotspot measurements

[GitHub CI 39007408199](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39007408199)
passed the localization-specific tests **and** the full Backend targeted
tests job and wrote source-location-only hotspot measurements. The 11 scanned pages contain **11** inline
`t({uz:...})`/`tr({uz:...})` translation call candidates,
**126** explicit `LANG` branch candidates, **54** declared JS
locale-object candidates, and **59** HTML attribute candidates.
These totals **include** previously scanned dictionaries and may contain
false positives. They are not defect counts or verified unlocalized
strings. The most concentrated sites are `course-v3.html` (125
language branches; 38 locale-object declarations) and
`course_v3_memorize.html` (9 inline locale-map calls).
Only counts and file/line locations are archived; no runtime text values.

The selected `hsk-lugat.html` dictionary source contains 3
legacy JavaScript localized formatting functions in each locale:
`countAll(n, level)`, `countResults(n)`, `strokes(n)`.
The updated static audit records 9 such entries and **0 parameter
signature differences** ([CI 39007233003](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39007233003)).
They cannot be naively converted to simple language strings in P1.

Further requirements before P0 closure: classify hotspot line locations,
manually review translations and fallback precedence, inspect rendered
screen snapshots for 3 locales, test WebView static caching/offline
and native Desktop/Android, and resolve any static Pro/exam-content
exposure before publishing versioned lesson locale bundles.

## P0 seventh audit — CI trigger coverage and future public bundle confidentiality (2026-10-17)

**P0 CI trigger gap confirmed:** the previous `Backend targeted tests`
workflow did not watch isolated PR modifications to `localization/**`,
`scripts/i18n_*.py`, `desktop/ui/**` or `android/app/src/**`. This is
a build-safety gap: source translation/catalog edits could bypass the
localization checks if no tracked backend/test source also changed.

`.github/workflows/i18n-p0.yml` now runs isolated stdlib-only source
unit tests, baseline guards and reporting on PR modifications to relevant
catalog, client and backend source trees. There is no Gemini/OpenAI
translation call, generated language activation, or new application HTTP
endpoint. Source-only CI does not validate actual Android/Desktop builds.

`scripts/i18n_public_bundle_guard.py` and its unit tests establish
an explicitly **pre-publication** safety guard for JSON in the *future*
Mini App public and generated-web locale output directories. The
script rejects grading keys like `correct_index`/`correctIndex`,
`answer_key`/`answerKey`, `is_correct`, and unreadable JSON, while
allowing ordinary visible UI labels `answer`/`correct`/`solution`.
Only file paths and JSON key paths are reported. Neither the unit
tests nor the guard output contain user data or actual correct answers.

**Verified:** [Actions run 39008015762](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39008015762)
completed SUCCESS with all source unit tests and read-only report steps.
The archived `public-pack-security.json` was opened directly and reports:

| Field | Verified |
| --- | --- |
| `status` | `NO_PACKS_YET` |
| `checked_json_packs` | `0` |
| `findings` | `[]` |

**Scope limitation is critical:** no new public language JSON was
present to inspect. Legacy publicly served HSK 2.0/3.0 lesson JSON
(and answer indices) remains outside this guard and its exposure
still requires a separate authorization/deployment review. Generated
JS, unregistered output folders, client cache semantics and actual
billing/entitlement boundaries are not certified. A passing optional
PR workflow only blocks merges automatically if repository branch
rules require that check; branch-protection configuration is not
confirmed by this audit.

**Next:** classify Mini App inline language branches/attributes with
stable source references, validate translation/HTML safety manually,
review real API and edge-route protection, and run client-level
locale/fallback/offline regression tests before closing P0.
No runtime modifications were made.

## P0 eighth audit — manually classified Mini App source hotspots (2026-10-17)

The existing residual hotspot scanner is intentionally heuristic.
We inspected the actual `app/static/course-v3.html` source and recorded
**21 distinct reviewed source line anchors** in
`localization/review/miniapp_course_hotspot_triage.json`. This is a
*partial* review, not 21 of 125 interchangeable individual patterns:
a single condensed JavaScript source line can contain multiple
`LANG` checks. The full source scan previously measured 125
`LANG` occurrences, not 125 distinct text strings.

The reviewed sample includes visible/accessibility UI copy, lesson
prompts, errors, rating/profile/navigation strings, lesson glosses,
access/limit status text, plus three **non-text transformations**:
`tj` to HTML `tg` locale adaptation, Russian plural grammar,
and TTS preferred-voice language lookup. These must preserve
their behavior during any build-time translation migration.
None was automatically translated, refactored or moved.

The source triage test
`tests/test_i18n_miniapp_hotspot_triage.py` checks the known file/line
anchors, categories, explicit review status, and data-only vs
behavioral distinction. It was verified in
[fast P0 CI 39008283996](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39008283996)
(**SUCCESS**). If source lines change, the test fails closed and
requires re-review rather than silently retaining stale classifications.

**CI efficiency:** source-only P0 checks and full backend tests now
have PR-scoped concurrency groups with `cancel-in-progress: true`
(commit `0b002834` for backend, `e3244675` for fast P0), to
avoid paying for several obsolete full runs on sequential commits.
An intentionally cancelled old run is *not* a regression test failure.

**Important remaining work:** review the other source hotspots,
check correct translation and escaping of those visual strings,
actual 3-language on-device screens, WebView cache/fallback flows,
and real static course entitlement/exam exposure. Neither P0 nor any
generated runtime translation target is complete.

## P0 ninth audit — explicit Mini App course predicates and memorization inline calls (2026-10-17)

**Verified, narrowly scoped source classification:** all **125** currently
detected `LANG ==/===` comparisons against `uz/ru/tj` in
`app/static/course-v3.html` occur on **60 distinct physical lines**.
`localization/review/miniapp_course_hotspot_triage.json` now classifies
all those 60 lines. The source-only regression compares the exact
60 line set and per-line counts and fails when new matching lines
appear without manual review. This is *not* a semantic review of each
of 125 expressions in every runtime state, nor proof of comprehensive
translation coverage. Notable non-copy branches preserve
`tj -> tg` HTML language mapping, Russian plurals, and preferred
TTS language; these are not candidates for blind text extraction.

The separate `app/static/course_v3_memorize.html` source contains
exactly **nine** `t({uz:...})` / `tr({uz:...})` message calls,
all inventoried in
`localization/review/miniapp_memorize_inline_triage.json`.
Eight are static copy candidates; one is a dynamic question that
concatenates the Chinese `H` Hanzi source into three language-specific
messages. Migration must preserve `H` via a named `{hanzi}`
placeholder and leave quiz-option and answer identity alone.
Its regression verifies nine ordinal/line anchors and the Hanzi
input in all three existing language choices.

[Fast GitHub Actions 39008932889](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39008932889)
concluded **SUCCESS** with both regression modules and the complete
set of existing read-only P0 source checks.

**Scope not validated:** all remaining Mini App source idioms (language
object selection, language-sensitive DOM updates, HTML attributes,
dynamic translated lesson content), user-facing correctness, real
WebView offline/cache behavior, Android/Desktop builds, production
Pro/Free lesson HTTP authorization and exam secrecy. P0 remains open,
and this audit made no runtime behavior changes.

## P0 tenth audit — lesson/public JSON and exam/404 route source boundary (2026-10-17)

**Reproducible read-only source check:** `scripts/i18n_route_boundary_audit.py`
and `tests/test_i18n_route_boundary_audit.py` analyze three existing
`GET /course_v3_data/...` route decorators and the blocked-user
middleware prefix with Python AST, **without importing the app**.
[Fast P0 CI 39010834743](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39010834743)
completed **SUCCESS**; the archived `static-route-security.json`
was downloaded and inspected:

| Source boundary | Verified result |
| --- | --- |
| Legacy lesson GET `/{level}/{filename}` | Serves JSON file |
| Handler-level dependency | Absent |
| Track and lesson filename regex constraints | Present |
| Blocked-user middleware | Guards `/api/` only |
| Exam file GET `/exams/{filename}` | Explicit 404, no file serving |
| Top-level map GET `/{filename}` | Public JSON file serving |
| Audit status | `SOURCE_REVIEW_REQUIRED` |

Two **source-level findings**, not exploit confirmations: a direct
lesson file path without handler entitlement and a public curriculum
map-serving path that requires payload classification before new
locale packs are published.

**Compatibility observation:** the current Mini App `lessonDataUrl`
fetches public lesson JSON directly; `loadLessonData` does not send
the Telegram initData header on this fetch, and uses a special
revision/cache policy for N1. Exams instead use
`/api/v3/exams/start` and `/complete` with initData.
Blocking the legacy URL in isolation risks client regressions; it is
not a safe localization-only fix.

**Planned, not implemented:** `docs/I18N_P0_LESSON_DELIVERY_SECURITY_DESIGN.md`
defines staged real-world access QA (anonymous/Free/Trial/Pro/blocked),
replacement authorized lesson delivery, versioned offline-aware caches
and phased clients, then potential legacy route closure **after** testing.
No permission or payment policy was changed and no actual production
HTTP/proxy or native/WebView E2E tests were run. P0 remains IN PROGRESS.

### P0 tenth follow-up — curriculum map content structure

All seven public root `course_v3_data/{level}.json` files were parsed
with a read-only, key-path-only scanner. The [CI source artifact for
39011261505](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39011261505)
was downloaded and verified:

| Track map | Navigation lesson entries |
| --- | ---: |
| `hsk1` | 63 |
| `hsk2` | 72 |
| `hsk3` | 109 |
| `hsk4` | 181 |
| `nhsk1` | 103 |
| `nhsk2` | 73 |
| `nhsk3` | 145 |
| **Total** | **746** |

Result: `maps_checked=7`, `lesson_navigation_entries=746`,
`private_assessment_key_occurrences=0`. The validator tests a
synthetic `correct_index`/`answer_key` insertion and treats new
private grading keys as a **release-stopping** regression.

**Important distinction:** these seven public *navigation maps* have
zero observed private grading keys, but the separate underlying
`/course_v3_data/{level}/lesson_*.json` files contain answer indexes
and are served by a handler without its own entitlement dependency.
Zero map-key findings are not proof of paid lesson privacy.
The maps contain translatable labels/content metadata and a
`progress` template; they are not guaranteed to be free of all
commercially restricted learner text. No live user-specific
response/proxy or native client was tested.

**Naming-variant hardening:** Source guard normalization also catches
`correctIndex`, `answer-key` and similar camelCase/kebab-case fields;
the synthetic fixture tests verify four forbidden grading paths
without exposing actual answer values. Verified in
[fast P0 CI 39011475458](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39011475458),
conclusion **SUCCESS**. This is protection for future map edits, not a
claim that runtime Pro content access has been fixed.

## P0 eleventh audit — source-level client transport compatibility (2026-10-17)

A dedicated read-only `scripts/i18n_client_lesson_compat_audit.py`
inspects the current Mini App, native Android (Retrofit and Room), Tauri
Desktop (JS bridge/Rust), and Android/Desktop server routes/services.
It deliberately compares **different existing delivery designs**
instead of assuming Android and Desktop must be converted to the raw
Mini App lesson JSON route.

| Client | Existing request | Source-level server access check |
| --- | --- | --- |
| Mini App | Public `GET /course_v3_data/<level>/lesson_*.json` with no initData header | Static handler has no per-lesson entitlement dependency |
| Android main-source transport | Bearer `GET /api/v3/android/course/lesson/{lessonOrder}` | Android service inherits desktop lesson logic; verifies account, sequence and `LessonAccessService.status(..., consume=True)` |
| Tauri Desktop | `bridge.lessonData` to Rust `authenticated_get_json`, Bearer `/api/v3/desktop/course/lesson/{lessonOrder}` | Server uses verified bearer, sequence gate and the same entitlement service |

Native lesson API responses are `Cache-Control: no-store`. Android
stores a validated server-authorized lesson envelope in Room and
falls back to it only on network `Offline`/`Timeout` errors. A
server-denied access state must not become a cache hit. A DAO
method exists to clear cached lessons on logout. The source under
`android/app/src/main` supplies common lesson transport to Play and
direct builds, but the behavior of already released clients has not
been tested here.

Regression tests specifically detect future removal of native
`Authorization` or bearer calls, unsafe remapping of Desktop to the
public path, and broadening Android cached fallback to non-network
errors. The first negative-fixture version of this audit failed
because a test string no longer matched the real Kotlin `!is`
condition. Both audit matcher and test fixture were corrected; the
[fast P0 run 39012530053](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39012530053)
concluded **SUCCESS** with the updated source contract.

**Resulting priority:** migrate only the Mini App's known anonymous
static lesson fetch in a staged, separately approved implementation
after entitlement QA; avoid needless native API replacement. The
corresponding account-state table and cache/rollback acceptance
criteria are in
`docs/I18N_P0_LESSON_DELIVERY_SECURITY_DESIGN.md`.

All findings concern **source code**. No actual Free/Pro test user,
production HTTP probe, reverse proxy, old APK/Desktop binary, offline
device, currency/checkout flow or deployed authorization boundary
was evaluated. P0 is not closed.

### Android logout and account-switch cache isolation follow-up

The cross-client source audit now checks the full local cache deletion
call chain: `MainActivity`'s explicit logout callback **and**
`AuthState.Unauthenticated` branch call
`HskAiApplication.clearLocalData()`, which invokes
`CourseRepository.clearCache()`, which clears both the course map
DAO and the lesson DAO. The current `AuthRepository` session-clear
callback itself only clears widget/notifications; the UI
`Unauthenticated` branch and explicit logout callback are therefore
part of the cache-isolation contract.

A regression fixture attempts to remove the actual UI logout wipe,
and a second one removes the app-to-repository cache clear.
The first fixture initially missed its target and made the
*test* fail; this was corrected and
[fast P0 CI 39012928501](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39012928501)
completed **SUCCESS**. Neither the client code nor account deletion,
payment, or course progression was modified.

This is **source-based** evidence, not demonstrated data isolation
between real accounts on installed phones. QA still needs account A
authorized lesson -> offline -> explicit logout or revoked session ->
account B sign in, plus race conditions with concurrent writes.

## P0 twelfth audit — six distinct Mini App lesson-data access intents (2026-10-17)

A further source call-graph review of `app/static/course-v3.html`
found **six direct calls** to `loadLessonData()` besides its
function declaration. Each is registered, by exact source
line/ordinal and behavior, in
`localization/review/miniapp_lesson_fetch_calls.json`.

| Direct caller | Source line | Critical constraint |
| --- | ---: | --- |
| Paywall sales prime | 1978 | Background marketing preview is not a learner-opened lesson |
| Preview audio warmer | 2128 | Runs before Continue, must not spend a daily opening |
| Nearby lesson prefetch | 2913 | Fetches current/next during idle; may fetch not-yet-entitled content |
| Skip-ahead test | 3533 | Uses static lesson cards as questions; requires separate authorization and answer-key safety |
| Starter 0 foundation | 3665 | Must preserve prerequisite access outside paid lesson consumption |
| User-entered lesson | 3995 | **Only** direct caller sequenced after `reserveLessonStart(l)` |

This makes a direct global replacement of `loadLessonData()`
with native Android/Desktop `consume=True` lesson APIs unsafe:
it could charge a Free learner's daily allowance for idle prefetch,
audio warming, paywall rendering or a foundation step. An authenticated,
typed content strategy is needed, not only adding headers to the
existing fetch. The separate
[security design](../docs/I18N_P0_LESSON_DELIVERY_SECURITY_DESIGN.md)
describes the proposed, **unimplemented** access separation.

**WebView cache identity observation:** `LESSON_DATA_CACHE`/
`LESSON_DATA_PROMISES` and `lessonDataKey` use level/order only;
the `lessonResumeKey` localStorage key also lacks `localUserScope`,
whereas the mastery cache key does include it. This may require
identity-aware cache keys or invalidation when introducing new
protected lesson bodies. The source alone does **not** demonstrate
an actual leak across Telegram accounts.

`scripts/i18n_miniapp_lesson_fetch_audit.py` plus
`tests/test_i18n_miniapp_lesson_fetch_audit.py` fail when six
documented read sites are changed without review, when a new
caller appears, or when the interactive reservation order is
lost. [P0 CI 39013692471](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39013692471)
completed **SUCCESS** with this guard and its 6 unit tests.
No new runtime route or quota behavior was implemented.
P0 is still open pending controlled staging and device-level QA.

## P0 thirteenth audit — staging-only HTTP probe (not executed remotely)

A dedicated Python-stdlib staging QA tool was added:
`scripts/i18n_staging_anon_route_probe.py`. Its normal invocation
is a **dry run**. It creates 15 proposed anonymous routes (7 course
root maps, 7 first lesson paths and 1 private-exam path), refusing
plain HTTP, a production domain, a mismatched confirmation host,
embedded credentials, non-staging domains and URL redirects.
The optional explicitly enabled staging mode records **HTTP status
only** and never reads returned content. Therefore this tool does not
expose lesson bodies, correct answers, session tokens or receipts.

Five unit tests in `tests/test_i18n_staging_anon_route_probe.py`
verify default zero-network operation, explicit QA hostname checks,
no response body reads/authorization headers, exam-404 failure
classification and network errors not counting as protection.
[Fast P0 CI 39014283200](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39014283200)
completed SUCCESS. Its downloaded artifact was inspected and contains
`status=NOT_EXECUTED_STAGING_TARGET_REQUIRED`, `planned_requests=15`,
`performed_requests=0`, `findings=[]`.

**This is evidence of test readiness, NOT proof of live anonymous
access restrictions.** No QA server was provided and the tool was
not instructed to contact any host. Free/Trial/Pro/blocked sessions
cannot be assessed by the anonymous status-only probe.
`docs/I18N_P0_STAGING_ACCESS_RUNBOOK.md` describes those manual
account-state scenarios, zero-consume prefetch behavior and the
Mini App account-switch cache verification required for P0 closure.
All live permissions and client E2E remain unverified.

### Railway staging readiness — live server still unavailable

A read-only Railway inventory confirmed the HSK AI Railway project
has a `staging` environment, but it contains only an operational
PostgreSQL service (`Postgres-Iy93`). The HSK AI app/backend and an
HTTPS staging domain are **absent** there. The production environment
separately runs the existing GitHub `main` backend and a database.

Therefore the anonymous route probe **was not run** against
any actual service. Its last CI artifact truthfully reports
`performed_requests=0`. Authenticated Free/Trial/Pro, paid-content
privacy, external CDN caching and account-switch QA remain open.
No Railway changes, deployments, domains, variables, or DB schema
were created or modified. See
`docs/I18N_P0_STAGING_ACCESS_RUNBOOK.md` for the controlled
staging provision/approval gate.
