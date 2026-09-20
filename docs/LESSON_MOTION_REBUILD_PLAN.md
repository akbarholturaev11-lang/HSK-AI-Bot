# HSK AI Lesson Motion Rebuild

Base branch: `codex/cloud-ai`
Working branch: `codex/cloud-ai-lesson-character-motion`

## Product boundary

Keep HSK AI lesson data, section order, mastery/repair queue, progress persistence, free-user limits, ads, skip-test unlock semantics, and API contracts unchanged.

Rebuild only the presentation/reaction layer around that logic:
- lesson entry transition;
- original HSK AI character cast;
- per-answer character reactions;
- heart-loss / one-heart warning presentation;
- lesson completion cinematic;
- map locked/unlock motion.

No Duolingo art, audio, character geometry, or proprietary assets are copied. The reference recordings are used only for interaction timing and motion grammar.

## What exists already in course-v3.html

The current implementation already has useful primitives:
- `#flow`, `#f-prog`, `.fheart`, `showBar()`, `Flow.pick()`, `Flow.next()`;
- `openLessonSheet()`, `startLesson()`, `flowDone()`;
- `openLockedLessonSheet()`, `offerSkipTest()`, `completeSkipUnlock()`;
- `PANDA_FX`, `pandaFx()`, `cinePanda()`, `pandaChar()`;
- lesson-end XP/streak screens;
- free-user start/completion gates and lesson-end ad flow.

This means the rebuild must extend those seams instead of creating a second lesson engine.

## Recording-derived timing targets

### Lesson entry
Reference sequence:
1. map / entry action;
2. short character gate;
3. very short clean transition;
4. mascot centered in a loading/reading pose;
5. lesson UI cross-fades in underneath;
6. mascot leaves and first lesson card becomes interactive.

Target total perceived transition: about 1.2–1.8 s after lesson data is ready.
Do not hold a blank screen for more than ~200 ms.

### Answer feedback
Correct:
- answer locks;
- green state + short sound/haptic;
- character reacts 450–750 ms;
- Continue stays immediately reachable.

Wrong:
- red state + sound/haptic;
- one heart is visually removed;
- character reacts without shaming the learner;
- at 1 remaining heart, a stronger warning beat is shown once.

### Lesson finish
Preserve existing server completion and XP/streak logic.
Replace presentation sequence only:
1. completion saved;
2. character cinematic;
3. result/XP card;
4. unlock path animation if next lesson became available;
5. existing free-user lesson-end ad/promo logic runs in its current order.

## Original HSK AI cast

1. **Panda — main coach**
   - role: default mentor / pronunciation / rescue reaction
   - character: patient, warm, confident
   - moods: idle, talk, correct, wrong, celebrate, proud, one-heart, loading

2. **Chinese dragon — energy / milestone**
   - role: streaks, exit checks, major correct chains, lesson finish
   - character: energetic, theatrical, competitive
   - moods: idle, talk, correct, wrong, celebrate, proud, one-heart, loading

3. **Red-crowned crane — grammar / precision**
   - role: grammar explanations and careful corrections
   - character: calm, exact, slightly strict
   - moods: idle, talk, correct, wrong, celebrate, proud, dismissive, loading

4. **Golden monkey — drills / dialogue**
   - role: matching, fast review, dialogue
   - character: playful, quick, cheeky
   - moods: idle, talk, correct, wrong, celebrate, proud, dismissive, loading

5. **Jade rabbit — memory / warning**
   - role: review cards, heart warning, gentle retry
   - character: observant, skeptical, caring
   - moods: idle, talk, correct, wrong, celebrate, proud, dismissive, one-heart, loading

Panda remains the dominant character. Other characters add variation; they do not replace the product mascot.

## Build sequence

### Phase 1 — Character pack
Create the five characters as reusable lightweight 2.5D SVG rigs, independent from the lesson engine. Add a character lab preview. Do not touch lesson logic.

### Phase 2 — Motion/effect engine
Create reusable effects: enter, pop, jump, proud nod, side-eye, recoil, laugh, one-heart pulse, loading/read, celebrate, exit. Support `prefers-reduced-motion`.

### Phase 3 — Lesson entry
Wire the central mascot loading transition into `startLesson()` after lesson data is available and before `#flow` becomes interactive. No changes to queue construction or API calls.

### Phase 4 — In-lesson reactions + hearts
Wire reactions into the existing grading seams (`showBar`, builders, matching, pronunciation). Add visual heart-loss and one-heart warning while keeping HP semantics intact.

### Phase 5 — Lesson completion
Use the existing `flowDone() -> applyLessonDone() -> showLevelUp()` path. Replace only the presentation layer and preserve ads, XP, streak and persistence.

### Phase 6 — Locked/unlock motion
Keep premium lock and skip-test behavior. Animate only the map state transition when a lesson becomes available.

### Phase 7 — Validation
Check:
- current lesson, completed lesson, ordinary locked lesson and premium locked lesson;
- HP 5→4, 2→1, 1→0;
- correct/wrong on choice, builder, matching and pronunciation;
- free vs paid user completion;
- resume after reload;
- reduced motion;
- Telegram iOS/Android WebView viewport and safe-area behavior.


## Implementation status

- Phase 1 — DONE: five-character SVG cast + Character Lab.
- Phase 2 — DONE: reusable motion/effect engine with reduced-motion support.
- Phase 3 — DONE: centered lesson-entry mascot gate, cross-fade and exit motion.
- Phase 4 — DONE: answer feedback cast mapping, builder/reverse-builder heart animation, match reaction, one-heart warning, Foundation feedback.
- Phase 5 — DONE: Panda ordinary lesson finish, Dragon checkpoint/level finish, combo cast integration; existing XP/streak/ad ordering preserved.
- Phase 6 — DONE: server-confirmed map unlock reveal plus skip-test unlock presentation.
- Phase 7 — PARTIAL: JavaScript syntax/static integration checks pass. GitHub Actions has no run/status for this branch. Physical Telegram iOS/Android WebView QA still requires a deployed/review build.

Current presentation integration branch: `codex/cloud-ai-lesson-character-motion`.
