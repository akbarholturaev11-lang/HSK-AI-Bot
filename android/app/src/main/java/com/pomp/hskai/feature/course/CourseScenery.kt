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
import com.pomp.hskai.core.design.PompColors

/**
 * Native port of the Mini App scenery. Light mode keeps the original values;
 * dark mode remaps the scenery into the Cosmos palette so pale stones/pagoda
 * surfaces do not flash against #002F49.
 */
@Composable
internal fun MiniAppScenery(
    seed: Int,
    small: Boolean,
    modifier: Modifier = Modifier,
) {
    val dark = PompColors.IsDark
    val treeMain = if (dark) PompColors.Jade.copy(alpha = 0.72f) else Color(0xFF3E8E5A)
    val treeShade = if (dark) PompColors.JadeSoft else Color(0xFF337A4C)
    val bambooMain = if (dark) PompColors.Jade.copy(alpha = 0.66f) else Color(0xFF57A773)
    val bambooLight = if (dark) PompColors.Jade.copy(alpha = 0.82f) else Color(0xFF6BBF8A)
    val trunk = if (dark) Color(0xFF8D6A3E) else Color(0xFF8A5A2B)
    val stoneMain = if (dark) PompColors.InkDisabled.copy(alpha = 0.42f) else Color(0xFFBFB4A2)
    val stoneLight = if (dark) PompColors.InkSecondary.copy(alpha = 0.42f) else Color(0xFFD2C8B7)
    val bushMain = if (dark) PompColors.Jade.copy(alpha = 0.58f) else Color(0xFF5FA97C)
    val bushLight = if (dark) PompColors.Jade.copy(alpha = 0.76f) else Color(0xFF6FBF8D)
    val flowerPink = if (dark) PompColors.Flame.copy(alpha = 0.82f) else Color(0xFFF2A9B5)
    val flowerGold = if (dark) PompColors.Gold.copy(alpha = 0.90f) else Color(0xFFFFD66B)
    val pagodaRoof = if (dark) PompColors.Flame.copy(alpha = 0.76f) else Color(0xFFD95A50)
    val pagodaRoofShade = if (dark) PompColors.FlameSoft else Color(0xFFC0453C)
    val pagodaWall = if (dark) PompColors.GoldSoft.copy(alpha = 0.92f) else Color(0xFFF6E7CC)
    val grassMain = if (dark) PompColors.Jade.copy(alpha = 0.62f) else Color(0xFF69B586)
    val grassShade = if (dark) PompColors.Jade.copy(alpha = 0.72f) else Color(0xFF57A773)
    val grassGlow = if (dark) PompColors.Jade.copy(alpha = 0.22f) else Color(0xFF7CC79A).copy(alpha = 0.5f)

    Canvas(modifier = modifier.size(if (small) 44.dp else 54.dp)) {
        val sx = size.width / 64f
        val sy = size.height / 64f
        fun x(v: Float) = v * sx
        fun y(v: Float) = v * sy

        when (((seed % 6) + 6) % 6) {
            0 -> {
                val left = Path().apply {
                    moveTo(x(32f), y(6f)); lineTo(x(46f), y(28f)); lineTo(x(38f), y(28f))
                    lineTo(x(50f), y(46f)); lineTo(x(14f), y(46f)); lineTo(x(26f), y(28f))
                    lineTo(x(18f), y(28f)); close()
                }
                drawPath(left, treeMain)
                val shade = Path().apply {
                    moveTo(x(32f), y(6f)); lineTo(x(46f), y(28f)); lineTo(x(38f), y(28f))
                    lineTo(x(50f), y(46f)); lineTo(x(32f), y(46f)); close()
                }
                drawPath(shade, treeShade)
                drawRoundRect(trunk, Offset(x(29f), y(46f)), Size(x(6f), y(10f)), CornerRadius(x(2f), y(2f)))
            }
            1 -> {
                drawRoundRect(bambooMain, Offset(x(18f), y(10f)), Size(x(6f), y(46f)), CornerRadius(x(3f), y(3f)))
                drawRoundRect(bambooLight, Offset(x(30f), y(4f)), Size(x(6f), y(52f)), CornerRadius(x(3f), y(3f)))
                drawRoundRect(bambooMain, Offset(x(42f), y(14f)), Size(x(6f), y(42f)), CornerRadius(x(3f), y(3f)))
                val branch = Path().apply { moveTo(x(36f), y(14f)); quadraticBezierTo(x(46f), y(6f), x(50f), y(10f)) }
                drawPath(branch, bambooLight, style = Stroke(width = x(3f), cap = StrokeCap.Round))
            }
            2 -> {
                drawOval(stoneMain, Offset(x(10f), y(39f)), Size(x(28f), y(18f)))
                drawOval(stoneLight, Offset(x(33f), y(45f)), Size(x(20f), y(12f)))
                drawOval(stoneLight, Offset(x(13f), y(39f)), Size(x(20f), y(12f)))
            }
            3 -> {
                drawOval(bushMain, Offset(x(14f), y(38f)), Size(x(36f), y(20f)))
                drawOval(bushLight, Offset(x(11f), y(36f)), Size(x(18f), y(14f)))
                drawOval(bushLight, Offset(x(34f), y(36f)), Size(x(18f), y(14f)))
                drawCircle(flowerPink, x(2.5f), Offset(x(26f), y(44f)))
                drawCircle(flowerPink, x(2.5f), Offset(x(38f), y(47f)))
                drawCircle(flowerGold, x(2.5f), Offset(x(32f), y(40f)))
            }
            4 -> {
                val roofTop = Path().apply { moveTo(x(10f), y(24f)); quadraticBezierTo(x(32f), y(4f), x(54f), y(24f)); close() }
                drawPath(roofTop, pagodaRoof)
                val roofShade = Path().apply { moveTo(x(16f), y(24f)); quadraticBezierTo(x(32f), y(12f), x(48f), y(24f)); close() }
                drawPath(roofShade, pagodaRoofShade)
                drawRect(pagodaWall, Offset(x(24f), y(24f)), Size(x(16f), y(9f)))
                val lowerRoof = Path().apply { moveTo(x(12f), y(40f)); quadraticBezierTo(x(32f), y(26f), x(52f), y(40f)); close() }
                drawPath(lowerRoof, pagodaRoof)
                drawRect(pagodaWall, Offset(x(21f), y(40f)), Size(x(22f), y(12f)))
                drawRect(trunk, Offset(x(29f), y(44f)), Size(x(6f), y(8f)))
            }
            else -> {
                val left = Path().apply {
                    moveTo(x(20f), y(54f)); quadraticBezierTo(x(18f), y(42f), x(24f), y(36f)); quadraticBezierTo(x(26f), y(46f), x(26f), y(54f)); close()
                }
                drawPath(left, grassMain)
                val middle = Path().apply {
                    moveTo(x(30f), y(54f)); quadraticBezierTo(x(30f), y(38f), x(36f), y(32f)); quadraticBezierTo(x(38f), y(44f), x(36f), y(54f)); close()
                }
                drawPath(middle, grassShade)
                val right = Path().apply {
                    moveTo(x(42f), y(54f)); quadraticBezierTo(x(46f), y(44f), x(42f), y(38f)); quadraticBezierTo(x(38f), y(46f), x(38f), y(54f)); close()
                }
                drawPath(right, grassMain)
                drawOval(grassGlow, Offset(x(16f), y(51f)), Size(x(32f), y(8f)))
            }
        }
    }
}
