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
 * Bitta qatordagi yo'lakcha — Mini App `drawTrails()` ning native ekvivalenti.
 *
 * Faqat shu qatorga tegishli bo'lak chiziladi, qator koordinatasida. Qo'shni
 * qatorlar bir xil nuqtalardan hisoblangani uchun chegarada uzilish
 * ko'rinmaydi.
 */
@Composable
internal fun ContinuousCourseTrail(
    previousXDp: Float?,
    currentXDp: Float,
    nextXDp: Float?,
    modifier: Modifier = Modifier,
) {
    val segments = remember(previousXDp, currentXDp, nextXDp) {
        courseTrailSegmentsForRow(previousXDp, currentXDp, nextXDp)
    }
    if (segments.isEmpty()) return

    Canvas(modifier = modifier) {
        val centerX = size.width / 2f
        val path = Path()
        segments.forEach { s ->
            path.moveTo(centerX + s.startXDp.dp.toPx(), s.startYDp.dp.toPx())
            path.cubicTo(
                centerX + s.control1XDp.dp.toPx(), s.control1YDp.dp.toPx(),
                centerX + s.control2XDp.dp.toPx(), s.control2YDp.dp.toPx(),
                centerX + s.endXDp.dp.toPx(), s.endYDp.dp.toPx(),
            )
        }
        drawPath(
            path = path,
            color = PompColors.CourseTrail,
            style = Stroke(width = 34.dp.toPx(), cap = StrokeCap.Round),
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
