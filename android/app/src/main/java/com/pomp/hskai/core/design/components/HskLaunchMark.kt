package com.pomp.hskai.core.design.components

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.RoundRect
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathMeasure
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.clipPath
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.graphics.drawscope.scale
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.ProColors

/**
 * "Knot Thread" — candidate minimalist launch mark (owner request 2026-11-22).
 *
 * The two gold strands of the real HSK AI knot are drawn as one thread, weave
 * at the crossings, one gold glint crosses the seal and the wordmark settles.
 * Same timeline as the PWA `/assets/brand/hsk-launch-mark.js`.
 *
 * Standalone and NOT wired: [HskBrandLoader] with its sound/haptic Golden Logo
 * stays the shipped splash until the owner approves a swap. With the system
 * "remove animations" switch the finished mark is shown and [onFinished] runs
 * at once. Integration: docs/design/LAUNCH_MARK_AND_PRO_PANDA.md.
 */
@Composable
fun HskLaunchMark(
    modifier: Modifier = Modifier,
    onFinished: () -> Unit = {},
) {
    val context = LocalContext.current
    val motionOff = remember { hskMotionOff(context) }
    val clock = remember { Animatable(if (motionOff) LaunchMarkTimeline.TOTAL_MS else 0f) }
    val finished by rememberUpdatedState(onFinished)
    LaunchedEffect(Unit) {
        if (!motionOff) {
            clock.animateTo(
                LaunchMarkTimeline.TOTAL_MS,
                tween(LaunchMarkTimeline.TOTAL_MS.toInt(), easing = LinearEasing),
            )
        }
        finished()
    }
    val t = clock.value
    val seal = LaunchMarkTimeline.seal(t)
    val word = LaunchMarkTimeline.word(t)
    Box(
        modifier = modifier
            .fillMaxSize()
            .background(ProColors.Paper)
            .semantics { contentDescription = "HSK AI" },
        contentAlignment = Alignment.Center,
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(20.dp)) {
            Canvas(
                Modifier
                    .size(96.dp)
                    .graphicsLayer {
                        alpha = seal
                        val s = 0.9f + 0.1f * seal
                        scaleX = s
                        scaleY = s
                    },
            ) { drawKnotThread(t) }
            Text(
                text = buildAnnotatedString {
                    append("HSK ")
                    withStyle(SpanStyle(color = PompColors.GoldInk)) { append("AI") }
                },
                style = TextStyle(fontSize = 25.sp, fontWeight = FontWeight.ExtraBold, letterSpacing = 2.7.sp),
                color = PompColors.Ink,
                modifier = Modifier.graphicsLayer {
                    alpha = word
                    translationY = 10.dp.toPx() * (1f - word)
                },
            )
        }
    }
}

/** Shared launch timeline (ms). Mirrors `HSKLaunchMark.TIMELINE` in the PWA. */
internal object LaunchMarkTimeline {
    const val SEAL_START = 0f
    const val SEAL_MS = 260f
    const val STRAND_A_START = 140f
    const val STRAND_B_START = 260f
    const val STRAND_MS = 420f
    const val WEAVE_START = 640f
    const val WEAVE_MS = 80f
    const val GLINT_START = 760f
    const val GLINT_MS = 300f
    const val WORD_START = 820f
    const val WORD_MS = 280f
    const val TOTAL_MS = 1150f

    fun phase(clock: Float, start: Float, duration: Float): Float =
        ((clock - start) / duration).coerceIn(0f, 1f)

    private fun easeOut(p: Float): Float = 1f - (1f - p) * (1f - p) * (1f - p)

    fun seal(clock: Float) = easeOut(phase(clock, SEAL_START, SEAL_MS))
    fun strandA(clock: Float) = easeOut(phase(clock, STRAND_A_START, STRAND_MS))
    fun strandB(clock: Float) = easeOut(phase(clock, STRAND_B_START, STRAND_MS))
    fun weave(clock: Float) = phase(clock, WEAVE_START, WEAVE_MS)
    fun word(clock: Float) = easeOut(phase(clock, WORD_START, WORD_MS))

    /** Glint band position 0..1 while it crosses; null before and after. */
    fun glint(clock: Float): Float? {
        if (clock <= GLINT_START || clock >= GLINT_START + GLINT_MS) return null
        return phase(clock, GLINT_START, GLINT_MS)
    }
}

// Explicit 108-unit endpoints: the brush is resolved inside the scaled logo grid.
// The casing reuses the seal gradient, so an under-pass reads as a cut in the knot.
private val SealRed = Brush.linearGradient(
    listOf(Color(0xFFF0614C), Color(0xFFC02F32)), start = Offset.Zero, end = Offset(108f, 108f),
)
private val StrandGold = listOf(Color(0xFFF7C948), Color(0xFFD9920F))

/** The knot in the 108-unit logo grid (branding/hsk-ai-logo.svg). */
private fun DrawScope.drawKnotThread(clock: Float) {
    val k = size.minDimension / 108f
    scale(k, k, pivot = Offset.Zero) {
        val sealPath = Path().apply {
            addRoundRect(RoundRect(0f, 0f, 108f, 108f, CornerRadius(22f)))
        }
        clipPath(sealPath) {
            drawPath(sealPath, SealRed)
            val gold = Brush.verticalGradient(StrandGold, startY = 28f, endY = 80f)
            val square = Path().apply {
                addRoundRect(RoundRect(35f, 35f, 73f, 73f, CornerRadius(4.5f)))
            }
            drawStrand(square, LaunchMarkTimeline.strandA(clock), reverse = false, gold)
            rotate(45f, pivot = Offset(54f, 54f)) {
                drawStrand(square, LaunchMarkTimeline.strandB(clock), reverse = true, gold)
            }
            val weave = LaunchMarkTimeline.weave(clock)
            if (weave > 0f) {
                val over = Path().apply {
                    moveTo(39.5f, 35f); lineTo(52.9f, 35f)
                    moveTo(73f, 39.5f); lineTo(73f, 52.9f)
                    moveTo(68.5f, 73f); lineTo(55.1f, 73f)
                    moveTo(35f, 68.5f); lineTo(35f, 55.1f)
                }
                drawPath(over, SealRed, alpha = weave, style = Stroke(9.5f, cap = StrokeCap.Butt))
                drawPath(over, gold, alpha = weave, style = Stroke(6f, cap = StrokeCap.Butt))
            }
            LaunchMarkTimeline.glint(clock)?.let { p ->
                val x = -40f + 200f * p
                rotate(-18f, pivot = Offset(x, 54f)) {
                    drawRect(
                        Brush.horizontalGradient(
                            listOf(Color.Transparent, ProColors.Glint, Color.Transparent),
                            startX = x, endX = x + 34f,
                        ),
                        topLeft = Offset(x, -20f),
                        size = Size(34f, 148f),
                    )
                }
            }
        }
    }
}

private fun DrawScope.drawStrand(path: Path, progress: Float, reverse: Boolean, gold: Brush) {
    if (progress <= 0f) return
    val drawn = if (progress >= 1f) path else {
        val measure = PathMeasure().apply { setPath(path, false) }
        val length = measure.length
        Path().also { out ->
            if (reverse) measure.getSegment(length * (1f - progress), length, out, true)
            else measure.getSegment(0f, length * progress, out, true)
        }
    }
    drawPath(drawn, SealRed, style = Stroke(9.5f, cap = StrokeCap.Round, join = StrokeJoin.Round))
    drawPath(drawn, gold, style = Stroke(6f, cap = StrokeCap.Round, join = StrokeJoin.Round))
}
