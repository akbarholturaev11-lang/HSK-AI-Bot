package com.pomp.hskai.feature.course

import androidx.compose.foundation.Canvas
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.dp
import com.pomp.hskai.core.design.PompColors

/**
 * One-path native equivalent of Mini App `drawTrails()` for a single course unit.
 * The caller owns the path container height; this renderer only draws behind nodes.
 */
@Composable
internal fun ContinuousCourseTrail(
    unitIndex: Int,
    nodeCount: Int,
    modifier: Modifier = Modifier,
) {
    val cubics = remember(unitIndex, nodeCount) {
        courseTrailCubics(unitIndex = unitIndex, nodeCount = nodeCount)
    }
    if (cubics.isEmpty()) return

    Canvas(modifier = modifier) {
        val centerX = size.width / 2f
        val path = Path().apply {
            val first = cubics.first().start
            moveTo(centerX + first.xOffsetDp.dp.toPx(), first.yDp.dp.toPx())
            cubics.forEach { segment ->
                cubicTo(
                    centerX + segment.control1.xOffsetDp.dp.toPx(),
                    segment.control1.yDp.dp.toPx(),
                    centerX + segment.control2.xOffsetDp.dp.toPx(),
                    segment.control2.yDp.dp.toPx(),
                    centerX + segment.end.xOffsetDp.dp.toPx(),
                    segment.end.yDp.dp.toPx(),
                )
            }
        }
        drawPath(
            path = path,
            color = PompColors.CourseTrail,
            style = Stroke(
                width = 34.dp.toPx(),
                cap = StrokeCap.Round,
            ),
        )
        drawPath(
            path = path,
            color = Color.White.copy(alpha = 0.80f),
            style = Stroke(
                width = 4.dp.toPx(),
                cap = StrokeCap.Round,
                pathEffect = PathEffect.dashPathEffect(
                    intervals = floatArrayOf(0.5.dp.toPx(), 16.dp.toPx()),
                ),
            ),
        )
    }
}
