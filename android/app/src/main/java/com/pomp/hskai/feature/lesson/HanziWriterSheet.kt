package com.pomp.hskai.feature.lesson

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Matrix
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathMeasure
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.vector.PathParser
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompTextStyles

/** The grid hanzi-writer data is drawn in. */
private const val GRID = 1024f

/**
 * How a character is written, stroke by stroke.
 *
 * The Mini App puts a pencil beside the lesson and plays the strokes in
 * order; a learner who has only ever seen the finished character does not
 * know where it starts. The data is the same hanzi-writer set the Mini App
 * uses, fetched through our own origin because the app talks to one host.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun HanziWriterSheet(
    hanzi: String,
    pinyin: String,
    meaning: String,
    strokes: List<String>?,
    isLoading: Boolean,
    onReplay: () -> Unit,
    onDismiss: () -> Unit,
) {
    val sheetState = rememberModalBottomSheetState()
    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = PompColors.PaperRaised,
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 20.dp)
                .padding(bottom = 28.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            if (pinyin.isNotBlank()) {
                Text(
                    text = pinyin,
                    style = PompTextStyles.pinyin.copy(fontSize = 17.sp),
                    fontWeight = FontWeight.Medium,
                    color = PompColors.CinnabarDark,
                )
            }
            if (meaning.isNotBlank()) {
                Text(
                    text = meaning,
                    style = MaterialTheme.typography.bodyMedium,
                    color = PompColors.InkSecondary,
                    textAlign = TextAlign.Center,
                )
            }
            Spacer(Modifier.height(14.dp))

            Surface(
                color = PompColors.Paper,
                shape = RoundedCornerShape(18.dp),
                border = BorderStroke(1.dp, PompColors.Divider),
                modifier = Modifier
                    .fillMaxWidth()
                    .aspectRatio(1f),
            ) {
                Box(contentAlignment = Alignment.Center) {
                    when {
                        isLoading -> CircularProgressIndicator(color = PompColors.Cinnabar)

                        // Without the outlines the character is still shown —
                        // the learner loses the animation, not the word.
                        strokes.isNullOrEmpty() -> Text(
                            text = hanzi,
                            style = PompTextStyles.hanziLarge.copy(fontSize = 128.sp),
                            color = PompColors.Ink,
                        )

                        else -> StrokeAnimation(strokes)
                    }
                }
            }

            Spacer(Modifier.height(14.dp))
            Surface(
                onClick = onReplay,
                enabled = !isLoading && !strokes.isNullOrEmpty(),
                color = PompColors.Gold,
                shape = RoundedCornerShape(13.dp),
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 22.dp, vertical = 13.dp),
                    horizontalArrangement = Arrangement.Center,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        text = stringResource(R.string.lesson_writer_replay),
                        style = MaterialTheme.typography.labelLarge.copy(fontSize = 15.sp),
                        fontWeight = FontWeight.SemiBold,
                        color = PompColors.PlanOnGold,
                    )
                }
            }
        }
    }
}

/**
 * Draws the finished character faintly, then inks each stroke in order.
 *
 * The stroke paths are given in a grid whose origin is bottom-left, so the
 * whole set is flipped once and scaled to the canvas.
 */
@Composable
private fun StrokeAnimation(strokes: List<String>) {
    val paths = remember(strokes) { strokes.mapNotNull(::parseStroke) }
    var run by remember(strokes) { mutableStateOf(0) }
    LaunchedEffect(strokes) { run++ }

    val progress by animateFloatAsState(
        targetValue = if (run > 0) paths.size.toFloat() else 0f,
        animationSpec = tween(
            durationMillis = paths.size * MILLIS_PER_STROKE,
            easing = LinearEasing,
        ),
        label = "strokeProgress",
    )

    Canvas(modifier = Modifier.fillMaxWidth().aspectRatio(1f).padding(18.dp)) {
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
