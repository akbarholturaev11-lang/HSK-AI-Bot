# Design

## Context

- Lesson parts are static JSON (`app/static/course_v3_data/<level>/lesson_NN.json`,
  generated, 11–18 cards, median 18). Sections: `intro` (teach + check),
  `grammar`, `practice`, `dialog`, `retention_review`, N1 `learning_exit_check` /
  `learning_repair_bank`, plus an optional `exit_ticket` outside `sections`.
- Mini App/PWA receives the raw lesson from
  `GET /api/v3/lesson/content/…` / `/api/v3/pwa/lesson/content/…`
  (`miniapp_entitlements._lesson_content_for_user`); Android receives it inside
  `GET /api/v3/android/course/lesson/{n}` (`AndroidCourseService.lesson`).
  **Both clients compute `material_ref` from the original section/card
  position** (`lessonMaterialRef` in `course-v3.html`, `LessonParser.materialRef`),
  and the server re-grades mistakes from that reference.
- Resume is an index into the client queue (`hsk_v3_lesson_resume`,
  `LessonResumeStore`), so the queue for a given learner and lesson must be
  deterministic.
- Pronunciation is already graded by `VoicePracticeService.score_pronunciation`
  (STT + hanzi/pinyin match, pass ≥ 60, free daily quota 25, server-side
  mastery and mistake writes). Lesson pronunciation cards already use it
  through `/api/voice-practice/pronounce`, `/api/v3/pwa/voice/pronounce`,
  `/api/v3/android/voice/pronounce`.
- Onboarding stores `daily_minutes ∈ {5,10,15,20,30}`, `goal`, `goals_json`,
  `preferred_focus`. `DailyPlanService._goal_weights` already defines how a
  primary goal (60%) and extra goals (40%) are mixed.

## Goals / Non-Goals

**Goals:** identical, server-decided lesson composition for PWA and Android;
length bounded by onboarding minutes and goal; goal/focus-relevant practice
kept; picture pronunciation deck graded by the existing check; zero impact
with the flag off.

**Non-Goals:** Desktop renderer; changing lesson JSON, `material_ref`, XP,
streak, completion API, daily plan or UIUX-007; new images/CDN; new analytics
events; self-assessment.

## Decisions

1. **Plan, not mutation.** The server appends `lesson.lesson_plan`
   (`version: 1`). Cards are never removed from the JSON; clients skip
   `omit` positions after assigning `material_ref`, so server re-grading,
   P3 grammar overlays and source SHA guards are untouched.
2. **What may be trimmed.** Only cards in `practice` and `retention_review`
   sections without `objective_id`, `learning_objective` or `learning_retry`.
   `intro` (new-word teaching), `grammar`, `dialog`, N1 learning sections and
   the exit ticket are always kept.
3. **Length budget** (base-card units, one picture card = 0.5 unit):
   minutes→units `5:14, 10:18, 15:21, 20:24, 30:27`; goal shift
   `hsk_exam +2, study_china +1, work_china 0, daily_communication −1,
   travel −2`, mixed 60/40 like `_goal_weights`. Picture cap by minutes
   `5:4, 10:6, 15:8, 20:10, 30:10`. Protected cards always stay even above
   the budget.
4. **Goal-aware selection.** Card type → skill: `pronunciation`→speaking,
   `listening_choice`→listening, choice/match/quiz→vocabulary,
   builders/gap/dialog cloze→grammar. Goal skill weights (0–3) are mixed
   60/40, `preferred_focus` adds 1.5, retention review adds 0.3, repeated
   skills decay ×0.6. Picture cards are speaking items worth 0.4 of a card,
   decaying ×0.85. Items are chosen greedily by value per unit until the
   budget is full; kept cards stay in original order.
5. **Learned words only.** Candidates are `active_words` of earlier parts of
   the same source lesson (most recent first), then earlier parts of the same
   level (most recent first). Words of the current part and of other levels
   are never used. Max 10, unique hanzi and unique picture per deck.
6. **Exact pictures.** A curated `lesson_picture_words.json` maps hanzi →
   system emoji per level where the picture names the word unambiguously
   (abstract words, emotions and collisions such as 杯子/牛奶 excluded).
   Missing entry → word not used. Android additionally drops a card whose
   emoji has no glyph on the device (`Paint.hasGlyph`, minSdk 26).
7. **Deck placement.** Before the `retention_review` section, else at the end
   of the last non-exit section. One lesson step; Android/PWA adaptive review
   (graded-card boundaries only) is unaffected.
8. **Grading.** Existing pronounce endpoints; pass ≥ 60. Empty transcript →
   `unclear`, no verdict, no mastery/mistake write. Network/AI error → retry
   hint, no verdict. `PRONOUNCE_LIMIT_EXCEEDED` → existing limit UI and the deck
   ends. Deck results do not change lesson accuracy, hearts, XP or mistakes
   payload (server already records pronunciation mastery/mistakes).
9. **Rollout.** `COURSE_LESSON_PLAN_ENABLED` + allowlist + stable percent
   bucket (`rollout_bucket`). Offline Android copies and PWA `preview_half`
   lessons ignore the plan.

## Risks / Trade-offs

- Resume index may shift if the learner changes daily minutes/goals in the
  middle of a lesson part (one-card offset; lesson remains completable).
- STT is hinted with the target (existing behaviour); a wrong but similar
  utterance can still pass — same as today's pronunciation cards.
- Free users spend pronunciation quota faster; the deck stops at the limit.
- Emoji look differs between iOS and Android vendors; meaning is identical.
- Rollback: flag off → no plan → original lessons on both clients.
