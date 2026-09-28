package com.pomp.hskai.feature.dictionary

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Matrix
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.clipPath
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.components.HskDepthButton
import com.pomp.hskai.core.design.components.HskGlassButton
import com.pomp.hskai.core.design.components.HskGlassIconButton
import com.pomp.hskai.core.design.components.HskStageProgress
import com.pomp.hskai.core.hanzi.BRUSH_WIDTH_RATIO
import com.pomp.hskai.core.hanzi.HanziGrid
import com.pomp.hskai.core.hanzi.StrokeAnimation
import com.pomp.hskai.core.hanzi.medianPath
import com.pomp.hskai.core.hanzi.parseStroke
import com.pomp.hskai.core.hanzi.partial
import com.pomp.hskai.core.hanzi.strokeDurationMillis

/**
 * Writing one character by hand: the app writes it, then the learner does,
 * three times with less help each time.
 */
@Composable
internal fun HanziWritingScreen(
    writing: WritingUiState,
    hasNextCharacter: Boolean,
    onClose: () -> Unit,
    onDemoAgain: () -> Unit,
    onBegin: () -> Unit,
    onStroke: (List<Offset>) -> Unit,
    onHint: () -> Unit,
    onRestart: () -> Unit,
    onWriteAgain: () -> Unit,
    onNextCharacter: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .statusBarsPadding()
            .navigationBarsPadding()
            .padding(horizontal = 20.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            HskGlassIconButton(
                icon = Icons.Filled.Close,
                contentDescription = stringResource(R.string.action_close),
                onClick = onClose,
                tint = PompColors.Ink,
            )
            HskStageProgress(
                progress = writing.progress,
                modifier = Modifier.weight(1f).padding(horizontal = 8.dp),
            )
            val round = writing.stage.round
            Text(
                text = if (round != null) {
                    stringResource(R.string.lesson_writer_position, round, WritingStage.ROUNDS)
                } else {
                    ""
                },
                style = MaterialTheme.typography.labelLarge,
                color = PompColors.InkSecondary,
            )
        }

        Text(
            text = stageTitle(writing.stage),
            style = MaterialTheme.typography.titleMedium,
            color = PompColors.Ink,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = 18.dp),
        )

        Surface(
            color = PompColors.PaperRaised,
            shape = RoundedCornerShape(20.dp),
            shadowElevation = 6.dp,
            modifier = Modifier
                .padding(top = 14.dp)
                .widthIn(max = 420.dp)
                .fillMaxWidth()
                .aspectRatio(1f),
        ) {
            Box {
                WriterGrid(Modifier.fillMaxSize())
                if (writing.stage == WritingStage.DEMO) {
                    StrokeAnimation(
                        strokes = writing.strokes,
                        replayKey = writing.demoKey,
                        modifier = Modifier.fillMaxSize(),
                    )
                } else {
                    WritingCanvas(writing, onStroke, Modifier.fillMaxSize())
                }
            }
        }

        StatusLine(writing, Modifier.padding(top = 12.dp))
        Spacer(Modifier.weight(1f))
        Actions(
            writing = writing,
            hasNextCharacter = hasNextCharacter,
            onClose = onClose,
            onDemoAgain = onDemoAgain,
            onBegin = onBegin,
            onHint = onHint,
            onRestart = onRestart,
            onWriteAgain = onWriteAgain,
            onNextCharacter = onNextCharacter,
        )
    }
}

@Composable
private fun stageTitle(stage: WritingStage): String = stringResource(
    when (stage) {
        WritingStage.DEMO -> R.string.writing_stage_demo
        WritingStage.TRACE -> R.string.writing_stage_trace
        WritingStage.HINT -> R.string.writing_stage_hint
        WritingStage.MEMORY -> R.string.writing_stage_memory
        WritingStage.DONE -> R.string.writing_done_title
    },
)

@Composable
private fun StatusLine(writing: WritingUiState, modifier: Modifier = Modifier) {
    val (text, color) = when {
        writing.stage == WritingStage.DEMO -> "" to PompColors.InkSecondary
        writing.stage == WritingStage.DONE && writing.totalMistakes == 0 ->
            stringResource(R.string.writing_done_clean) to PompColors.Jade
        writing.stage == WritingStage.DONE ->
            stringResource(R.string.writing_done_mistakes, writing.totalMistakes) to PompColors.InkSecondary
        writing.lastMiss == WritingMiss.BACKWARDS ->
            stringResource(R.string.writing_miss_backwards) to PompColors.CinnabarDark
        writing.lastMiss == WritingMiss.WRONG ->
            stringResource(R.string.writing_miss_wrong) to PompColors.CinnabarDark
        else -> stringResource(
            R.string.writing_stroke_progress,
            (writing.strokeIndex + 1).coerceAtMost(writing.strokeCount),
            writing.strokeCount,
        ) to PompColors.InkSecondary
    }
    Text(
        text = text,
        style = MaterialTheme.typography.bodyMedium,
        color = color,
        textAlign = TextAlign.Center,
        modifier = modifier.fillMaxWidth(),
    )
}

@Composable
private fun Actions(
    writing: WritingUiState,
    hasNextCharacter: Boolean,
    onClose: () -> Unit,
    onDemoAgain: () -> Unit,
    onBegin: () -> Unit,
    onHint: () -> Unit,
    onRestart: () -> Unit,
    onWriteAgain: () -> Unit,
    onNextCharacter: () -> Unit,
) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 16.dp),
        horizontalArrangement = Arrangement.spacedBy(10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        when (writing.stage) {
            WritingStage.DEMO -> {
                HskGlassButton(
                    text = stringResource(R.string.writing_demo_again),
                    onClick = onDemoAgain,
                    enabled = writing.canPlayDemoAgain,
                    modifier = Modifier.weight(1f),
                )
                HskDepthButton(
                    text = stringResource(R.string.writing_start),
                    color = PompColors.Cinnabar,
                    onClick = onBegin,
                    modifier = Modifier.weight(1f),
                )
            }

            WritingStage.DONE -> {
                HskGlassButton(
                    text = stringResource(R.string.writing_again),
                    onClick = onWriteAgain,
                    modifier = Modifier.weight(1f),
                )
                HskDepthButton(
                    text = stringResource(
                        if (hasNextCharacter) R.string.writing_next_character else R.string.writing_finish,
                    ),
                    color = PompColors.Cinnabar,
                    onClick = if (hasNextCharacter) onNextCharacter else onClose,
                    modifier = Modifier.weight(1f),
                )
            }

            else -> {
                HskGlassButton(
                    text = stringResource(R.string.writing_hint),
                    onClick = onHint,
                    enabled = writing.acceptsStrokes,
                    modifier = Modifier.weight(1f),
                )
                HskGlassButton(
                    text = stringResource(R.string.writing_restart),
                    onClick = onRestart,
                    enabled = writing.acceptsStrokes && writing.strokeIndex > 0,
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
}

/**
 * The square the learner writes in.
 *
 * Touches are collected per stroke and handed over in the character's own
 * grid, where they are compared with the stroke that should come next. What
 * is drawn back is the stroke's real shape, not the finger's line — the way
 * hanzi-writer's quiz does it — so the character builds up looking right.
 */
@Composable
private fun WritingCanvas(
    writing: WritingUiState,
    onStroke: (List<Offset>) -> Unit,
    modifier: Modifier = Modifier,
) {
    val outlines = remember(writing.strokes) { writing.strokes.outlines.mapNotNull(::parseStroke) }
    val medians = remember(writing.strokes) { writing.strokes.medians.map(::medianPath) }
    val submit by rememberUpdatedState(onStroke)
    var drawing by remember { mutableStateOf<List<Offset>>(emptyList()) }
    var lastDrawn by remember { mutableStateOf<List<Offset>>(emptyList()) }
    var rejected by remember { mutableStateOf<List<Offset>>(emptyList()) }
    val rejectedAlpha = remember { Animatable(0f) }
    val hintProgress = remember { Animatable(0f) }

    // A miss: the learner's own line turns red and fades, so it is clear the
    // stroke was seen and refused rather than lost.
    LaunchedEffect(writing.missKey) {
        if (writing.missKey == 0) return@LaunchedEffect
        rejected = lastDrawn
        rejectedAlpha.snapTo(1f)
        rejectedAlpha.animateTo(0f, tween(REJECT_FADE_MILLIS))
        rejected = emptyList()
    }
    LaunchedEffect(writing.hintKey, writing.hintStroke) {
        val stroke = writing.hintStroke ?: return@LaunchedEffect
        val median = writing.strokes.medians.getOrNull(stroke) ?: return@LaunchedEffect
        hintProgress.snapTo(0f)
        hintProgress.animateTo(1f, tween(strokeDurationMillis(median), easing = FastOutSlowInEasing))
    }

    Canvas(
        modifier = modifier
            .padding(18.dp)
            .testTag(WRITING_CANVAS_TAG)
            .pointerInput(writing.acceptsStrokes) {
                if (!writing.acceptsStrokes) return@pointerInput
                awaitEachGesture {
                    val down = awaitFirstDown()
                    down.consume()
                    val points = mutableListOf(down.position)
                    drawing = points.toList()
                    while (true) {
                        val event = awaitPointerEvent()
                        val change = event.changes.firstOrNull { it.id == down.id } ?: break
                        if (!change.pressed) break
                        points += change.position
                        drawing = points.toList()
                        change.consume()
                    }
                    val side = minOf(size.width, size.height).toFloat()
                    lastDrawn = points.toList()
                    drawing = emptyList()
                    submit(points.map { HanziGrid.toGrid(it, side) })
                }
            },
    ) {
        val side = size.minDimension
        val matrix = HanziGrid.matrix(side)
        val shapes = outlines.map { source -> Path().apply { addPath(source); transform(matrix) } }
        val done = when {
            writing.stage == WritingStage.DONE -> shapes.size
            else -> writing.strokeIndex.coerceAtMost(shapes.size)
        }
        val inkColor = if (writing.isRoundComplete) PompColors.Jade else PompColors.Ink

        if (writing.stage.showsOutline) shapes.forEach { drawPath(it, PompColors.Divider) }
        for (index in 0 until done) drawPath(shapes[index], inkColor)

        val hinted = writing.hintStroke
        if (hinted != null && hinted >= done && hinted < shapes.size) {
            drawHint(shapes[hinted], medians.getOrNull(hinted), matrix, hintProgress.value, side)
        }

        if (writing.stage.showsStartDot && writing.acceptsStrokes) {
            writing.strokes.medians.getOrNull(writing.strokeIndex)?.firstOrNull()?.let { start ->
                drawCircle(
                    color = PompColors.Cinnabar,
                    radius = side * START_DOT_RATIO,
                    center = HanziGrid.toCanvas(start, side),
                )
            }
        }

        if (rejected.size > 1) {
            drawLine(rejected, PompColors.Cinnabar.copy(alpha = rejectedAlpha.value), side)
        }
        if (drawing.size > 1) drawLine(drawing, PompColors.Ink, side)
    }
}

private fun DrawScope.drawHint(
    shape: Path,
    median: Path?,
    matrix: Matrix,
    progress: Float,
    side: Float,
) {
    val color = PompColors.Cinnabar.copy(alpha = HINT_ALPHA)
    if (median == null || progress >= 1f) {
        drawPath(shape, color)
        return
    }
    val brush = Path().apply { addPath(median); transform(matrix) }
    clipPath(shape) {
        drawPath(
            path = partial(brush, progress),
            color = color,
            style = Stroke(width = side * BRUSH_WIDTH_RATIO, cap = StrokeCap.Round, join = StrokeJoin.Round),
        )
    }
}

private fun DrawScope.drawLine(points: List<Offset>, color: Color, side: Float) {
    val path = Path().apply {
        moveTo(points.first().x, points.first().y)
        points.drop(1).forEach { lineTo(it.x, it.y) }
    }
    drawPath(
        path = path,
        color = color,
        style = Stroke(width = side * PEN_WIDTH_RATIO, cap = StrokeCap.Round, join = StrokeJoin.Round),
    )
}

/** The square the learner writes in; the handwriting test draws on it. */
internal const val WRITING_CANVAS_TAG = "hanzi-writing-canvas"

private const val REJECT_FADE_MILLIS = 500
private const val HINT_ALPHA = 0.55f
private const val START_DOT_RATIO = 0.022f
private const val PEN_WIDTH_RATIO = 0.035f
