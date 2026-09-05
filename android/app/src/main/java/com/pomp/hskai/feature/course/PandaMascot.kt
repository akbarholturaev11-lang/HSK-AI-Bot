package com.pomp.hskai.feature.course

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.unit.dp
import com.pomp.hskai.core.design.PompColors

/**
 * Native course-path mascot ported from the Mini App `pandaChar()` proportions.
 * It intentionally uses Canvas primitives instead of a GIF/WebView so motion,
 * scale and accessibility remain native Compose behavior.
 */
@Composable
fun CoursePandaMascot(
    modifier: Modifier = Modifier,
    celebrate: Boolean = false,
) {
    val transition = rememberInfiniteTransition(label = "course-panda")
    val bob = transition.animateFloat(
        initialValue = 0f,
        targetValue = if (celebrate) -7f else -5f,
        animationSpec = infiniteRepeatable(
            animation = tween(if (celebrate) 700 else 1700),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "course-panda-bob",
    ).value
    val nod = transition.animateFloat(
        initialValue = -3f,
        targetValue = 3f,
        animationSpec = infiniteRepeatable(tween(2300), RepeatMode.Reverse),
        label = "course-panda-nod",
    ).value
    val shadowScale = transition.animateFloat(
        initialValue = 1f,
        targetValue = 0.78f,
        animationSpec = infiniteRepeatable(tween(1700), RepeatMode.Reverse),
        label = "course-panda-shadow",
    ).value

    Box(
        modifier = modifier.size(72.dp),
        contentAlignment = Alignment.Center,
    ) {
        Canvas(Modifier.size(44.dp, 10.dp).graphicsLayer {
            translationY = 28.dp.toPx()
            scaleX = shadowScale
        }) {
            drawOval(Color(0x29211D17))
        }

        Canvas(
            Modifier
                .size(72.dp)
                .graphicsLayer { translationY = bob }
        ) {
            rotate(nod, pivot = center) {
                val sx = size.width / 200f
                val sy = size.height / 210f
                fun x(v: Float) = v * sx
                fun y(v: Float) = v * sy

                val ink = PompColors.Ink
                val white = Color.White
                val scarf = PompColors.Cinnabar
                val scarfDark = PompColors.CinnabarDark

                // Body — same rounded white shell used by the Mini App mascot.
                drawOval(
                    color = white,
                    topLeft = androidx.compose.ui.geometry.Offset(x(51f), y(119f)),
                    size = androidx.compose.ui.geometry.Size(x(98f), y(89f)),
                )
                drawOval(
                    color = ink,
                    topLeft = androidx.compose.ui.geometry.Offset(x(51f), y(119f)),
                    size = androidx.compose.ui.geometry.Size(x(98f), y(89f)),
                    style = Stroke(width = x(2.5f)),
                )

                // Ears.
                drawCircle(ink, radius = x(22f), center = androidx.compose.ui.geometry.Offset(x(64f), y(58f)))
                drawCircle(ink, radius = x(22f), center = androidx.compose.ui.geometry.Offset(x(136f), y(58f)))
                drawCircle(Color(0xFF3A352F), radius = x(10f), center = androidx.compose.ui.geometry.Offset(x(64f), y(58f)))
                drawCircle(Color(0xFF3A352F), radius = x(10f), center = androidx.compose.ui.geometry.Offset(x(136f), y(58f)))

                // Face.
                drawCircle(white, radius = x(54f), center = androidx.compose.ui.geometry.Offset(x(100f), y(86f)))
                drawCircle(
                    ink,
                    radius = x(54f),
                    center = androidx.compose.ui.geometry.Offset(x(100f), y(86f)),
                    style = Stroke(width = x(2.5f)),
                )

                // Eye patches and eyes.
                drawOval(ink, androidx.compose.ui.geometry.Offset(x(64f), y(72f)), androidx.compose.ui.geometry.Size(x(30f), y(40f)))
                drawOval(ink, androidx.compose.ui.geometry.Offset(x(106f), y(72f)), androidx.compose.ui.geometry.Size(x(30f), y(40f)))
                drawCircle(white, radius = x(8f), center = androidx.compose.ui.geometry.Offset(x(79f), y(93f)))
                drawCircle(white, radius = x(8f), center = androidx.compose.ui.geometry.Offset(x(121f), y(93f)))
                drawCircle(ink, radius = x(4.2f), center = androidx.compose.ui.geometry.Offset(x(79f), y(94f)))
                drawCircle(ink, radius = x(4.2f), center = androidx.compose.ui.geometry.Offset(x(121f), y(94f)))

                // Nose and happy mouth.
                drawOval(ink, androidx.compose.ui.geometry.Offset(x(92f), y(105f)), androidx.compose.ui.geometry.Size(x(16f), y(11f)))
                drawArc(
                    color = Color(0xFF9A2F2B),
                    startAngle = 8f,
                    sweepAngle = 164f,
                    useCenter = true,
                    topLeft = androidx.compose.ui.geometry.Offset(x(86f), y(114f)),
                    size = androidx.compose.ui.geometry.Size(x(28f), y(20f)),
                )

                // Arms/paws.
                drawOval(ink, androidx.compose.ui.geometry.Offset(x(26f), y(137f)), androidx.compose.ui.geometry.Size(x(28f), y(42f)))
                drawOval(ink, androidx.compose.ui.geometry.Offset(x(146f), y(137f)), androidx.compose.ui.geometry.Size(x(28f), y(42f)))

                // Red HSK AI scarf from the Mini App panda.
                val scarfPath = androidx.compose.ui.graphics.Path().apply {
                    moveTo(x(60f), y(132f))
                    quadraticBezierTo(x(100f), y(152f), x(140f), y(132f))
                    lineTo(x(134f), y(152f))
                    quadraticBezierTo(x(100f), y(168f), x(66f), y(152f))
                    close()
                }
                drawPath(scarfPath, scarf)
                val tailPath = androidx.compose.ui.graphics.Path().apply {
                    moveTo(x(128f), y(150f))
                    lineTo(x(143f), y(178f))
                    lineTo(x(126f), y(172f))
                    lineTo(x(121f), y(156f))
                    close()
                }
                drawPath(tailPath, scarfDark)
            }
        }
    }
}
