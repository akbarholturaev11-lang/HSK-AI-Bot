package com.pomp.hskai.core.hanzi

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Matrix
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathMeasure
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.clipPath
import androidx.compose.ui.graphics.vector.PathParser
import androidx.compose.ui.unit.dp
import com.pomp.hskai.core.design.PompColors
import kotlinx.coroutines.delay

/**
 * One character's writing data: the filled shape of each stroke and the line
 * the brush travels down it.
 *
 * Both come from the same hanzi-writer payload and are meaningless apart, so
 * they travel together rather than as two lists a caller could pair up wrong.
 */
data class CharacterStrokes(
    val outlines: List<String>,
    val medians: List<List<Offset>> = emptyList(),
) {
    val size: Int get() = outlines.size
    fun isEmpty(): Boolean = outlines.isEmpty()
    fun isNotEmpty(): Boolean = outlines.isNotEmpty()

    companion object {
        val EMPTY = CharacterStrokes(emptyList())
    }
}

/**
 * A character written stroke by stroke, from the hanzi-writer data the Mini
 * App uses.
 *
 * **How a stroke is written.** A hanzi-writer stroke is a filled outline — the
 * shape of the brush mark — not a line to trace. The previous version animated
 * it by cutting a fraction of that outline's *perimeter* and filling what was
 * left, which is not a partly written stroke at all: it is a sliver of the
 * edge, and it looked like one. The brush travels down the stroke's centre
 * line instead, so the ink is revealed by sweeping a thick round line along
 * the median and clipping it to the stroke's own shape. That is what
 * hanzi-writer does, and it is why a stroke now grows the way a pen draws it.
 *
 * **How long it takes.** Each stroke's duration follows its own length, so a
 * long sweeping stroke is not over in the same instant as a short tick, and
 * the strokes are separated by a pause. Both are the Mini App's numbers.
 *
 * The stroke paths are given in a grid whose origin is bottom-left, so the
 * whole set is flipped once and scaled to the canvas.
 *
 * This lives outside any one screen because two of them show the same thing:
 * the lesson's writing sheet and the dictionary entry. One drawing, so a
 * character cannot be written differently depending on where it is opened.
 */
@Composable
fun StrokeAnimation(
    strokes: CharacterStrokes,
    modifier: Modifier = Modifier,
    replayKey: Int = 0,
    /** Null animates every stroke; a value shows exactly that many strokes. */
    visibleStrokeCount: Int? = null,
) {
    val paths = remember(strokes) { strokes.outlines.mapNotNull(::parseStroke) }
    val medians = remember(strokes) { strokes.medians.map(::medianPath) }
    // How far into the character the brush is: 2.4 means stroke 3 is 40% done.
    val progress = remember(strokes) { Animatable(0f) }

    LaunchedEffect(strokes, replayKey, visibleStrokeCount) {
        val manualCount = visibleStrokeCount
        if (manualCount != null) {
            progress.snapTo(manualCount.coerceIn(0, paths.size).toFloat())
            return@LaunchedEffect
        }
        progress.snapTo(0f)
        // One stroke at a time, each paced by its own length, with the Mini
        // App's pause in between. Animating the whole character as a single
        // linear sweep was what made it read as fast and mechanical.
        strokes.medians.forEachIndexed { index, median ->
            progress.animateTo(
                targetValue = index + 1f,
                animationSpec = tween(
                    durationMillis = strokeDurationMillis(median),
                    easing = FastOutSlowInEasing,
                ),
            )
            if (index < strokes.medians.lastIndex) delay(DELAY_BETWEEN_STROKES_MILLIS)
        }
    }

    Canvas(
        modifier = modifier
            .fillMaxWidth()
            .aspectRatio(1f)
            .padding(18.dp),
    ) {
        val scale = size.minDimension / GRID
        val matrix = Matrix().apply {
            // hanzi-writer's own transform: flip the y axis, then fit the box.
            translate(0f, size.height)
            scale(scale, -scale)
        }
        // Wide enough to cover the stroke it is clipped to, whatever its shape.
        val brushWidth = GRID * BRUSH_WIDTH_RATIO * scale

        paths.forEachIndexed { index, source ->
            val path = Path().apply { addPath(source) }
            path.transform(matrix)

            // The unwritten character sits underneath as a faint filled shape,
            // the way hanzi-writer shows its outline — not as a hairline
            // wireframe, which is what a 2px stroke drew.
            drawPath(path = path, color = PompColors.Divider)

            val strokeProgress = visibleStrokeCount?.let { count ->
                if (index < count.coerceIn(0, paths.size)) 1f else 0f
            } ?: (progress.value - index).coerceIn(0f, 1f)
            if (strokeProgress <= 0f) return@forEachIndexed

            val median = medians.getOrNull(index)
            if (strokeProgress >= 1f || median == null) {
                // Finished, or a character whose payload carried no median:
                // fill the whole stroke rather than animate it wrongly.
                drawPath(path = path, color = PompColors.Ink)
                return@forEachIndexed
            }
            val brush = Path().apply { addPath(median) }
            brush.transform(matrix)
            clipPath(path) {
                drawPath(
                    path = partial(brush, strokeProgress),
                    color = PompColors.Ink,
                    style = Stroke(
                        width = brushWidth,
                        cap = StrokeCap.Round,
                        join = StrokeJoin.Round,
                    ),
                )
            }
        }
    }
}

private fun parseStroke(data: String): Path? =
    runCatching { PathParser().parsePathString(data).toPath() }.getOrNull()

/** The brush's route down one stroke, as a path through its median points. */
private fun medianPath(points: List<Offset>): Path? {
    if (points.size < 2) return null
    return Path().apply {
        moveTo(points.first().x, points.first().y)
        points.drop(1).forEach { lineTo(it.x, it.y) }
    }
}

/**
 * How long one stroke takes, from how far the brush travels.
 *
 * hanzi-writer paces a stroke by its own length rather than giving every
 * stroke the same time, which is what keeps a long sweep from finishing as
 * abruptly as a short tick.
 */
private fun strokeDurationMillis(median: List<Offset>): Int {
    var length = 0f
    for (index in 1 until median.size) {
        length += (median[index] - median[index - 1]).getDistance()
    }
    return ((length + STROKE_DURATION_BASE) / STROKE_DURATION_DIVISOR)
        .toInt()
        .coerceIn(MIN_STROKE_MILLIS, MAX_STROKE_MILLIS)
}

/** The first [fraction] of the brush's route. */
private fun partial(path: Path, fraction: Float): Path {
    val measure = PathMeasure().apply { setPath(path, false) }
    val cut = Path()
    measure.getSegment(0f, measure.length * fraction, cut, true)
    return cut
}

// hanzi-writer's own pacing: `(length + 600) / 3` at its default speed of 1.
private const val STROKE_DURATION_BASE = 600f
private const val STROKE_DURATION_DIVISOR = 3f
private const val MIN_STROKE_MILLIS = 220
private const val MAX_STROKE_MILLIS = 900

/** `delayBetweenStrokes` on the Mini App's dictionary writer. */
private const val DELAY_BETWEEN_STROKES_MILLIS = 280L

/**
 * Brush width as a share of the 1024 grid.
 *
 * It only has to be wide enough to cover the widest stroke once clipped to it,
 * so it is generous on purpose — the stroke's own outline decides the edge.
 */
private const val BRUSH_WIDTH_RATIO = 0.22f

/** hanzi-writer draws on a 1024 grid. */
private const val GRID = 1024f
