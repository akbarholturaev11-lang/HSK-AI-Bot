package com.pomp.hskai.feature.lesson

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.compositeOver
import androidx.compose.ui.graphics.toPixelMap
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.unit.dp
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.domain.model.MatchPairsCard
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * `Juftlarni moslang` drew every cell the same way whatever was picked: `Tile`
 * was handed neither the selection nor the matched set, so tapping a hanzi
 * changed nothing on screen and there was no way to see what the next tap would
 * be matched against.
 *
 * The colours are read back off the rendered pixels rather than off the state,
 * because the point of the fix is that the state reaches the paint.
 */
@RunWith(AndroidJUnit4::class)
class MatchPairsSelectionTest {

    @get:Rule
    val compose = createComposeRule()

    private val card = MatchPairsCard(
        materialRef = "m1",
        pairs = listOf("颜色" to "rang", "左边" to "chap tomon"),
        explanation = "",
    )

    private fun render(onFinished: () -> Unit = {}) {
        compose.setContent {
            PompHskAiTheme {
                // A known ground, so a half-transparent cell composites predictably.
                Box(Modifier.fillMaxSize().background(PompColors.Paper).padding(8.dp)) {
                    MatchPairsCardView(card = card, isAnswered = false, onFinished = onFinished)
                }
            }
        }
    }

    /**
     * Reads a cell's fill.
     *
     * Sampled inside the left padding at mid height: the top edge is the 2dp
     * border and the middle is the glyph, so either would report a colour that
     * is not the fill.
     */
    private fun cellColor(text: String): Color {
        // A tap leaves a ripple; sampling mid-fade would read the ripple, not the fill.
        compose.mainClock.advanceTimeBy(1_500)
        compose.waitForIdle()
        val pixels = compose.onNodeWithText(text).captureToImage().toPixelMap()
        return pixels[(pixels.width * 0.08f).toInt(), pixels.height / 2]
    }

    private fun hex(c: Color): String {
        fun ch(v: Float) = "%02X".format((v * 255).toInt().coerceIn(0, 255))
        return "#" + ch(c.red) + ch(c.green) + ch(c.blue)
    }

    private fun assertSameColor(expected: Color, actual: Color, label: String) {
        val where = "$label: expected ${hex(expected)}, drew ${hex(actual)}"
        assertEquals(where, expected.red, actual.red, 0.03f)
        assertEquals(where, expected.green, actual.green, 0.03f)
        assertEquals(where, expected.blue, actual.blue, 0.03f)
    }

    /**
     * Names which of the three fills a cell is wearing: neutral, red or green.
     *
     * A tapped cell keeps Material's focus state layer, which darkens whatever
     * is under it by a few percent — so the pixel is never the bare token and
     * comparing it to one is a losing game. What a learner actually reads off
     * the screen is the tint, and a tint survives a uniform darkening: the idle
     * fill is neutral, `.sel` leans red, `.ok` leans green. That the tints
     * themselves are the Mini App's exact hex values is asserted separately, in
     * `MiniAppPaletteTest`.
     */
    private fun fillOf(text: String): String {
        val c = cellColor(text)
        val spread = maxOf(c.red, c.green, c.blue) - minOf(c.red, c.green, c.blue)
        return when {
            spread < 0.02f -> "idle"
            c.green > c.red && c.green > c.blue -> "matched"
            c.red > c.green && c.red > c.blue -> "selected"
            else -> "unrecognised ${hex(c)}"
        }
    }

    /** Nothing tapped, nothing focused: this one can be held to the exact hex. */
    @Test
    fun an_untouched_cell_sits_on_the_plain_card_colour() {
        render()
        assertSameColor(PompColors.PaperRaised, cellColor("颜色"), "idle")
    }

    @Test
    fun tapping_a_hanzi_turns_that_cell_cinnabar() {
        render()

        compose.onNodeWithText("颜色").performClick()

        // `.pcell.sel{background:var(--cinbg)}`
        assertEquals("selected", fillOf("颜色"))
        // Only the picked cell changes; its neighbour stays as it was.
        assertEquals("idle", fillOf("左边"))
    }

    @Test
    fun a_solved_pair_turns_jade_on_both_sides() {
        render()

        compose.onNodeWithText("颜色").performClick()
        compose.onNodeWithText("rang").performClick()

        // `.pcell.ok{background:var(--jadebg)}` on both halves of the pair.
        assertEquals("matched", fillOf("颜色"))
        assertEquals("matched", fillOf("rang"))
    }

    @Test
    fun a_wrong_pick_clears_the_selection_instead_of_leaving_it_lit() {
        render()

        compose.onNodeWithText("颜色").performClick()
        compose.onNodeWithText("chap tomon").performClick()

        assertEquals("idle", fillOf("颜色"))
        assertEquals("idle", fillOf("chap tomon"))
    }

    /**
     * A miss is a nudge, as in the Mini App's `cardMatch`: the grid still
     * finishes once every pair is matched. It used to hand the miss on, and
     * the lesson then failed a fully matched grid.
     */
    @Test
    fun a_missed_pick_does_not_stop_the_grid_finishing() {
        var finished = 0
        render(onFinished = { finished++ })

        compose.onNodeWithText("颜色").performClick()
        compose.onNodeWithText("chap tomon").performClick()
        compose.onNodeWithText("颜色").performClick()
        compose.onNodeWithText("rang").performClick()
        compose.onNodeWithText("左边").performClick()
        compose.onNodeWithText("chap tomon").performClick()
        compose.waitForIdle()

        assertEquals(1, finished)
    }

    @Test
    fun a_right_cell_tapped_first_matches_nothing() {
        render()

        compose.onNodeWithText("rang").performClick()

        // `window._mR` bails while `selL === null`; nothing may turn jade.
        assertEquals("idle", fillOf("rang"))
        assertEquals("idle", fillOf("颜色"))
    }
}
