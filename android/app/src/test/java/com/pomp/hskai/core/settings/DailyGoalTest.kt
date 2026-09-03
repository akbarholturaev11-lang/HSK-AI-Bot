package com.pomp.hskai.core.settings

import org.junit.Assert.assertEquals
import org.junit.Test

class DailyGoalTest {

    @Test
    fun `the offered choices are accepted`() {
        DailyGoal.CHOICES.forEach { choice ->
            assertEquals(choice, DailyGoal.sanitize(choice))
        }
    }

    /**
     * A stored value from an older build, a corrupted preference or a hand
     * edited datastore must not produce a goal the picker cannot show.
     */
    @Test
    fun `anything else falls back to the default`() {
        assertEquals(DailyGoal.DEFAULT, DailyGoal.sanitize(null))
        assertEquals(DailyGoal.DEFAULT, DailyGoal.sanitize(0))
        assertEquals(DailyGoal.DEFAULT, DailyGoal.sanitize(-30))
        assertEquals(DailyGoal.DEFAULT, DailyGoal.sanitize(35))
        assertEquals(DailyGoal.DEFAULT, DailyGoal.sanitize(100_000))
    }

    @Test
    fun `the default is one of the choices`() {
        assertEquals(true, DailyGoal.DEFAULT in DailyGoal.CHOICES)
    }
}
