package com.pomp.hskai.feature.foundation

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class FoundationVisualRulesTest {
    @Test
    fun listeningAnswerIsHiddenUntilCorrect() {
        assertFalse(foundationShowExample("listen_choice", null))
        assertFalse(foundationShowExample("listen_choice", false))
        assertTrue(foundationShowExample("listen_choice", true))
    }

    @Test
    fun regularCardsKeepTheirExample() {
        assertTrue(foundationShowExample("choice", null))
        assertTrue(foundationShowExample("speak", null))
        assertTrue(foundationShowExample("explain", null))
    }
}
