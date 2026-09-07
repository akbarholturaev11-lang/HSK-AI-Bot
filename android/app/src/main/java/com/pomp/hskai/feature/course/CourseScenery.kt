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
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.dp

/**
 * Native, value-for-value port of the six SVG decorations from Mini App
 * `scenerySvg()`: tree, bamboo, stones, bush, pagoda and grass.
 *
 * The Mini App uses a 64x64 SVG viewBox. We keep that coordinate system and
 * only scale the final canvas to `.decor` (54px) or `.decor.sm` (44px).
 */
@Composable
internal fun MiniAppScenery(
    seed: Int,
    small: Boolean,
    modifier: Modifier = Modifier,
) {
    Canvas(modifier = modifier.size(if (small) 44.dp else 54.dp)) {
        val sx = size.width / 64f
        val sy = size.height / 64f
        fun x(v: Float) = v * sx
        fun y(v: Float) = v * sy

        when (((seed % 6) + 6) % 6) {
            0 -> { // tree
                val left = Path().apply {
                    moveTo(x(32f), y(6f))
                    lineTo(x(46f), y(28f))
                    lineTo(x(38f), y(28f))
                    lineTo(x(50f), y(46f))
                    lineTo(x(14f), y(46f))
                    lineTo(x(26f), y(28f))
                    lineTo(x(18f), y(28f))
                    close()
                }
                drawPath(left, Color(0xFF3E8E5A))
                val shade = Path().apply {
                    moveTo(x(32f), y(6f))
                    lineTo(x(46f), y(28f))
                    lineTo(x(38f), y(28f))
                    lineTo(x(50f), y(46f))
                    lineTo(x(32f), y(46f))
                    close()
                }
                drawPath(shade, Color(0xFF337A4C))
                drawRoundRect(
                    Color(0xFF8A5A2B),
                    topLeft = Offset(x(29f), y(46f)),
                    size = Size(x(6f), y(10f)),
                    cornerRadius = CornerRadius(x(2f), y(2f)),
                )
            }

            1 -> { // bamboo
                drawRoundRect(Color(0xFF57A773), Offset(x(18f), y(10f)), Size(x(6f), y(46f)), CornerRadius(x(3f), y(3f)))
                drawRoundRect(Color(0xFF6BBF8A), Offset(x(30f), y(4f)), Size(x(6f), y(52f)), CornerRadius(x(3f), y(3f)))
                drawRoundRect(Color(0xFF57A773), Offset(x(42f), y(14f)), Size(x(6f), y(42f)), CornerRadius(x(3f), y(3f)))
                val branch = Path().apply {
                    moveTo(x(36f), y(14f))
                    quadraticBezierTo(x(46f), y(6f), x(50f), y(10f))
                }
                drawPath(
                    branch,
                    Color(0xFF6BBF8A),
                    style = Stroke(width = x(3f), cap = StrokeCap.Round),
                )
            }

            2 -> { // stones
                drawOval(Color(0xFFBFB4A2), Offset(x(10f), y(39f)), Size(x(28f), y(18f)))
                drawOval(Color(0xFFD2C8B7), Offset(x(33f), y(45f)), Size(x(20f), y(12f)))
                drawOval(Color(0xFFD2C8B7), Offset(x(13f), y(39f)), Size(x(20f), y(12f)))
            }

            3 -> { // bush
                drawOval(Color(0xFF5FA97C), Offset(x(14f), y(38f)), Size(x(36f), y(20f)))
                drawOval(Color(0xFF6FBF8D), Offset(x(11f), y(36f)), Size(x(18f), y(14f)))
                drawOval(Color(0xFF6FBF8D), Offset(x(34f), y(36f)), Size(x(18f), y(14f)))
                drawCircle(Color(0xFFF2A9B5), x(2.5f), Offset(x(26f), y(44f)))
                drawCircle(Color(0xFFF2A9B5), x(2.5f), Offset(x(38f), y(47f)))
                drawCircle(Color(0xFFFFD66B), x(2.5f), Offset(x(32f), y(40f)))
            }

            4 -> { // pagoda
                val roofTop = Path().apply {
                    moveTo(x(10f), y(24f))
                    quadraticBezierTo(x(32f), y(4f), x(54f), y(24f))
                    close()
                }
                drawPath(roofTop, Color(0xFFD95A50))
                val roofShade = Path().apply {
                    moveTo(x(16f), y(24f))
                    quadraticBezierTo(x(32f), y(12f), x(48f), y(24f))
                    close()
                }
                drawPath(roofShade, Color(0xFFC0453C))
                drawRect(Color(0xFFF6E7CC), Offset(x(24f), y(24f)), Size(x(16f), y(9f)))
                val lowerRoof = Path().apply {
                    moveTo(x(12f), y(40f))
                    quadraticBezierTo(x(32f), y(26f), x(52f), y(40f))
                    close()
                }
                drawPath(lowerRoof, Color(0xFFD95A50))
                drawRect(Color(0xFFF6E7CC), Offset(x(21f), y(40f)), Size(x(22f), y(12f)))
                drawRect(Color(0xFF8A5A2B), Offset(x(29f), y(44f)), Size(x(6f), y(8f)))
            }

            else -> { // grass
                val left = Path().apply {
                    moveTo(x(20f), y(54f))
                    quadraticBezierTo(x(18f), y(42f), x(24f), y(36f))
                    quadraticBezierTo(x(26f), y(46f), x(26f), y(54f))
                    close()
                }
                drawPath(left, Color(0xFF69B586))
                val middle = Path().apply {
                    moveTo(x(30f), y(54f))
                    quadraticBezierTo(x(30f), y(38f), x(36f), y(32f))
                    quadraticBezierTo(x(38f), y(44f), x(36f), y(54f))
                    close()
                }
                drawPath(middle, Color(0xFF57A773))
                val right = Path().apply {
                    moveTo(x(42f), y(54f))
                    quadraticBezierTo(x(46f), y(44f), x(42f), y(38f))
                    quadraticBezierTo(x(38f), y(46f), x(38f), y(54f))
                    close()
                }
                drawPath(right, Color(0xFF69B586))
                drawOval(
                    Color(0xFF7CC79A).copy(alpha = 0.5f),
                    Offset(x(16f), y(51f)),
                    Size(x(32f), y(8f)),
                )
            }
        }
    }
}
