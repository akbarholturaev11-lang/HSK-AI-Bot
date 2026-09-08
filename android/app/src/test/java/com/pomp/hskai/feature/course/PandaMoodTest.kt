package com.pomp.hskai.feature.course

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 阿宝 has to be one character in three states, not three drawings.
 *
 * There is little to assert about a Canvas from a JVM test, so what is pinned
 * here is the thing that actually regressed: the set of moods every caller
 * can ask for. A mood removed or renamed breaks the AI Voice screen and the
 * reward overlay silently, because both pass it by name.
 */
class PandaMoodTest {

    @Test
    fun `the character has exactly the three states the app asks for`() {
        assertEquals(
            listOf(PandaMood.Happy, PandaMood.Celebrate, PandaMood.Talk),
            PandaMood.entries.toList(),
        )
    }

    @Test
    fun `the resting state is the default`() {
        // Kurs yo'lakchasidagi panda hech qanday kayfiyat so'ramaydi.
        assertTrue(PandaMood.entries.first() == PandaMood.Happy)
    }
}
