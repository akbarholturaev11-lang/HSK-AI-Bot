package com.pomp.hskai.core.design.components

import androidx.compose.foundation.layout.Spacer
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawWithCache
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import com.pomp.hskai.core.design.PompColors

/**
 * A faded ink-wash landscape (山水, shānshuǐ) behind a learning screen: misty
 * hills, a pagoda, a pine on the cliff and a boat at the bottom, a low sun and
 * three birds at the top.
 *
 * It is vector, not a picture: nothing is added to the APK, it has no
 * copyright of its own, and dark mode repaints it in the theme's ink instead of
 * showing a light image on Cosmos Blue. The colours are palette tokens only,
 * so the Mini App palette check stays exact.
 *
 * The scene is drawn once per size ([drawWithCache]) and never animates — it
 * sits under every card of a lesson and must cost nothing while scrolling.
 *
 * Coordinates are the 390×844 design the approved mockup was drawn on. The
 * hills are anchored to the bottom edge and the sky to the top, both scaled by
 * width, so a taller phone gets more empty paper in the middle rather than a
 * stretched mountain.
 */
@Composable
fun HskSceneBackground(modifier: Modifier = Modifier) {
    val dark = PompColors.IsDark
    val ink = PompColors.Ink
    val sun = if (dark) PompColors.Gold else PompColors.Cinnabar
    Spacer(
        modifier.drawWithCache {
            val scene = InkLandscape(size, ink, sun, if (dark) DARK_STRENGTH else 1f)
            onDrawBehind { scene.draw(this) }
        },
    )
}

/** Light ink on Cosmos Blue reads stronger than dark ink on paper. */
private const val DARK_STRENGTH = 0.85f
private const val DESIGN_WIDTH = 390f
private const val DESIGN_HEIGHT = 844f

private class InkLandscape(size: Size, private val ink: Color, private val sun: Color, private val k: Float) {
    private val s = size.width / DESIGN_WIDTH
    private val bottom = size.height

    private fun x(v: Float) = v * s
    private fun top(v: Float) = v * s
    private fun low(v: Float) = bottom - (DESIGN_HEIGHT - v) * s

    private fun Path.m(px: Float, py: Float) = moveTo(x(px), low(py))
    private fun Path.l(px: Float, py: Float) = lineTo(x(px), low(py))
    private fun Path.q(x1: Float, y1: Float, x2: Float, y2: Float) =
        quadraticTo(x(x1), low(y1), x(x2), low(y2))
    private fun Path.c(x1: Float, y1: Float, x2: Float, y2: Float, x3: Float, y3: Float) =
        cubicTo(x(x1), low(y1), x(x2), low(y2), x(x3), low(y3))
    private fun Path.rect(left: Float, topY: Float, width: Float, height: Float) =
        addRect(Rect(x(left), low(topY), x(left + width), low(topY + height)))
    private fun Path.oval(cx: Float, cy: Float, rx: Float, ry: Float) =
        addOval(Rect(x(cx - rx), low(cy - ry), x(cx + rx), low(cy + ry)))

    private fun Path.closeToBottom() {
        l(DESIGN_WIDTH, DESIGN_HEIGHT)
        l(0f, DESIGN_HEIGHT)
        close()
    }

    /** Mist: full ink at the ridge, gone by the foot of the hill. */
    private fun mist(alpha: Float, ridge: Float) = Brush.verticalGradient(
        0f to ink.copy(alpha = alpha * k),
        0.6f to ink.copy(alpha = alpha * k * 0.35f),
        1f to ink.copy(alpha = 0f),
        startY = low(ridge),
        endY = bottom,
    )

    private val birds = Path().apply {
        fun bird(startX: Float, y: Float, span: Float, lift: Float) {
            moveTo(x(startX), top(y))
            quadraticTo(x(startX + span / 2), top(y - lift), x(startX + span), top(y))
            quadraticTo(x(startX + span * 1.5f), top(y - lift), x(startX + span * 2), top(y))
        }
        bird(52f, 176f, 10f, 5f)
        bird(82f, 160f, 8f, 4f)
        bird(72f, 200f, 7f, 3.5f)
    }

    private val farHills = Path().apply {
        m(0f, 720f)
        c(28f, 700f, 52f, 668f, 84f, 676f)
        c(108f, 682f, 124f, 642f, 154f, 636f)
        c(178f, 631f, 194f, 668f, 218f, 674f)
        c(244f, 680f, 266f, 628f, 302f, 618f)
        c(330f, 610f, 348f, 654f, 372f, 660f)
        c(380f, 662f, 386f, 658f, 390f, 656f)
        closeToBottom()
    }

    private val midHills = Path().apply {
        m(0f, 780f)
        c(24f, 758f, 42f, 728f, 72f, 720f)
        c(96f, 714f, 112f, 748f, 140f, 752f)
        c(160f, 755f, 176f, 722f, 206f, 704f)
        c(226f, 692f, 242f, 698f, 254f, 710f)
        c(270f, 728f, 292f, 748f, 322f, 745f)
        c(350f, 742f, 366f, 724f, 390f, 716f)
        closeToBottom()
    }

    private val nearCliff = Path().apply {
        m(0f, 690f)
        c(16f, 692f, 28f, 708f, 40f, 736f)
        c(50f, 760f, 60f, 790f, 92f, 810f)
        c(122f, 828f, 172f, 832f, 232f, 833f)
        c(300f, 834f, 350f, 826f, 390f, 820f)
        closeToBottom()
    }

    /** One path, so the overlapping tiers are filled once and stay one shade. */
    private val pagoda = Path().apply {
        rect(201f, 692f, 10f, 12f)
        m(193f, 693f); q(200f, 691f, 206f, 686f); q(212f, 691f, 219f, 693f); l(215f, 695f); l(197f, 695f); close()
        rect(202f, 680f, 8f, 8f)
        m(195f, 681f); q(201f, 679f, 206f, 674f); q(211f, 679f, 217f, 681f); l(213f, 683f); l(199f, 683f); close()
        rect(203f, 669f, 6f, 7f)
        m(197f, 670f); q(202f, 668f, 206f, 664f); q(210f, 668f, 215f, 670f); l(212f, 672f); l(200f, 672f); close()
        rect(205.4f, 656f, 1.2f, 9f)
    }

    private val boat = Path().apply {
        m(270f, 800f); q(292f, 808f, 316f, 800f); l(311f, 805f); q(292f, 811f, 275f, 805f); close()
        rect(288f, 789f, 2.2f, 11f)
        m(283f, 790f); l(289f, 784f); l(295f, 790f); close()
    }

    private val fishingRod = Path().apply { m(291f, 792f); l(322f, 774f) }

    private val pineTrunk = Path().apply {
        m(12f, 702f); c(16f, 684f, 22f, 672f, 34f, 662f); c(42f, 656f, 50f, 654f, 60f, 652f)
        m(30f, 666f); c(26f, 654f, 28f, 646f, 22f, 638f)
    }

    private val pineNeedles = Path().apply {
        oval(62f, 650f, 20f, 5f)
        oval(44f, 660f, 16f, 4.5f)
        oval(24f, 636f, 14f, 4.5f)
        oval(72f, 642f, 11f, 3.6f)
        oval(38f, 644f, 10f, 3.4f)
    }

    private val ripples = Path().apply {
        listOf(236f to 22f, 272f to 30f, 318f to 18f, 252f to 16f, 300f to 26f)
            .zip(listOf(814f, 820f, 812f, 830f, 834f))
            .forEach { (line, y) -> m(line.first, y); l(line.first + line.second, y) }
    }

    private val farMist = mist(0.06f, 610f)
    private val midMist = mist(0.10f, 692f)
    private val nearMist = mist(0.15f, 690f)

    fun draw(scope: DrawScope) = with(scope) {
        drawCircle(sun.copy(alpha = 0.07f * k), radius = x(40f), center = Offset(x(318f), top(190f)))
        drawPath(birds, ink.copy(alpha = 0.17f * k), style = Stroke(width = x(1.6f), cap = StrokeCap.Round))
        drawPath(farHills, farMist)
        drawPath(midHills, midMist)
        drawPath(pagoda, ink.copy(alpha = 0.15f * k))
        drawPath(boat, ink.copy(alpha = 0.2f * k))
        drawPath(fishingRod, ink.copy(alpha = 0.2f * k), style = Stroke(width = x(0.9f)))
        drawPath(nearCliff, nearMist)
        drawPath(pineTrunk, ink.copy(alpha = 0.18f * k), style = Stroke(width = x(3.2f), cap = StrokeCap.Round))
        drawPath(pineNeedles, ink.copy(alpha = 0.18f * k))
        drawPath(ripples, ink.copy(alpha = 0.15f * k), style = Stroke(width = x(1.2f), cap = StrokeCap.Round))
    }
}
