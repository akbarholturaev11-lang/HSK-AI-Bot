package com.pomp.hskai.feature.practice

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PracticeSectionNewBadgeTest {
    @Test
    fun `new badge is visible only during the first 72 hours after release`() {
        val releasedAt = 1_791_821_284_000L
        val expiresAt = releasedAt + 72L * 60 * 60 * 1000

        assertFalse(isPracticeSectionNew(releasedAt, releasedAt - 1))
        assertTrue(isPracticeSectionNew(releasedAt, releasedAt))
        assertTrue(isPracticeSectionNew(releasedAt, expiresAt - 1))
        assertFalse(isPracticeSectionNew(releasedAt, expiresAt))
    }
}
