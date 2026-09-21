package com.pomp.hskai.feature.practice

import com.pomp.hskai.core.design.components.HskCharacter
import com.pomp.hskai.core.design.components.HskCharacterMood
import com.pomp.hskai.core.design.components.HskCharacterReaction
import com.pomp.hskai.data.api.PracticeQuestionDto

/**
 * Practice's half of the character system: WHICH character each practice
 * screen gets. The cast, its moods and its motion are shared with the lesson
 * ([com.pomp.hskai.core.design.components.HskCharacterStage]).
 *
 * Every choice below keys off the cast ROLE declared in the Mini App pack
 * (`app/static/assets/characters/hsk-character-pack.js`), not off taste:
 *
 * | role               | character | what it owns                |
 * |--------------------|-----------|-----------------------------|
 * | `main_coach`       | Panda     | the default voice           |
 * | `grammar_precision`| Crane     | grammar, reading precision  |
 * | `drill_dialogue`   | Monkey    | listening, speaking, drills |
 * | `memory_warning`   | Rabbit    | anything being re-reviewed  |
 * | `energy_milestone` | Dragon    | a milestone worth a bang    |
 *
 * The HSK exams deliberately have no character at all: an exam withholds
 * correctness until the end (`ExamRun` passes `false` for both correct and
 * wrong option states), and a coach that reacts to an answer would hand the
 * learner the answer. The placement test is not in that position — it shows
 * the right answer and an explanation after every question — so it keeps one.
 */

/** The listening types the practice service emits; see `_skill_match`. */
private val LISTENING_TYPES = setOf("listening_choice", "listen_and_fill")

/**
 * Placement test. A question the learner has to HEAR belongs to the dialogue
 * drill role; everything else is the main coach's.
 */
internal fun practiceCharacterFor(question: PracticeQuestionDto): HskCharacter = when {
    question.audioText.isNotBlank() -> HskCharacter.Monkey
    question.type in LISTENING_TYPES -> HskCharacter.Monkey
    else -> HskCharacter.Panda
}

/**
 * Mistake review. Rabbit owns the review as a whole, but a mistake keeps the
 * subject it came from — grammar stays the crane's, pronunciation stays the
 * monkey's. Categories come from the server (`word`, `grammar`, `character`,
 * `pronunciation`).
 */
internal fun mistakeCharacterFor(category: String): HskCharacter = when (category) {
    "grammar" -> HskCharacter.Crane
    "pronunciation" -> HskCharacter.Monkey
    else -> HskCharacter.Rabbit
}

/**
 * Word drills. Recognition is precision work on the written character;
 * pronunciation is the spoken half of the dialogue drill.
 */
internal fun drillCharacterFor(mode: DrillMode): HskCharacter = when (mode) {
    DrillMode.RECOGNITION -> HskCharacter.Crane
    DrillMode.PRONUNCIATION -> HskCharacter.Monkey
}

/**
 * The face that closes a session. A clean sweep is a milestone and gets the
 * dragon — the same character the lesson gives a checkpoint. A weak result
 * gets the rabbit, whose role is "come back to this", NOT a sad panda: the
 * screen already says the score, and a coach sulking at the learner is the
 * kind of thing that makes people stop opening the app.
 */
internal fun completionCharacterFor(reaction: PracticeCompletionReaction): HskCharacter =
    when (reaction) {
        PracticeCompletionReaction.CELEBRATE -> HskCharacter.Dragon
        PracticeCompletionReaction.CHEER -> HskCharacter.Panda
        PracticeCompletionReaction.CALM -> HskCharacter.Panda
        PracticeCompletionReaction.FOCUS -> HskCharacter.Rabbit
    }

/**
 * Completion moods stay on the encouraging half of the range for the same
 * reason: [HskCharacterMood.Wrong] never closes a session.
 */
internal fun completionMoodFor(reaction: PracticeCompletionReaction): HskCharacterMood =
    when (reaction) {
        PracticeCompletionReaction.CELEBRATE -> HskCharacterMood.Celebrate
        PracticeCompletionReaction.CHEER -> HskCharacterMood.Correct
        PracticeCompletionReaction.CALM -> HskCharacterMood.Proud
        PracticeCompletionReaction.FOCUS -> HskCharacterMood.Idle
    }

/**
 * How the closing character enters. A milestone gets the full burst; the rest
 * pop in, which is an entrance rather than a verdict.
 */
internal fun completionReactionFor(reaction: PracticeCompletionReaction): HskCharacterReaction =
    when (reaction) {
        PracticeCompletionReaction.CELEBRATE -> HskCharacterReaction.Celebrate
        else -> HskCharacterReaction.Pop
    }

/**
 * The mood a question card shows while it waits, and after it is answered.
 * [answered] being null means the learner has not committed yet.
 */
internal fun practiceMoodFor(answered: Boolean?): HskCharacterMood = when (answered) {
    null -> HskCharacterMood.Idle
    true -> HskCharacterMood.Correct
    false -> HskCharacterMood.Wrong
}
