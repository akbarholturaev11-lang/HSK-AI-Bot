package com.pomp.hskai.feature.lesson

import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * A lesson question is answered in two steps: a tap only picks, Tekshirish
 * checks. Before the check nothing may give the answer away.
 */
class LessonOptionStateTest {

    private fun states(selected: Int?, answered: Boolean, correct: Int = 1) =
        (0..2).map { lessonOptionState(it, correct, selected, answered) }

    @Test
    fun nothing_is_lit_before_a_pick() {
        assertEquals(
            List(3) { LessonOptionState.IDLE },
            states(selected = null, answered = false),
        )
    }

    @Test
    fun a_pick_lights_only_itself_and_reveals_nothing() {
        // The pick is wrong (0, the right one is 1): still only the pick is lit.
        assertEquals(
            listOf(LessonOptionState.SELECTED, LessonOptionState.IDLE, LessonOptionState.IDLE),
            states(selected = 0, answered = false),
        )
    }

    @Test
    fun after_the_check_the_right_answer_and_the_wrong_pick_show() {
        assertEquals(
            listOf(LessonOptionState.WRONG, LessonOptionState.CORRECT, LessonOptionState.IDLE),
            states(selected = 0, answered = true),
        )
    }

    @Test
    fun a_right_pick_is_simply_correct() {
        assertEquals(
            listOf(LessonOptionState.IDLE, LessonOptionState.CORRECT, LessonOptionState.IDLE),
            states(selected = 1, answered = true),
        )
    }
}
