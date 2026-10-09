package com.pomp.hskai.feature.foundation

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Answer material must not make a listen-and-choose card solvable by reading. */
class FoundationListeningVisibilityTest {
    @Test
    fun no_answer_is_visible_before_the_first_attempt() {
        assertFalse(foundationListeningExampleVisible(null))
    }

    @Test
    fun incorrect_attempt_does_not_reveal_the_listening_answer() {
        assertFalse(foundationListeningExampleVisible(false))
    }

    @Test
    fun confirmed_correct_answer_can_reveal_the_explanation() {
        assertTrue(foundationListeningExampleVisible(true))
    }
}
