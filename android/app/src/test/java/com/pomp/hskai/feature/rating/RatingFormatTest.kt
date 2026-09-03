package com.pomp.hskai.feature.rating

import org.junit.Assert.assertEquals
import org.junit.Test

class RatingFormatTest {

    @Test
    fun `each server league maps to its own badge`() {
        assertEquals("玄", leagueGlyph("Bronze"))
        assertEquals("朱", leagueGlyph("silver"))
        assertEquals("龙", leagueGlyph("GOLD"))
        assertEquals("凤", leagueGlyph("Sapphire"))
    }

    /**
     * A league the client does not know about must not be silently drawn as
     * another league: the learner would read a standing they do not have.
     */
    @Test
    fun `an unknown league is shown as sent`() {
        assertEquals("Diamond", leagueGlyph("Diamond"))
    }

    @Test
    fun `a missing league falls back to the first step`() {
        assertEquals("玄", leagueGlyph(""))
    }

    @Test
    fun `countdown reads in the largest useful unit`() {
        assertEquals("3d 8h", countdownText(3 * 86_400 + 8 * 3_600 + 42))
        assertEquals("5h 30m", countdownText(5 * 3_600 + 30 * 60))
        assertEquals("12m", countdownText(12 * 60 + 59))
        assertEquals("0m", countdownText(0))
    }

    /** A clock skew must not render a negative countdown. */
    @Test
    fun `a negative countdown is clamped`() {
        assertEquals("0m", countdownText(-500))
    }
}
