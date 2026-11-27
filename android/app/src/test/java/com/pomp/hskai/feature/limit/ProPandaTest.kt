package com.pomp.hskai.feature.limit

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.abs
import kotlin.math.hypot

/** The Pro spark burst: eight sparks, spread evenly, played once and gone. */
class ProPandaTest {

    @Test
    fun sparks_start_on_the_panda_and_spread_evenly() {
        val start = proSparkOffsets(PRO_SPARK_COUNT, 0f, 100f)
        assertEquals(PRO_SPARK_COUNT, start.size)
        assertTrue(start.all { it.x == 0f && it.y == 0f })
        val end = proSparkOffsets(PRO_SPARK_COUNT, 1f, 100f)
        end.forEachIndexed { i, o ->
            val expected = if (i % 2 == 0) 100f else 77f
            assertEquals(expected, hypot(o.x, o.y), 0.01f)
        }
    }

    @Test
    fun no_spark_flies_straight_up_through_the_face() {
        proSparkOffsets(PRO_SPARK_COUNT, 1f, 100f).forEach { o ->
            assertTrue("spark at $o", !(abs(o.x) < 1f && o.y < 0f))
        }
    }

    @Test
    fun the_burst_fades_in_then_out_to_nothing() {
        assertEquals(0f, proSparkAlpha(0f), 0f)
        assertEquals(1f, proSparkAlpha(0.25f), 1e-4f)
        assertEquals(0f, proSparkAlpha(1f), 1e-4f)
        assertTrue(PRO_SPARK_MS in 500..1000)
    }
}
