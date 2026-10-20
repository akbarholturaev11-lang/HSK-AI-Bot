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

## Mini App P3 reservation-only integration (protected runtime gate)

Mini App P3 translation display values are supplied by the existing signed
`POST /api/v3/lesson/start` **allowed** response, never an anonymous
public lesson-content pack. The server must validate Telegram initData,
user track/lesson unlock and the existing consume=True entitlement BEFORE
returning any P3 translation values. Denied responses carry no locale patch.
No extra per-string request. The browser must apply to an isolated copy
after successful reservation, check all original Chinese+pinyin targets
and whitelisted, previously blank grammar/mirror display slots atomically,
and fall back to its unchanged legacy cached lesson on any mismatch.
Preserve the original direct static JSON prefetch and its purpose; it does
not authorize translation access. Native/Desktop continue using their
shared auth-gated course service. Do not claim production deployment merely
from source CI.

Regression prevention: the giant `app/static/course-v3.html` file has
exact physical line anchors (8712 lines) and a reviewed original/new blob
manifest. NEVER insert line breaks casually into the live HTML or relax
existing line-classification tests just to pass migration. Use a small
versioned local JS asset and minimal same-line call-site edits, then
update `localization/baselines/reviewed_ui_changes.json` to exactly pin
the new source Git blob. Existing 58-failure CI regression was repaired this
way and P0 passed 331 tests. ASGI 200/403 Mini App entitlement tests plus
Node atomic-patch smoke belong to the required code review gates.

## Completed Mini App lesson review must honor explicit server denial

Regression discovered 2026-10-19: `reserveCompletedP3Grammar()` previously
returned `allowed:true` even when the authenticated reservation endpoint
explicitly returned HTTP 401/403 or `allowed:false`. A client-side
`status==="done"` snapshot is not authoritative when server progress,
account or entitlement state differs. The agent fixed this in
`app/static/course_v3_data/p3-grammar-reservation.js`: explicit server denial
throws a structured lesson-access error that the existing lesson-start UI
handles; **only genuine network/service failures retain the old offline
completed-lesson fallback**. Tests must cover both 401 and 403, an explicit
200 with `allowed:false`, offline, and no residual P3 patch. Do not
reintroduce unconditional `.catch(() => ({allowed:true}))` or weaken the
signed Telegram server gate to improve translation availability.

Cross-platform P3 parity regression: test **all 48 affected lessons**,
not only lesson 16. For every returned Mini App display pointer confirm
the authenticated native adapter produces exactly the same UZ/RU/TJ value,
the original source still has an empty display map, and no assessed/Pro
fields are exposed. Expected totals: 272 original display maps, 136 mirrored
maps and 1,224 locale display values. Any new mapping failure must become a
scoped regression test before an agent can call P3 released.

## Completed P3 reviews must retain shared entitlement and explicit HTTP grants

Root cause (2026-10-19): Mini App `review_only:true` checked signed
Telegram identity and completed progress, but skipped the shared
`LessonAccessService.status` check. Unlike native/Desktop, a blocked user
or an account whose HSK 3.0 track is no longer entitled could reach
the P3 display patch. Another browser-side path converted any response
other than an explicit 401/403 into `allowed:true` even for HTTP 500 or
malformed HTTP 200; its reserved patch was not cleared inside the
completed-review helper before starting a new request.

Fix: After signed identity, server-completed progress and lesson-order
checks, call the **existing** `LessonAccessService.status(..., consume=False)`
and fail with HTTP 403/no P3 patch if denied. Do not spend a quota slot on
completed revisit. At the browser call site, clear stale reserved translations,
accept **only** `response.ok && body.ok === true && body.allowed === true`,
and propagate all other HTTP decisions as access errors. Retain legacy
offline already-completed reading **only** for real rejected network/transport
promises, and never adopt P3 while offline.

Regression: `tests/test_i18n_miniapp_reservation_asgi.py` covers the
read-only service decision, quota-free completed review, revoked/blocked
denials with zero P3 data, signed auth and non-object JSON bodies.
`tests/test_i18n_miniapp_grammar_reservation.py` executes JS response
denial, malformed success, stale-patch clearing and offline fallback.
These synthetic tests do not prove real payment/track configurations, devices,
or production session policy. Repeat with real authenticated test accounts.

Prevention: **progress proves completion, not entitlement**. No P3
translation read path may skip the shared blocked/track/access gate.
Only an explicit successful HTTP entitlement decision may authorize
localized reading; non-network HTTP errors must never become offline grants.

## Chinese-context semantic corrections: G030, G128, G131 (2026-10-19)

- `G030`, `画我们的家！有爸爸、妈妈、弟弟……`: family members
  and pets are being drawn; Russian `наш дом` falsely points to a building.
  The canonical RU cell now says `нашу семью`.
- `G131`, `烤鸭` (*kǎoyā*): roast **duck**, not chicken; the
  previous Tajik `мурғи бирён` implied chicken. Keep duck species in all
  three locales, and distinguish roasting from pan-frying. Current UZ,
  RU and TJ canonical entries have been updated accordingly.
- `G128`, `虽然去过一次，但是很想再去一次`: preserve the
  desire to **visit again** and use natural Tajik wording, not the
  calqued `боз рафтанам хеле мехоҳад`.

These corrections are pinned by the existing Chinese-context SHA and
`tests/test_i18n_canonical_grammar_catalog.py` semantic regressions.
Prevention: when a Chinese noun has multiple meanings or names an animal
or dish, read the enumerated objects and grammatical context rather than
translating token by token. This focused fix does not certify all 408
independent values or real-device display QA.

## Additional source-aligned fixes: G051, G109 (2026-10-19)

- `G051` `我看网上说……`: Russian omitted the learner's
  observation entirely (`В интернете пишут...`). The central Russian
  version now uses a neutral first-person experiencer
  (`Мне попадалось в интернете...`) rather than inserting a
  masculine `Я прочитал` the Chinese does not require.
- `G109` `他卖给我一本中文书。`: Uzbek `kitobni sotdi`
  incorrectly made the object definite and dropped `一本`. The
  localized text now says `xitoy tilidagi bir kitob sotdi`.
- The same pinned 136-context canonical TSV and
  `tests/test_i18n_canonical_grammar_catalog.py` carry these
  corrections. Whenever correcting explicit subject/quantity or
  aspect semantics, independently check gender, definiteness and
  tense introduced in the target language.

Local isolated executable JS smoke evidence (NOT GitHub CI):
`app/static/course_v3_data/p3-grammar-reservation.js` was matched
byte-for-byte by Git blob hash `ab2956e4b6a7da339ddb6531b0b5a8acfa8cd291`
and passed Node 22 `--check` plus nine runtime scenarios: explicit
grant, 401, 403, 500, HTTP-200 explicit deny, HTTP-200 malformed
response, network offline fallback without P3, isolated successful
locale patch, and changed-Chinese target rejection. Backend ASGI,
Android/Desktop emulator, real Telegram WebView and latest GitHub CI
still require independent execution.

## Mini App P3 must reject incomplete-but-valid locale patch sets

Root cause (2026-10-20): `applyReservedP3Grammar` validated each received
`/grammar/...` or `/_grammar`-mirror path independently, but never verified
that **every** originally blank source display map was represented. Dropping
a mirrored row left a syntactically valid subset and returned a partially
localized lesson; another accepted pointer could target an unrelated card's
`g.examples` field despite the `_grammar` type invariant.

Fix: derive a strict whitelist of **all and only** originally blank grammar
example and `type === "_grammar"` mirror translation paths from the loaded
lesson. Reject unless the response row count matches that expected set and
**every** pointer belongs to it; preserve the existing duplicate, Chinese,
pinyin, three-language, source-id and atomic-clone guards. This check remains
local and synchronous; no new request, static pack or grading/Pro change.
For verified affected source files, 48 lessons contain 272 root gaps and 136
mirrored card gaps (408 total patch locations). Some repeated checkpoint
lessons contain no additional `_grammar` mirror, so **never** assume a fixed
2× multiplier per lesson.

Regression: `tests/test_i18n_miniapp_grammar_reservation.py` rejects a
missing mirror row, an unrelated `meaning_guess` card pointer, changed
Chinese and attempts to run all 48 original lessons with their actual
source-pinned patches in Node (stdin, no gated text in CLI output). Direct
Node syntax/runtime smoke was run against Git blob
`a90dfa1a07b585bcb236d85dc815612415417e8c` for the core rejection
cases. Latest GitHub Actions/real device CI must still be verified separately.

Prevention: the frontend must verify **whole-set completeness** independently
of any server-declared count, not just validity of individual source pointers.
Reject a partial response as a whole; never publish mixed blank/localized
course grammar. Keep source/graded payload bytes untouched.

## Independent 136-context source reading: 2026-10-20

The agent read all 136 unique grammar examples against the original nHSK2
lesson source (48 affected lessons, including repeated checkpoint contexts),
with each associated UZ/RU/TJ row from the source-hash-pinned canonical TSV.
This is a first complete independent Chinese-context semantic pass, NOT
native-speaker certification or device acceptance. The pass identified and
fixed six locale cells across three contexts, in the canonical catalog only:

- `G019` `你们太客气了，还拿这么多礼物来！`: `客气` in the
  gift-receiving social context indicates excessive courtesy or trouble
  taken, not simply the personality trait `kind`. UZ now refers to taking
  trouble (`ovora bo‘libsizlar`) and Tajik to effort/trouble (`ташвиш
  кашидаед`); the existing idiomatic Russian social response was retained.
- `G023` `妈妈拿出了二十块钱，让小雪自己去买点儿吃的。`:
  the causative request/instruction `让...自己去买` in this context does
  not explicitly say `gave permission`. Replaced permission-only readings
  in **UZ, RU, TJ** with the mother telling Xiaoxue to buy something to
  eat by herself. Do not misinterpret every `让` as `permit`, `ask`, or
  `force` in isolation; use the full subject/verb setting.
- `G135` `你女儿今年有10岁了吧？`: clause-final `吧` is an
  expectation/confirmation, not a neutral direct yes/no question and does
  not prove the exact day the child turned ten. UZ now says the daughter
  is probably ten this year (`bo‘lsa kerak, shundaymi?`). RU/TJ already
  preserved confirmation and remain unchanged.

`tests/test_i18n_canonical_grammar_catalog.py` binds these specific
Chinese source contexts to the corrected meanings. Frozen lesson JSON,
Chinese/pinyin, answers/grading and subscription checks remain untouched;
full P0 and authenticated device/WebView QA must still be reconfirmed
on the new HEAD. All 408 independent text cells were read in this pass,
but semantic review should continue when new contextual evidence appears.

## Current-lesson HTTP-200 entitlement responses must be explicit

Root cause (2026-10-20): the normal Mini App current-lesson
`reserveLessonStart(l)` browser branch previously checked
`!r.ok || !d.ok || d.allowed === false`. A syntactically successful
HTTP 200 body with `ok: true` but **without any `allowed` field**
therefore resolved as a permitted reservation. The completed-lesson
P3 branch was already fail-closed; the ordinary current branch was not.
The actual server `LessonAccessService.status(..., consume=True)`
returns an explicit access decision, so a missing decision is a malformed
response, not permission.

Fix: require all of `HTTP response.ok`, `body.ok === true` and
`body.allowed === true` on current reservations. Do not turn an HTTP
failure or malformed 200 into an offline grant. The signed server remains
the authority; do not consume a second time or modify the course
lesson/quiz/Pro rules. The change is **same-line only** in
`app/static/course-v3.html`, preserving 8712 physical lines and
all classified anchor positions. The exact new reviewed Git blob
`4d40834086f9cda19dcafbc53df590d4974f4eff` is pinned in
`localization/baselines/reviewed_ui_changes.json`.

Regression: `tests/test_i18n_miniapp_grammar_reservation.py`
executes the real extracted current reservation JS via Node. It tests
HTTP 200 with missing `allowed`, explicit deny, missing `ok`, HTTP 403,
malformed success, and valid explicit 200 grant, as well as clearing
stale P3 state. Keep this test in P0 CI. Legacy anonymous/offline
static lesson JSON remains a *separate unresolved security review risk*;
this narrow fix does not make publicly served lesson JSON private.

## G066/G069/G130 semantic actor and implied-event corrections (2026-10-20)

- **Root cause:** In lesson 43, `G066` `李文等了她一个小时。` and `G069`
  `李文等她等了一个小时。` say that Li Wen **waited for her** for one hour.
  Prior Russian `На ожидание её прихода...` asserted her eventual **arrival**
  without evidence, turning waiting into a result. Both RU rows now use
  `Ли Вэнь ждал её целый час.`; UZ and TJ remain source-aligned.
- **Root cause:** In lesson 70 (and repeated lesson 73), `G130`
  `李文见了杨同乐两次。` has Li Wen as the subject and Yang Tongle as
  the object of two sightings. The former Russian plural
  `встречались дважды` turned the subject-object statement into
  a mutual meeting. The canonical RU row now reads
  `Ли Вэнь дважды видел Ян Тунлэ.` UZ and TJ are unchanged.
- **Fix and prevention:** Change only the three Russian cells of the
  exact 136-row, source-SHA-pinned canonical TSV. The reviewed original
  lesson blobs, Chinese and grammar rules, pinyin, answer tokens, scoring,
  access checks and mirror targets stay unchanged. New source-bound
  `tests/test_i18n_canonical_grammar_catalog.py` regressions assert exact
  Chinese contexts, retention of time and direction/agent, and absence of
  invented outcomes. Structural/source/mirror CI and authenticated
  cross-platform rendering still need separate verification; these three
  corrections do not certify all 408 localized values.
