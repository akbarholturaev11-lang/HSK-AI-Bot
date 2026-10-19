# HSK AI P3 — agent-owned translation QA and local-first integration

This is the controlling policy for EXISTING UZ/RU/TJ lesson translations as
explicitly delegated by the product owner on 2026-10-19. Earlier P3 worksheets,
draft statuses and handoffs refer to a "mandatory human reviewer"; treat those
as historical process wording, **not** a current human-approval prerequisite.
It is the agent's responsibility to perform and document the actual QA.

## Agent responsibility (no user linguistic homework)

1. The agent reads the real Chinese source example AND the grammar rule, lesson
   setting, subject, aspect, direction, number, time and proper-name context.
   Check each proposed Uzbek, Russian and Tajik string individually. Do not
   blindly reuse a syntactically valid AI draft or treat passing P0 as semantic
   proof. Never claim independent/native-speaker certification if none occurred.
2. The agent fixes wrong meaning, omitted negation, misleading pronoun/gender,
   tense/aspect, directional 来/去, quantity, cultural names or unnatural copy.
   Use neutral language for source ambiguity; NEVER invent unseen subjects,
   referents or pinyin. For repeated exact Chinese+grammar contexts, propagate
   the same corrected UZ/RU/TJ text to every source pointer.
3. The agent is the QA owner: DO NOT block progress asking the user to read
   Chinese, Uzbek, Russian or Tajik or obtain an outside editor's signoff.
   If an ambiguity cannot be resolved with available source, record the
   exact unresolved context for follow-up and DO NOT silently publish that
   particular misleading string; proceed on other verified contexts.
4. Before integration validate each original lesson Git blob SHA, accepted
   grammar-display pointer whitelist, all 3 nonblank NFC strings, every
   duplicate exact-context occurrence, mirrored _grammar source equality,
   and a protected-tree diff proving no Chinese/pinyin, answers, grading,
   paywall, Pro, user/auth or unrelated content changed.
5. Move reviewed translations into the existing local-first course model only
   after the above quality gates; keep all platform resources deterministic.
   No per-string remote API, no new server dependencies or gated-content
   exposure. Verify Mini App, Android, Desktop and Bot consumption/fallback
   along affected paths, and preserve the frozen P0 baseline via a narrow
   audited lesson-content migration manifest or an equivalent explicit diff.
6. Run focused tests, source-wide counts, Android/Desktop native checks when
   available and the relevant integration smoke tests. No skipped failing
   gate is "SUCCESS". Feature branch/PR is the safe staging area while checks
   or merge conflicts remain. Merge to main/release only when the applicable
   code, security and platform QA gates pass; do not deploy merely because
   translations were syntactically valid.
7. For every confirmed bug, document root cause, correction, regression test,
   and preventive rule in this policy or relevant knowledge/bugs entry. Future
   agents must reuse the lesson, not repeat the bug. Keep a source-SHA-bound
   QA/change ledger without personal data or private source content in CI logs.

## Known reproducible error classes

- Chinese `昨天比今天下得大。` has no rain/snow noun in that example:
  do not assert snow or rain without sufficient context. Check adjacent
  lesson context; otherwise translate neutrally (stronger precipitation).
- Russian `был(а)` / `возвращался(ась)` and similar parenthetical gender
  markers are translator placeholders, not polished learner copy. Prefer
  an idiomatic gender-neutral construction when exact meaning is preserved.
- `来` is movement toward the discourse speaker and `去` away from that
  reference point; distinguish `上来/上去/下来/下去` and object order.
- `过` experiential aspect is not mechanically the past tense; `着`
  sustained state is not a completed action. Avoid asserting gender or
  completed actions that Chinese does not encode.
- The original 136 Chinese grammar examples have no source pinyin; do not
  fabricate a purported original reading, especially for proper names.
- Repeated display fields in `_grammar` are not separate translator tasks.
  Any migration must maintain exact mirror parity while keeping graded
  answer fields untouched.

## Evidence and done criteria

Use source SHA + exact-context grouping + complete cross-locale count,
semantic issue list and source-diff integrity proof; never print gated answer
keys, account data or private drafts in public CI. `AI_QA_PASSED` means
agent-checked within described limits, not third-party certified. "DONE"
requires integrated reviewed content, correct client rendering and green
applicable CI and functional QA, not just a draft ZIP or private preview.

## Repeatable known-error detector

Before centralizing a completed private draft directory, run:

```bash
python scripts/i18n_editor_semantic_guard.py --draft-dir /private/drafts
```

It rejects Russian gender-placeholders such as `был(а)`, unsupported
rain/snow claims for the ambiguous `昨天比今天下得大。`, and missing snow
meaning when the Chinese explicitly says `下雪` or `下着雪`.
This detector is deliberately NOT a replacement for the agent's full
source-context semantic check; it only captures previous reproducible bugs.
CLI suppresses private text and user data. `--allow-partial` is only for
incomplete private editorial pilots, not a release gate.

Implementation regression found by Python 3.11 CI: `\b?` is invalid because
the regex engine does not allow quantifying a zero-width word boundary.
Terminate the Russian placeholder with an explicit `(?:$|\W)` boundary and
keep the P0 import/behavior tests in the supported CI Python version.

## Offline grammar display-only locale generation (P3)

`scripts/i18n_editor_grammar_local_catalog.py` generates UZ/RU/TJ
source-SHA-pinned, private local-first grammar display overlays, including
only the verified `_grammar` mirrors. Run with:

```bash
python scripts/i18n_editor_grammar_local_catalog.py \
  --draft-dir /private/source-pinned-editor-drafts \
  --private-output-dir /private/locale-display-overlays
```

Default requires full 136-context/272-original-map coverage. Expected full
batch: 48 lessons × 3 languages = **144 private locale JSON files**,
covering (272 original maps + 136 mirrored copies) × 3 = **1,224 display
locale values**. Every generated overlay excludes Chinese, pinyin, answers,
option banks, grading, Pro and account fields. The output must remain private
until the agent wires it into source-version-pinned local clients with correct
entitlement boundaries and E2E QA; it is not a public pack nor a release.
The limited regression guard detects known errors but does not replace
source-context semantic checking. Agent carries this responsibility, NOT user.

Verified on [P0 run 39241612582](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39241612582): **313 tests SUCCESS**.

## Native P3 regression: do not assume card order

Native authenticated lesson payloads use the common
`DesktopCourseService.lesson` access gate. `nhsk2` original grammar texts
are overlaid only after the existing successful unlock/entitlement checks,
with exact source SHA plus protected-diff mirror verification; failures fall
back to the original lesson. Do not expose the same new data through
unauthenticated static JSON or change answer/score/Pro logic to make
localization easier. Lesson `_grammar` cards can appear at different
indexes. Tests/clients MUST select cards using `type == "_grammar"`, not
`sections[0].cards[0]`; the mistaken index caused P0 test failure.
Android and Desktop share this service; Mini App still needs its
entitlement-safe localized read path and app QA.
