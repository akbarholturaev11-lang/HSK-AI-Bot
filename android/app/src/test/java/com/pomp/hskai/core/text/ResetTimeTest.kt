package com.pomp.hskai.core.text

import java.time.ZoneId
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class ResetTimeTest {

    private val tashkent = ZoneId.of("Asia/Tashkent")   // UTC+5
    private val moscow = ZoneId.of("Europe/Moscow")     // UTC+3

    @Test
    fun `the same instant reads as each learner's own clock`() {
        val iso = "2026-09-15T19:00:00+00:00"
        assertEquals("00:00", ResetTime.localClock(iso, tashkent))
        assertEquals("22:00", ResetTime.localClock(iso, moscow))
    }

    @Test
    fun `a Z suffix is accepted as well as an offset`() {
        assertEquals("05:00", ResetTime.localClock("2026-09-16T00:00:00Z", tashkent))
        assertEquals("05:00", ResetTime.localClock("2026-09-16T00:00:00+00:00", tashkent))
    }

    @Test
    fun `an offset other than UTC is honoured`() {
        // Whatever offset the server sends, only the instant matters:
        // 02:00+02:00 is midnight UTC, which is 05:00 in Tashkent.
        assertEquals("05:00", ResetTime.localClock("2026-09-16T02:00:00+02:00", tashkent))
        assertEquals("00:00", ResetTime.localClock("2026-09-15T17:00:00-02:00", tashkent))
    }

    @Test
    fun `nothing to show returns null instead of a made-up hour`() {
        assertNull(ResetTime.localClock(null, tashkent))
        assertNull(ResetTime.localClock("", tashkent))
        assertNull(ResetTime.localClock("   ", tashkent))
        assertNull(ResetTime.localClock("tomorrow", tashkent))
        assertNull(ResetTime.localClock("2026-09-16", tashkent))
        assertNull(ResetTime.localClock("00:00", tashkent))
    }

    @Test
    fun `midnight and noon are not confused`() {
        assertEquals("00:00", ResetTime.localClock("2026-09-16T00:00:00Z", ZoneId.of("UTC")))
        assertEquals("12:00", ResetTime.localClock("2026-09-16T12:00:00Z", ZoneId.of("UTC")))
        assertEquals("23:59", ResetTime.localClock("2026-09-16T23:59:00Z", ZoneId.of("UTC")))
    }
}
