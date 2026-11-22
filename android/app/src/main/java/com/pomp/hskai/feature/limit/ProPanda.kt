package com.pomp.hskai.feature.limit

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.unit.dp
import com.pomp.hskai.core.design.ProColors
import com.pomp.hskai.core.design.components.hskMotionOff
import com.pomp.hskai.feature.course.CoursePandaMascot
import com.pomp.hskai.feature.course.PandaMood
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin

/**
 * The course panda (阿宝, [CoursePandaMascot]) dressed for Pro and Trial
 * screens: a soft gold halo behind it and, once, a gold spark burst.
 *
 * No new character: the drawing, moods and idle motion are the existing
 * panda's. Decorative only (no semantics, no text, no access logic). With the
 * system "remove animations" switch the halo is static and no burst plays.
 * Not wired anywhere yet: see docs/design/LAUNCH_MARK_AND_PRO_PANDA.md.
 */
@Composable
fun ProPanda(
    modifier: Modifier = Modifier,
    celebrate: Boolean = false,
    burst: Boolean = celebrate,
) {
    val context = LocalContext.current
    val motionOff = remember { hskMotionOff(context) }
    val halo = if (motionOff) 1f else rememberInfiniteTransition(label = "pro-halo").animateFloat(
        initialValue = 0.96f,
        targetValue = 1.04f,
        animationSpec = infiniteRepeatable(tween(3200), RepeatMode.Reverse),
        label = "pro-halo-scale",
    ).value
    val sparks = remember { Animatable(0f) }
    LaunchedEffect(burst, motionOff) {
        if (burst && !motionOff) {
            sparks.snapTo(0f)
            sparks.animateTo(1f, tween(PRO_SPARK_MS, easing = SparkEase))
        }
    }
    Box(modifier.clearAndSetSemantics {}, contentAlignment = Alignment.Center) {
        Canvas(Modifier.fillMaxSize()) {
            val r = size.minDimension * 0.47f * halo
            drawCircle(
                Brush.radialGradient(
                    0f to ProColors.Halo,
                    0.62f to ProColors.Halo.copy(alpha = 0.10f),
                    1f to Color.Transparent,
                    center = center,
                    radius = r,
                ),
                radius = r,
            )
        }
        CoursePandaMascot(
            modifier = Modifier.fillMaxSize().padding(8.dp),
            mood = if (celebrate) PandaMood.Celebrate else PandaMood.Happy,
        )
        val p = sparks.value
        if (p > 0f && p < 1f) {
            Canvas(Modifier.fillMaxSize()) {
                val origin = Offset(size.width / 2f, size.height * 0.56f)
                val alpha = proSparkAlpha(p)
                proSparkOffsets(PRO_SPARK_COUNT, p, size.minDimension * 0.30f).forEachIndexed { i, o ->
                    val c = origin + o
                    val s = (if (i % 2 == 0) 5f else 4f).dp.toPx() * (0.4f + 0.6f * p)
                    rotate(45f, pivot = c) {
                        drawPath(sparkDiamond(c, s), ProColors.Gold, alpha = alpha)
                    }
                }
            }
        }
    }
}

internal const val PRO_SPARK_COUNT = 8
internal const val PRO_SPARK_MS = 800
private val SparkEase = CubicBezierEasing(0.2f, 0.8f, 0.3f, 1f)

/**
 * Where each spark is at [progress] (0..1): evenly spread around the panda's
 * chest, alternating long and short rays, offset half a step so no spark
 * flies straight up through the face. Same geometry as the PWA burst.
 */
internal fun proSparkOffsets(count: Int, progress: Float, radius: Float): List<Offset> {
    val p = progress.coerceIn(0f, 1f)
    return List(count) { i ->
        val angle = (i + 0.5) * 2.0 * PI / count
        val reach = radius * (if (i % 2 == 0) 1f else 0.77f) * p
        Offset((sin(angle) * reach).toFloat(), (-cos(angle) * reach).toFloat())
    }
}

/** Fade in over the first quarter, then out to zero at the end. */
internal fun proSparkAlpha(progress: Float): Float {
    val p = progress.coerceIn(0f, 1f)
    return if (p < 0.25f) p / 0.25f else 1f - (p - 0.25f) / 0.75f
}

private fun sparkDiamond(c: Offset, s: Float) = Path().apply {
    moveTo(c.x, c.y - s); lineTo(c.x + s * 0.3f, c.y - s * 0.3f)
    lineTo(c.x + s, c.y); lineTo(c.x + s * 0.3f, c.y + s * 0.3f)
    lineTo(c.x, c.y + s); lineTo(c.x - s * 0.3f, c.y + s * 0.3f)
    lineTo(c.x - s, c.y); lineTo(c.x - s * 0.3f, c.y - s * 0.3f)
    close()
}
