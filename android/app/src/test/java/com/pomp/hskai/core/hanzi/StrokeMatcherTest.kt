package com.pomp.hskai.core.hanzi

import androidx.compose.ui.geometry.Offset
import java.io.File
import kotlin.math.sin
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.float
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Real strokes from the bundled data, written by a slightly shaky finger. */
class StrokeMatcherTest {

    private val hao = bundledMedians('好')

    @Test
    fun `each stroke written in order is accepted`() {
        hao.forEachIndexed { index, median ->
            val drawn = finger(median, seed = index)
            assertTrue("stroke $index with outline", StrokeMatcher.match(drawn, hao, index, outlineVisible = true).isMatch)
            assertTrue("stroke $index from memory", StrokeMatcher.match(drawn, hao, index, outlineVisible = false).isMatch)
        }
    }

    @Test
    fun `a stroke written from the wrong end is refused and named as such`() {
        val drawn = finger(hao[0], seed = 3).asReversed()

        val result = StrokeMatcher.match(drawn, hao, 0, outlineVisible = true)

        assertFalse(result.isMatch)
        assertTrue(result.isBackwards)
    }

    @Test
    fun `a later stroke written early is refused`() {
        // 好's last stroke is the long horizontal of 子; the first is the
        // opening stroke of 女. Nothing about one passes for the other.
        val drawn = finger(hao.last(), seed = 5)

        assertFalse(StrokeMatcher.match(drawn, hao, 0, outlineVisible = true).isMatch)
    }

    @Test
    fun `the right shape in the wrong place is refused`() {
        val drawn = finger(hao[0], seed = 7).map { it + Offset(420f, 0f) }

        assertFalse(StrokeMatcher.match(drawn, hao, 0, outlineVisible = true).isMatch)
    }

    @Test
    fun `a tap is not a stroke`() {
        val tap = listOf(hao[0].first(), hao[0].first())

        assertFalse(StrokeMatcher.match(tap, hao, 0, outlineVisible = true).isMatch)
    }

    @Test
    fun `a stroke index past the character matches nothing`() {
        assertFalse(StrokeMatcher.match(finger(hao[0], 1), hao, hao.size, outlineVisible = true).isMatch)
    }

    @Test
    fun `grid and canvas coordinates round trip`() {
        val point = Offset(512f, -60f)
        val side = 900f

        val back = HanziGrid.toGrid(HanziGrid.toCanvas(point, side), side)

        assertEquals(point.x, back.x, 0.01f)
        assertEquals(point.y, back.y, 0.01f)
        // The top edge of the data (y = 900) is the top of the canvas.
        assertEquals(0f, HanziGrid.toCanvas(Offset(0f, 900f), side).y, 0.01f)
        assertEquals(side, HanziGrid.toCanvas(Offset(0f, -124f), side).y, 0.01f)
    }

    companion object {
        /** Evenly resampled along the stroke with a small, repeatable wobble. */
        fun finger(median: List<Offset>, seed: Int, samples: Int = 24): List<Offset> {
            val lengths = median.zipWithNext { a, b -> (b - a).getDistance() }
            val total = lengths.sum()
            return (0 until samples).map { i ->
                var target = total * i / (samples - 1)
                var segment = 0
                while (segment < lengths.lastIndex && target > lengths[segment]) {
                    target -= lengths[segment]
                    segment++
                }
                val a = median[segment]
                val b = median[segment + 1]
                val t = if (lengths[segment] == 0f) 0f else (target / lengths[segment]).coerceIn(0f, 1f)
                val wobble = 12f * sin((i + seed) * 1.7f)
                Offset(a.x + (b.x - a.x) * t + wobble, a.y + (b.y - a.y) * t - wobble)
            }
        }

        fun bundledMedians(char: Char): List<List<Offset>> {
            val raw = File("src/main/assets/strokes/${char.code}.json").readText()
            val medians = Json.parseToJsonElement(raw).jsonObject.getValue("medians").jsonArray
            return medians.map { stroke ->
                stroke.jsonArray.map { point ->
                    val xy = point.jsonArray
                    Offset(xy[0].jsonPrimitive.float, xy[1].jsonPrimitive.float)
                }
            }
        }
    }
}
