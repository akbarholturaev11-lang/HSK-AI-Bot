package com.pomp.hskai.feature.practice

import com.pomp.hskai.core.design.components.HskCharacter
import com.pomp.hskai.core.design.components.HskCharacterMood
import com.pomp.hskai.core.design.components.HskCharacterReaction
import com.pomp.hskai.core.design.components.hskReactionFor
import com.pomp.hskai.data.api.PracticeQuestionDto
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * Locks the practice screens onto the Mini App cast ROLES
 * (`app/static/assets/characters/hsk-character-pack.js`), the same way
 * `LessonCharacterParityTest` locks the lesson. A character picked by taste
 * instead of by role is exactly what drifts between the two clients.
 */
class PracticeCharacterParityTest {

    @Test
    fun a_heard_question_belongs_to_the_dialogue_drill_role() {
        assertEquals(
            HskCharacter.Monkey,
            practiceCharacterFor(PracticeQuestionDto(audioText = "你好")),
        )
        assertEquals(
            HskCharacter.Monkey,
            practiceCharacterFor(PracticeQuestionDto(type = "listening_choice")),
        )
        assertEquals(
            HskCharacter.Monkey,
            practiceCharacterFor(PracticeQuestionDto(type = "listen_and_fill")),
        )
    }

    @Test
    fun a_read_question_stays_with_the_main_coach() {
        assertEquals(
            HskCharacter.Panda,
            practiceCharacterFor(PracticeQuestionDto(type = "multiple_choice")),
        )
    }

    @Test
    fun a_mistake_keeps_the_subject_it_came_from() {
        assertEquals(HskCharacter.Crane, mistakeCharacterFor("grammar"))
        assertEquals(HskCharacter.Monkey, mistakeCharacterFor("pronunciation"))
        // Everything else is the review's own role: memory_warning.
        assertEquals(HskCharacter.Rabbit, mistakeCharacterFor("word"))
        assertEquals(HskCharacter.Rabbit, mistakeCharacterFor("character"))
        assertEquals(HskCharacter.Rabbit, mistakeCharacterFor(""))
    }

    @Test
    fun the_drills_split_precision_from_speech() {
        assertEquals(HskCharacter.Crane, drillCharacterFor(DrillMode.RECOGNITION))
        assertEquals(HskCharacter.Monkey, drillCharacterFor(DrillMode.PRONUNCIATION))
    }

    @Test
    fun a_milestone_closes_on_the_dragon_and_a_weak_run_never_sulks() {
        assertEquals(
            HskCharacter.Dragon,
            completionCharacterFor(PracticeCompletionReaction.CELEBRATE),
        )
        assertEquals(
            HskCharacter.Rabbit,
            completionCharacterFor(PracticeCompletionReaction.FOCUS),
        )
        // A session must never end on a disappointed face.
        PracticeCompletionReaction.values().forEach { reaction ->
            assertEquals(
                "$reaction must not close on a wrong-answer mood",
                false,
                completionMoodFor(reaction) == HskCharacterMood.Wrong,
            )
        }
    }

    @Test
    fun practice_climbs_the_same_reaction_ladder_as_the_lesson() {
        // No practice screen has hearts, so the last-heart rung is out of
        // reach — the ladder is shared rather than forked.
        assertEquals(
            HskCharacterReaction.Wrong,
            hskReactionFor(correct = false, streak = 0),
        )
        assertEquals(
            HskCharacterReaction.Jump,
            hskReactionFor(correct = true, streak = 1),
        )
        assertEquals(
            HskCharacterReaction.Celebrate,
            hskReactionFor(correct = true, streak = 4),
        )
    }

    @Test
    fun an_unanswered_question_shows_no_verdict() {
        assertEquals(HskCharacterMood.Idle, practiceMoodFor(null))
        assertEquals(HskCharacterMood.Correct, practiceMoodFor(true))
        assertEquals(HskCharacterMood.Wrong, practiceMoodFor(false))
    }
}
