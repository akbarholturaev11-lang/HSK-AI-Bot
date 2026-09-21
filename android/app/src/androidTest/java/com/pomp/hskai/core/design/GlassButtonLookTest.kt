package com.pomp.hskai.core.design

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.unit.dp
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.pomp.hskai.core.design.components.HskGlassButton
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import kotlin.math.abs

/**
 * The glass button must be one flat surface.
 *
 * It used to be painted translucent WITH an elevation shadow, which let its
 * own shadow through: the shadow's inner edge landed as a hard white band
 * straight across the button, under the label. The colour is now composited
 * onto the page up front, so the fill is opaque and nothing shows through.
 *
 * This walks a column of pixels down the middle of the button, away from the
 * text, and fails on any sudden jump in brightness — which is exactly what a
 * band is and what a smooth surface never has.
 */
@RunWith(AndroidJUnit4::class)
class GlassButtonLookTest {

    @get:Rule
    val compose = createComposeRule()

    @Test
    fun theButtonSurfaceHasNoBandAcrossIt() {
        compose.setContent {
            PompHskAiTheme {
                Box(
                    Modifier.fillMaxSize().background(PompColors.Paper),
                    contentAlignment = Alignment.Center,
                ) {
                    HskGlassButton(
                        text = "Yopish",
                        onClick = {},
                        modifier = Modifier.fillMaxWidth().padding(horizontal = 24.dp),
                    )
                }
            }
        }
        compose.waitForIdle()

        val bounds = compose.onNodeWithText("Yopish").fetchSemanticsNode().boundsInRoot
        val bitmap = compose.onRoot().captureToImage().asAndroidBitmap()

        // A column well inside the button and clear of the glyphs: the label
        // is centred, so a tenth in from the left edge is blank surface.
        val x = (bounds.left + bounds.width * 0.1f).toInt()
        val top = (bounds.top + 6).toInt()
        val bottom = (bounds.bottom - 6).toInt()
        assertTrue("the button must be measurable", bottom - top > 8 && x > 0)

        fun luma(px: Int): Int {
            val r = (px shr 16) and 0xFF
            val g = (px shr 8) and 0xFF
            val b = px and 0xFF
            return (r * 299 + g * 587 + b * 114) / 1000
        }

        var worst = 0
        var worstY = top
        for (y in top until bottom) {
            val step = abs(luma(bitmap.getPixel(x, y + 1)) - luma(bitmap.getPixel(x, y)))
            if (step > worst) { worst = step; worstY = y }
        }

        // A band shows up as a double-digit jump between neighbouring rows;
        // the soft gradient of a real surface moves a point or two at a time.
        assertTrue(
            "brightness jumps by $worst at y=$worstY — the surface has a band across it",
            worst <= 6,
        )
    }
}
