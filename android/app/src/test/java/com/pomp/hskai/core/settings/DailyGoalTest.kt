package com.pomp.hskai.core.settings

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The daily goal belongs to the account, not to this phone.
 *
 * `sanitize` used to be an allowlist of the four values the picker offered,
 * which quietly rewrote anything else. A learner who chose 40 in the Mini App —
 * a value this list did not contain — had it turned into 50 on the way in, and
 * the same account then showed 40 in one product and 50 in the other, which is
 * exactly what was reported from a phone.
 *
 * So the rule is now the server's: accept what the server would store, offer
 * what the Mini App offers.
 */
class DailyGoalTest {

    @Test
    fun `the offered choices are accepted`() {
        DailyGoal.CHOICES.forEach { choice ->
            assertEquals(choice, DailyGoal.sanitize(choice))
        }
    }

    @Test
    fun `the picker offers what the Mini App offers`() {
        // course-v3.html: opts=[20,30,40,50,80]
        assertEquals(listOf(20, 30, 40, 50, 80), DailyGoal.CHOICES)
    }

    @Test
    fun `a goal the picker does not list is still honoured`() {
        // The Mini App appends a stored value outside its own list rather than
        // replacing it, and so must this: the server is what decides.
        assertEquals(35, DailyGoal.sanitize(35))
        assertEquals(10, DailyGoal.sanitize(10))
        assertEquals(500, DailyGoal.sanitize(500))
    }

    @Test
    fun `only what the server could never have stored falls back`() {
        // miniapp_preferences.py bounds it to 10..500.
        assertEquals(DailyGoal.DEFAULT, DailyGoal.sanitize(null))
        assertEquals(DailyGoal.DEFAULT, DailyGoal.sanitize(0))
        assertEquals(DailyGoal.DEFAULT, DailyGoal.sanitize(-30))
        assertEquals(DailyGoal.DEFAULT, DailyGoal.sanitize(9))
        assertEquals(DailyGoal.DEFAULT, DailyGoal.sanitize(501))
        assertEquals(DailyGoal.DEFAULT, DailyGoal.sanitize(100_000))
    }

    @Test
    fun `the default is one of the choices`() {
        assertTrue(DailyGoal.DEFAULT in DailyGoal.CHOICES)
    }
}
