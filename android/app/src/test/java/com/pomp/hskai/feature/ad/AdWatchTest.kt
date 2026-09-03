package com.pomp.hskai.feature.ad

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AdWatchTest {

    @Test
    fun `the attempt duration wins because the server checks against it`() {
        assertEquals(9, AdWatch.requiredSeconds(fromAttempt = 9, fromCreative = 30))
    }

    @Test
    fun `the listing duration is the fallback when the attempt said nothing`() {
        assertEquals(30, AdWatch.requiredSeconds(fromAttempt = 0, fromCreative = 30))
    }

    @Test
    fun `with nothing to go on the shared default is used`() {
        assertEquals(AdWatch.DEFAULT_SECONDS, AdWatch.requiredSeconds(0, 0))
        assertEquals(AdWatch.DEFAULT_SECONDS, AdWatch.requiredSeconds(-4, -9))
    }

    @Test
    fun `an absurd duration is clamped to the same bounds as the server`() {
        // Below the server's minimum the learner could press continue on a
        // view the server would then refuse to count.
        assertEquals(AdWatch.MIN_SECONDS, AdWatch.requiredSeconds(1))
        assertEquals(AdWatch.MAX_SECONDS, AdWatch.requiredSeconds(9_999))
    }

    @Test
    fun `continue only unlocks once the time has actually passed`() {
        assertFalse(AdWatch.canContinue(0, 7))
        assertFalse(AdWatch.canContinue(6, 7))
        assertTrue(AdWatch.canContinue(7, 7))
        assertTrue(AdWatch.canContinue(8, 7))
    }

    @Test
    fun `a broken duration never traps the learner in the ad`() {
        // Nothing to wait for is not the same as waiting forever.
        assertFalse(AdWatch.canContinue(3, 0))
        assertEquals(0, AdWatch.remainingSeconds(3, 0))
        assertEquals(1f, AdWatch.progress(0, 0), 0.0001f)
    }

    @Test
    fun `the countdown never goes negative`() {
        assertEquals(7, AdWatch.remainingSeconds(0, 7))
        assertEquals(1, AdWatch.remainingSeconds(6, 7))
        assertEquals(0, AdWatch.remainingSeconds(7, 7))
        assertEquals(0, AdWatch.remainingSeconds(99, 7))
    }

    @Test
    fun `progress stays inside the ring`() {
        assertEquals(0f, AdWatch.progress(0, 10), 0.0001f)
        assertEquals(0.5f, AdWatch.progress(5, 10), 0.0001f)
        assertEquals(1f, AdWatch.progress(10, 10), 0.0001f)
        assertEquals(1f, AdWatch.progress(40, 10), 0.0001f)
        assertEquals(0f, AdWatch.progress(-3, 10), 0.0001f)
    }
}
