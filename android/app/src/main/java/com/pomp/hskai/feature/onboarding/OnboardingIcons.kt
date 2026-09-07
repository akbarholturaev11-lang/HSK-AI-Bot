package com.pomp.hskai.feature.onboarding

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

internal enum class OnboardingIconKind {
    Back,
    Arrow,
    Check,
    HskExam,
    DailyCommunication,
    Travel,
    WorkChina,
    StudyChina,
}

@Composable
internal fun MiniAppOnboardingIcon(
    kind: OnboardingIconKind,
    tint: Color,
    modifier: Modifier = Modifier,
    size: Dp = 24.dp,
    strokeWidth: Float = 2f,
) {
    Canvas(modifier.size(size)) {
        val unitX = this.size.width / 24f
        val unitY = this.size.height / 24f
        fun x(value: Float) = value * unitX
        fun y(value: Float) = value * unitY
        fun p(px: Float, py: Float) = Offset(x(px), y(py))
        val stroke = Stroke(
            width = strokeWidth * unitX,
            cap = StrokeCap.Round,
            join = StrokeJoin.Round,
        )

        when (kind) {
            OnboardingIconKind.Back -> {
                val path = Path().apply {
                    moveTo(x(19f), y(12f))
                    lineTo(x(5f), y(12f))
                    moveTo(x(11f), y(6f))
                    lineTo(x(5f), y(12f))
                    lineTo(x(11f), y(18f))
                }
                drawPath(path, tint, style = stroke)
            }

            OnboardingIconKind.Arrow -> {
                val path = Path().apply {
                    moveTo(x(5f), y(12f))
                    lineTo(x(19f), y(12f))
                    moveTo(x(13f), y(6f))
                    lineTo(x(19f), y(12f))
                    lineTo(x(13f), y(18f))
                }
                drawPath(path, tint, style = stroke)
            }

            OnboardingIconKind.Check -> {
                val path = Path().apply {
                    moveTo(x(5f), y(12f))
                    lineTo(x(9f), y(16f))
                    lineTo(x(19f), y(6f))
                }
                drawPath(path, tint, style = stroke)
            }

            OnboardingIconKind.HskExam -> {
                drawRoundRect(
                    color = tint,
                    topLeft = p(5f, 3f),
                    size = Size(x(14f), y(18f)),
                    cornerRadius = CornerRadius(x(2f), y(2f)),
                    style = stroke,
                )
                drawLine(tint, p(9f, 7f), p(15f, 7f), strokeWidth = stroke.width, cap = StrokeCap.Round)
                drawLine(tint, p(9f, 11f), p(13f, 11f), strokeWidth = stroke.width, cap = StrokeCap.Round)
                val check = Path().apply {
                    moveTo(x(9f), y(16f))
                    lineTo(x(11f), y(18f))
                    lineTo(x(15f), y(14f))
                }
                drawPath(check, tint, style = stroke)
            }

            OnboardingIconKind.DailyCommunication -> {
                val bubble = Path().apply {
                    moveTo(x(7f), y(18f))
                    lineTo(x(4f), y(18f))
                    lineTo(x(4f), y(7f))
                    cubicTo(x(4f), y(5.34f), x(5.34f), y(4f), x(7f), y(4f))
                    lineTo(x(17f), y(4f))
                    cubicTo(x(18.66f), y(4f), x(20f), y(5.34f), x(20f), y(7f))
                    lineTo(x(20f), y(15f))
                    cubicTo(x(20f), y(16.66f), x(18.66f), y(18f), x(17f), y(18f))
                    lineTo(x(11f), y(18f))
                    lineTo(x(7f), y(21f))
                    close()
                }
                drawPath(bubble, tint, style = stroke)
                drawLine(tint, p(8f, 9f), p(16f, 9f), strokeWidth = stroke.width, cap = StrokeCap.Round)
                drawLine(tint, p(8f, 13f), p(13f, 13f), strokeWidth = stroke.width, cap = StrokeCap.Round)
            }

            OnboardingIconKind.Travel -> {
                drawCircle(tint, radius = x(9f), center = p(12f, 12f), style = stroke)
                drawOval(
                    color = tint,
                    topLeft = p(8f, 3f),
                    size = Size(x(8f), y(18f)),
                    style = stroke,
                )
                drawLine(tint, p(3f, 12f), p(21f, 12f), strokeWidth = stroke.width, cap = StrokeCap.Round)
            }

            OnboardingIconKind.WorkChina -> {
                drawRoundRect(
                    color = tint,
                    topLeft = p(3f, 7f),
                    size = Size(x(18f), y(13f)),
                    cornerRadius = CornerRadius(x(2f), y(2f)),
                    style = stroke,
                )
                val handle = Path().apply {
                    moveTo(x(8f), y(7f))
                    lineTo(x(8f), y(5f))
                    cubicTo(x(8f), y(3.9f), x(8.9f), y(3f), x(10f), y(3f))
                    lineTo(x(14f), y(3f))
                    cubicTo(x(15.1f), y(3f), x(16f), y(3.9f), x(16f), y(5f))
                    lineTo(x(16f), y(7f))
                }
                drawPath(handle, tint, style = stroke)
                drawLine(tint, p(3f, 12f), p(21f, 12f), strokeWidth = stroke.width, cap = StrokeCap.Round)
                val clasp = Path().apply {
                    moveTo(x(10f), y(12f))
                    lineTo(x(10f), y(15f))
                    lineTo(x(14f), y(15f))
                    lineTo(x(14f), y(12f))
                }
                drawPath(clasp, tint, style = stroke)
            }

            OnboardingIconKind.StudyChina -> {
                val book = Path().apply {
                    moveTo(x(12f), y(5f))
                    cubicTo(x(9f), y(3f), x(6f), y(3f), x(3f), y(4f))
                    lineTo(x(3f), y(19f))
                    cubicTo(x(6f), y(18f), x(9f), y(18f), x(12f), y(20f))
                    cubicTo(x(15f), y(18f), x(18f), y(18f), x(21f), y(19f))
                    lineTo(x(21f), y(4f))
                    cubicTo(x(18f), y(3f), x(15f), y(3f), x(12f), y(5f))
                    close()
                }
                drawPath(book, tint, style = stroke)
                drawLine(tint, p(12f, 5f), p(12f, 20f), strokeWidth = stroke.width, cap = StrokeCap.Round)
            }
        }
    }
}

internal fun goalIconKind(key: String): OnboardingIconKind = when (key) {
    "hsk_exam" -> OnboardingIconKind.HskExam
    "daily_communication" -> OnboardingIconKind.DailyCommunication
    "travel" -> OnboardingIconKind.Travel
    "work_china" -> OnboardingIconKind.WorkChina
    "study_china" -> OnboardingIconKind.StudyChina
    else -> OnboardingIconKind.Check
}
