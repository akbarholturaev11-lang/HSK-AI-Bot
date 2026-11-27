package com.pomp.hskai.core.design.components

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The Knot Thread launch mark is one deterministic clock shared with the PWA
 * (`HSKLaunchMark.TIMELINE`). What can regress is the order of its beats and
 * its end state; the PWA/Android numbers are also pinned by
 * tests/test_launch_mark_pro_panda_contract.py.
 */
class HskLaunchMarkTest {

    @Test
    fun every_beat_starts_at_zero_and_ends_complete() {
        val t = LaunchMarkTimeline
        assertEquals(0f, t.seal(0f), 0f)
        assertEquals(0f, t.strandA(t.STRAND_A_START), 0f)
        assertEquals(0f, t.strandB(t.STRAND_B_START), 0f)
        assertEquals(0f, t.word(t.WORD_START), 0f)
        for (beat in listOf(t::seal, t::strandA, t::strandB, t::weave, t::word)) {
            assertEquals(1f, beat(t.TOTAL_MS), 0f)
        }
    }

    @Test
    fun the_knot_is_drawn_before_it_weaves_and_shines() {
        val t = LaunchMarkTimeline
        assertTrue(t.STRAND_A_START < t.STRAND_B_START)
        assertTrue(t.STRAND_B_START + t.STRAND_MS <= t.WEAVE_START + t.WEAVE_MS)
        assertTrue(t.WEAVE_START + t.WEAVE_MS <= t.GLINT_START)
        assertTrue(t.WORD_START + t.WORD_MS <= t.TOTAL_MS)
        assertTrue(t.GLINT_START + t.GLINT_MS <= t.TOTAL_MS)
        // Snappy: the whole mark is well under the old 2.9 s Golden Logo.
        assertTrue(t.TOTAL_MS <= 1200f)
    }

    @Test
    fun the_glint_crosses_once_and_is_gone_on_the_final_frame() {
        val t = LaunchMarkTimeline
        assertNull(t.glint(t.GLINT_START))
        assertEquals(0.5f, t.glint(t.GLINT_START + t.GLINT_MS / 2f)!!, 1e-4f)
        assertNull(t.glint(t.TOTAL_MS))
    }

    @Test
    fun the_pro_glint_band_enters_from_the_left_and_leaves_on_the_right() {
        assertEquals(-40f, proGlintX(0f, 200f, 40f), 0f)
        assertEquals(240f, proGlintX(1f, 200f, 40f), 0f)
        assertEquals(240f, proGlintX(2f, 200f, 40f), 0f)
    }
}
