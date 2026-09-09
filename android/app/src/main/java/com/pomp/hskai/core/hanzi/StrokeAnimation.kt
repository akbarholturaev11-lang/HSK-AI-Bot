package com.pomp.hskai.core.hanzi

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Matrix
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathMeasure
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.vector.PathParser
import androidx.compose.ui.unit.dp
import com.pomp.hskai.core.design.PompColors

/**
 * A character written stroke by stroke, from the hanzi-writer data the Mini
 * App uses.
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
    strokes: List<String>,
    modifier: Modifier = Modifier,
    replayKey: Int = 0,
) {
    val paths = remember(strokes) { strokes.mapNotNull(::parseStroke) }
    var run by remember(strokes) { mutableStateOf(0) }
    LaunchedEffect(strokes, replayKey) { run++ }

    val progress by animateFloatAsState(
        targetValue = if (run > 0) paths.size.toFloat() else 0f,
        animationSpec = tween(
            durationMillis = paths.size * MILLIS_PER_STROKE,
            easing = LinearEasing,
        ),
        label = "strokeProgress",
    )

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
        paths.forEachIndexed { index, source ->
            val path = Path().apply { addPath(source) }
            path.transform(matrix)

            drawPath(
                path = path,
                color = PompColors.Divider,
                style = Stroke(width = 2f, cap = StrokeCap.Round, join = StrokeJoin.Round),
            )
            val strokeProgress = (progress - index).coerceIn(0f, 1f)
            if (strokeProgress <= 0f) return@forEachIndexed
            drawPath(
                path = if (strokeProgress >= 1f) path else partial(path, strokeProgress),
                color = PompColors.Ink,
            )
        }
    }
}

private fun parseStroke(data: String): Path? =
    runCatching { PathParser().parsePathString(data).toPath() }.getOrNull()

/** The first [fraction] of a filled stroke, so it appears to be written. */
private fun partial(path: Path, fraction: Float): Path {
    val measure = PathMeasure().apply { setPath(path, false) }
    val cut = Path()
    measure.getSegment(0f, measure.length * fraction, cut, true)
    return cut
}

private const val MILLIS_PER_STROKE = 420

/** hanzi-writer draws on a 1024 grid. */
private const val GRID = 1024f
