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
The current report is produced in [CI run 38999948668](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/38999948668)
and is archived under `hsk-i18n-p0-audit`. The localization-specific test
step passed. Check the complete workflow conclusion independently.

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
