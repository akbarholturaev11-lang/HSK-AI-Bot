package com.pomp.hskai.core.design.components

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.tween
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.composed
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.draw.drawWithContent
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.platform.LocalContext
import com.pomp.hskai.core.design.ProColors

/**
 * One gold light sweep across a Pro card or badge, played once per [key]
 * (PWA twin: `HSKProPanda.glint(el)`). Decorative; skipped entirely when the
 * system "remove animations" switch is on.
 */
fun Modifier.hskProGlint(key: Any? = Unit): Modifier = composed {
    val context = LocalContext.current
    val motionOff = remember { hskMotionOff(context) }
    val sweep = remember { Animatable(0f) }
    LaunchedEffect(key, motionOff) {
        if (!motionOff) {
            sweep.snapTo(0f)
            sweep.animateTo(1f, tween(PRO_GLINT_MS, easing = CubicBezierEasing(0.3f, 0.7f, 0.3f, 1f)))
        }
    }
    clipToBounds().drawWithContent {
        drawContent()
        val p = sweep.value
        if (p > 0f && p < 1f) {
            val band = size.width * 0.45f
            val x = proGlintX(p, size.width, band)
            rotate(18f, pivot = Offset(x + band / 2f, size.height / 2f)) {
                drawRect(
                    Brush.horizontalGradient(listOf(Color.Transparent, ProColors.Glint, Color.Transparent), x, x + band),
                    topLeft = Offset(x, -size.height * 0.2f),
                    size = Size(band, size.height * 1.4f),
                )
            }
        }
    }
}

internal const val PRO_GLINT_MS = 1000

/** Left edge of the glint band: from fully left of the card to fully right of it. */
internal fun proGlintX(progress: Float, width: Float, band: Float): Float {
    val p = progress.coerceIn(0f, 1f)
    return -band + (width + band * 2f) * p
}
