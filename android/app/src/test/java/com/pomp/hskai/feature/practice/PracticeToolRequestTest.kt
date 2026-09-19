package com.pomp.hskai.feature.practice

import com.pomp.hskai.core.navigation.PracticeTool
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/**
 * A `pomp-hsk-ai://practice/<tool>` link used to reach `MainActivity`, switch to
 * Mashq and then drop the tool on the floor — Profile's own "Xatolarim" link
 * included. The mapping that fixes it is asserted here so a new tool cannot be
 * added without deciding where it opens.
 */
class PracticeToolRequestTest {

    @Test
    fun `each finished tool opens its own screen`() {
        assertEquals(PracticeRequest.MISTAKES, PracticeTool.MISTAKES.toRequest())
        assertEquals(PracticeRequest.RECOGNITION, PracticeTool.RECOGNITION.toRequest())
        assertEquals(PracticeRequest.PRONUNCIATION, PracticeTool.PRONUNCIATION.toRequest())
        assertEquals(PracticeRequest.TESTS, PracticeTool.TESTS.toRequest())
    }

    @Test
    fun `memorize has no android screen and stops on the section home`() {
        assertNull(PracticeTool.MEMORIZE.toRequest())
    }

    @Test
    fun `every request is reachable from some tool`() {
        val reached = PracticeTool.entries.mapNotNull { it.toRequest() }.toSet()
        assertEquals(PracticeRequest.entries.toSet(), reached)
    }
}
