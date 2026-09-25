package com.pomp.hskai.core.design.components

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The lesson-end clip is a port of the Mini App's, so two things have to
 * hold: keyframes are read the way CSS reads them, and the vibration pulses
 * land on the tones they accompany.
 */
class HskCelebrationFxTest {

    private val track = arrayOf(
        HskKey(0f, 0f),
        HskKey(.5f, 10f, HskEaseInOut),
        HskKey(1f, 4f),
    )

    @Test
    fun a_track_hits_every_keyframe_exactly() {
        assertEquals(0f, hskTrack(track, 0f), 0f)
        assertEquals(10f, hskTrack(track, .5f), 0f)
        assertEquals(4f, hskTrack(track, 1f), 0f)
    }

    @Test
    fun a_track_holds_its_ends_outside_the_run() {
        assertEquals(0f, hskTrack(track, -1f), 0f)
        assertEquals(4f, hskTrack(track, 2f), 0f)
    }

    @Test
    fun each_keyframe_eases_only_the_segment_it_starts() {
        // The first segment is linear: halfway there is exactly halfway.
        assertEquals(5f, hskTrack(track, .25f), 1e-4f)
        // The second is ease-in-out, which is symmetric about its middle.
        assertEquals(7f, hskTrack(track, .75f), 1e-3f)
        // ...and slow at its start, so just after the keyframe it has barely moved.
        assertTrue(hskTrack(track, .55f) > 9.8f)
    }

    @Test
    fun every_vibration_pulse_starts_with_its_note() {
        HskCue.entries.filter { it.notes.isNotEmpty() }.forEach { cue ->
            assertEquals(cue.name, cue.timings.size, cue.amplitudes.size)
            var at = 0L
            val onsets = mutableListOf<Long>()
            cue.timings.forEachIndexed { index, length ->
                if (index % 2 == 1) onsets += at
                at += length
            }
            // `beep()` starts a note every 90 ms; the phone pulses with each.
            assertEquals(cue.name, cue.notes.indices.map { it * 90L }, onsets)
            assertTrue(cue.name, cue.amplitudes.all { it in 0..255 })
        }
    }
}
