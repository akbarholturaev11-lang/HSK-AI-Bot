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
