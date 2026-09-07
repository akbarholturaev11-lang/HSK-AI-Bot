package com.pomp.hskai.feature.course

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

/**
 * Native stroke icons matching the Tabler icons used by Mini App course-v3:
 * check, lock, flag-2, gift, star and book-2.
 *
 * Tabler's visual language is a 24x24 grid with rounded 2px strokes. Keeping
 * the same grid/stroke ratios avoids the heavier filled Material glyphs that
 * were still visible on the Android course path and unit banners.
 */
internal enum class CourseNodeIconKind { Check, Lock, Flag, Gift, Star, Book2 }

/** Mini App node-specific sizing so CourseScreen does not re-invent glyph metrics. */
@Composable
internal fun MiniAppLessonNodeIcon(
    kind: CourseNodeIconKind,
    tint: Color,
    modifier: Modifier = Modifier,
) {
    val iconSize = when (kind) {
        CourseNodeIconKind.Check -> 28.dp
        CourseNodeIconKind.Lock -> 22.dp
        CourseNodeIconKind.Flag -> 25.dp
        CourseNodeIconKind.Gift -> 30.dp
        CourseNodeIconKind.Star -> 27.dp
        CourseNodeIconKind.Book2 -> 24.dp
    }
    MiniAppNodeIcon(kind = kind, tint = tint, modifier = modifier, size = iconSize)
}

@Composable
internal fun MiniAppNodeIcon(
    kind: CourseNodeIconKind,
    tint: Color,
    modifier: Modifier = Modifier,
    size: Dp = 24.dp,
) {
    Canvas(modifier = modifier.size(size)) {
        val sx = this.size.width / 24f
        val sy = this.size.height / 24f
        val strokeWidth = 2f * ((sx + sy) / 2f)
        fun x(v: Float) = v * sx
        fun y(v: Float) = v * sy
        val stroke = Stroke(width = strokeWidth, cap = StrokeCap.Round, join = StrokeJoin.Round)

        when (kind) {
            CourseNodeIconKind.Check -> {
                val p = Path().apply {
                    moveTo(x(5f), y(12f))
                    lineTo(x(10f), y(17f))
                    lineTo(x(20f), y(7f))
                }
                drawPath(p, tint, style = stroke)
            }

            CourseNodeIconKind.Lock -> {
                drawRoundRect(
                    color = tint,
                    topLeft = Offset(x(5f), y(11f)),
                    size = Size(x(14f), y(10f)),
                    cornerRadius = CornerRadius(x(2f), y(2f)),
                    style = stroke,
                )
                val shackle = Path().apply {
                    moveTo(x(8f), y(11f))
                    lineTo(x(8f), y(7f))
                    cubicTo(x(8f), y(4.8f), x(9.8f), y(3f), x(12f), y(3f))
                    cubicTo(x(14.2f), y(3f), x(16f), y(4.8f), x(16f), y(7f))
                    lineTo(x(16f), y(11f))
                }
                drawPath(shackle, tint, style = stroke)
            }

            CourseNodeIconKind.Flag -> {
                val pole = Path().apply {
                    moveTo(x(5f), y(21f))
                    lineTo(x(5f), y(5f))
                }
                drawPath(pole, tint, style = stroke)
                val flag = Path().apply {
                    moveTo(x(5f), y(5f))
                    cubicTo(x(8.5f), y(2.8f), x(10.5f), y(7.2f), x(14f), y(5f))
                    cubicTo(x(16.2f), y(3.6f), x(18f), y(4.2f), x(19f), y(5f))
                    lineTo(x(19f), y(14f))
                    cubicTo(x(16.5f), y(12.4f), x(14.5f), y(12.8f), x(12f), y(14f))
                    cubicTo(x(9.2f), y(15.4f), x(7.2f), y(12.8f), x(5f), y(14f))
                }
                drawPath(flag, tint, style = stroke)
            }

            CourseNodeIconKind.Gift -> {
                drawRoundRect(
                    color = tint,
                    topLeft = Offset(x(3f), y(8f)),
                    size = Size(x(18f), y(4f)),
                    cornerRadius = CornerRadius(x(1f), y(1f)),
                    style = stroke,
                )
                drawRoundRect(
                    color = tint,
                    topLeft = Offset(x(5f), y(12f)),
                    size = Size(x(14f), y(9f)),
                    cornerRadius = CornerRadius(x(1f), y(1f)),
                    style = stroke,
                )
                drawLine(tint, Offset(x(12f), y(8f)), Offset(x(12f), y(21f)), strokeWidth, StrokeCap.Round)
                val leftBow = Path().apply {
                    moveTo(x(12f), y(8f))
                    cubicTo(x(10.6f), y(4f), x(8.5f), y(3f), x(7f), y(3f))
                    cubicTo(x(5.3f), y(3f), x(4f), y(4.3f), x(4f), y(6f))
                    cubicTo(x(4f), y(7.3f), x(5.2f), y(8f), x(7f), y(8f))
                    close()
                }
                val rightBow = Path().apply {
                    moveTo(x(12f), y(8f))
                    cubicTo(x(13.4f), y(4f), x(15.5f), y(3f), x(17f), y(3f))
                    cubicTo(x(18.7f), y(3f), x(20f), y(4.3f), x(20f), y(6f))
                    cubicTo(x(20f), y(7.3f), x(18.8f), y(8f), x(17f), y(8f))
                    close()
                }
                drawPath(leftBow, tint, style = stroke)
                drawPath(rightBow, tint, style = stroke)
            }

            CourseNodeIconKind.Star -> {
                val p = Path().apply {
                    moveTo(x(12f), y(3f))
                    lineTo(x(14.7f), y(8.45f))
                    lineTo(x(20.7f), y(9.32f))
                    lineTo(x(16.35f), y(13.56f))
                    lineTo(x(17.38f), y(19.55f))
                    lineTo(x(12f), y(16.72f))
                    lineTo(x(6.62f), y(19.55f))
                    lineTo(x(7.65f), y(13.56f))
                    lineTo(x(3.3f), y(9.32f))
                    lineTo(x(9.3f), y(8.45f))
                    close()
                }
                drawPath(p, tint, style = stroke)
            }

            CourseNodeIconKind.Book2 -> {
                val cover = Path().apply {
                    moveTo(x(19f), y(4f))
                    lineTo(x(19f), y(20f))
                    lineTo(x(7f), y(20f))
                    cubicTo(x(5.9f), y(20f), x(5f), y(19.1f), x(5f), y(18f))
                    lineTo(x(5f), y(6f))
                    cubicTo(x(5f), y(4.9f), x(5.9f), y(4f), x(7f), y(4f))
                    close()
                }
                drawPath(cover, tint, style = stroke)
                val page = Path().apply {
                    moveTo(x(19f), y(16f))
                    lineTo(x(7f), y(16f))
                    cubicTo(x(5.9f), y(16f), x(5f), y(16.9f), x(5f), y(18f))
                }
                drawPath(page, tint, style = stroke)
                drawLine(
                    color = tint,
                    start = Offset(x(9f), y(8f)),
                    end = Offset(x(15f), y(8f)),
                    strokeWidth = strokeWidth,
                    cap = StrokeCap.Round,
                )
            }
        }
    }
}
