package com.pomp.hskai.feature.onboarding

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.keyframes
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/** Native port of the notebook-and-pencil Li panda from course_v3_onboarding.html. */
@Composable
internal fun OnboardingPandaMascot(
    reactionKey: Int = 0,
    motionEnabled: Boolean = true,
    happy: Boolean = true,
    modifier: Modifier = Modifier,
) {
    val transition = if (motionEnabled) {
        rememberInfiniteTransition(label = "onboarding-panda")
    } else {
        null
    }
    val breathe = if (transition != null) {
        transition.animateFloat(
            initialValue = 1f,
            targetValue = 1.02f,
            animationSpec = infiniteRepeatable(tween(1300), RepeatMode.Reverse),
            label = "onboarding-panda-breathe",
        ).value
    } else {
        1f
    }
    val blink = if (!happy && transition != null) {
        transition.animateFloat(
            initialValue = 1f,
            targetValue = 1f,
            animationSpec = infiniteRepeatable(
                animation = keyframes {
                    durationMillis = 4200
                    1f at 0
                    1f at 3780
                    0.08f at 3940
                    1f at 4050
                    1f at 4200
                },
                repeatMode = RepeatMode.Restart,
            ),
            label = "onboarding-panda-blink",
        ).value
    } else {
        1f
    }
    val nodY = remember { Animatable(0f) }
    val nodRotation = remember { Animatable(0f) }
    val armRotation = remember { Animatable(0f) }
    var pleased by remember { mutableStateOf(false) }

    LaunchedEffect(motionEnabled) {
        armRotation.snapTo(0f)
        if (!motionEnabled) return@LaunchedEffect
        delay(200)
        armRotation.animateTo(
            targetValue = 0f,
            animationSpec = keyframes {
                durationMillis = 1200
                0f at 0
                -13f at 264
                7f at 504
                -13f at 744
                7f at 984
                0f at 1200
            },
        )
    }

    LaunchedEffect(reactionKey, motionEnabled) {
        if (reactionKey <= 0) return@LaunchedEffect
        pleased = true
        if (!motionEnabled) {
            delay(800)
            pleased = false
            return@LaunchedEffect
        }
        coroutineScope {
            launch {
                nodY.snapTo(0f)
                nodY.animateTo(
                    0f,
                    keyframes {
                        durationMillis = 550
                        0f at 0
                        -3f at 193
                        1f at 358
                        0f at 550
                    },
                )
            }
            launch {
                nodRotation.snapTo(0f)
                nodRotation.animateTo(
                    0f,
                    keyframes {
                        durationMillis = 550
                        0f at 0
                        -2f at 193
                        1f at 358
                        0f at 550
                    },
                )
            }
            launch {
                armRotation.snapTo(0f)
                armRotation.animateTo(
                    0f,
                    keyframes {
                        durationMillis = 750
                        0f at 0
                        -13f at 165
                        7f at 315
                        -13f at 465
                        7f at 615
                        0f at 750
                    },
                )
            }
        }
        delay(50)
        pleased = false
    }

    Box(modifier = modifier, contentAlignment = Alignment.Center) {
        Canvas(Modifier.fillMaxSize()) {
            val sx = size.width / 100f
            val sy = size.height / 114f
            fun x(v: Float) = v * sx
            fun y(v: Float) = (v + 4f) * sy
            fun p(vx: Float, vy: Float) = androidx.compose.ui.geometry.Offset(x(vx), y(vy))
            fun oval(cx: Float, cy: Float, rx: Float, ry: Float, color: Color) {
                drawOval(
                    color = color,
                    topLeft = p(cx - rx, cy - ry),
                    size = androidx.compose.ui.geometry.Size(x(rx * 2f), y(ry) - y(-ry)),
                )
            }

            val ink = Color(0xFF2B2620)
            val face = Color(0xFFFFFDF7)
            val cream = Color(0xFFFFF4DE)
            val deep = Color(0xFFD4B27C)
            val cinnabar = Color(0xFFE04A40)
            val cinnabarDark = Color(0xFFB23530)
            val gold = Color(0xFFE9A916)

            oval(50f, 103f, 29f, 5f, ink.copy(alpha = 0.10f))

            rotate(nodRotation.value, pivot = p(50f, 54f)) {
                withTransform({
                    translate(top = (nodY.value - ((breathe - 1f) / 0.02f).coerceIn(0f, 1f)) * sy)
                    scale(scaleX = 1f, scaleY = breathe, pivot = p(50f, 103f))
                }) {
                    oval(38f, 97f, 9.5f, 6.5f, ink)
                    oval(62f, 97f, 9.5f, 6.5f, ink)

                    val leftArm = if (happy) {
                        Path().apply {
                            moveTo(x(30f), y(62f))
                            quadraticBezierTo(x(15f), y(55f), x(13f), y(39f))
                            quadraticBezierTo(x(19f), y(33f), x(25f), y(37f))
                            quadraticBezierTo(x(28f), y(48f), x(36f), y(55f))
                            close()
                        }
                    } else {
                        Path().apply {
                            moveTo(x(30f), y(64f))
                            quadraticBezierTo(x(18f), y(68f), x(17f), y(82f))
                            quadraticBezierTo(x(24f), y(87f), x(30f), y(83f))
                            quadraticBezierTo(x(31f), y(73f), x(34f), y(68f))
                            close()
                        }
                    }
                    drawPath(leftArm, ink)

                    val backBody = Path().apply {
                        moveTo(x(31f), y(96f))
                        quadraticBezierTo(x(24f), y(67f), x(40f), y(56f))
                        lineTo(x(63f), y(56f))
                        quadraticBezierTo(x(80f), y(66f), x(73f), y(96f))
                        quadraticBezierTo(x(53f), y(106f), x(31f), y(96f))
                        close()
                    }
                    drawPath(backBody, deep)

                    val body = Path().apply {
                        moveTo(x(28f), y(94f))
                        quadraticBezierTo(x(23f), y(66f), x(37f), y(58f))
                        lineTo(x(63f), y(58f))
                        quadraticBezierTo(x(77f), y(66f), x(72f), y(94f))
                        quadraticBezierTo(x(50f), y(101f), x(28f), y(94f))
                        close()
                    }
                    drawPath(body, face)
                    drawPath(body, ink, style = Stroke(width = x(3f)))
                    oval(50f, 80f, 14f, 10.5f, cream)

                    oval(27f, 15f, 12f, 12f, ink)
                    oval(73f, 15f, 12f, 12f, ink)
                    oval(27f, 15f, 5f, 5f, Color(0xFF4A443C))
                    oval(73f, 15f, 5f, 5f, Color(0xFF4A443C))

                    drawCircle(face, radius = x(30f), center = p(50f, 38f))
                    drawCircle(ink, radius = x(30f), center = p(50f, 38f), style = Stroke(width = x(3f)))

                    val sideShade = Path().apply {
                        moveTo(x(61f), y(12f))
                        quadraticBezierTo(x(79f), y(24f), x(78f), y(40f))
                        quadraticBezierTo(x(77f), y(59f), x(58f), y(67f))
                        quadraticBezierTo(x(71f), y(50f), x(61f), y(12f))
                        close()
                    }
                    drawPath(sideShade, deep)
                    oval(40f, 24f, 13f, 8f, Color.White)

                    rotate(-12f, pivot = p(38f, 35f)) { oval(38f, 35f, 9f, 12f, ink) }
                    rotate(12f, pivot = p(62f, 35f)) { oval(62f, 35f, 9f, 12f, ink) }

                    if (happy || pleased) {
                        val leftSmile = Path().apply {
                            moveTo(x(32f), y(35f))
                            quadraticBezierTo(x(38f), y(28f), x(44f), y(35f))
                        }
                        val rightSmile = Path().apply {
                            moveTo(x(56f), y(35f))
                            quadraticBezierTo(x(62f), y(28f), x(68f), y(35f))
                        }
                        drawPath(leftSmile, Color.White, style = Stroke(width = x(3f)))
                        drawPath(rightSmile, Color.White, style = Stroke(width = x(3f)))
                    } else {
                        val eyeScale = blink.coerceAtLeast(0.08f)
                        oval(38f, 34f, 4.8f, 4.8f * eyeScale, Color.White)
                        oval(62f, 34f, 4.8f, 4.8f * eyeScale, Color.White)
                        oval(38.6f, 34.8f, 2.7f, 2.7f * eyeScale, ink)
                        oval(61.4f, 34.8f, 2.7f, 2.7f * eyeScale, ink)
                        if (eyeScale > 0.4f) {
                            oval(39.8f, 33.2f, 1.1f, 1.1f, Color.White)
                            oval(62.6f, 33.2f, 1.1f, 1.1f, Color.White)
                        }
                    }

                    oval(50f, 51f, 11f, 8f, cream)
                    val nose = Path().apply {
                        moveTo(x(46f), y(46.5f))
                        quadraticBezierTo(x(50f), y(43.5f), x(54f), y(46.5f))
                        quadraticBezierTo(x(52f), y(50.5f), x(50f), y(50.5f))
                        quadraticBezierTo(x(48f), y(50.5f), x(46f), y(46.5f))
                        close()
                    }
                    drawPath(nose, ink)
                    val mouth = Path().apply {
                        moveTo(x(43f), y(53f))
                        quadraticBezierTo(x(50f), y(61f), x(57f), y(53f))
                    }
                    drawPath(mouth, ink, style = Stroke(width = x(2.6f)))
                    oval(29f, 46f, 4.8f, 3.2f, Color(0xD9F5B8C0))
                    oval(71f, 46f, 4.8f, 3.2f, Color(0xD9F5B8C0))

                    val scarf = Path().apply {
                        moveTo(x(35f), y(65f))
                        quadraticBezierTo(x(50f), y(70f), x(65f), y(65f))
                        lineTo(x(63f), y(72f))
                        quadraticBezierTo(x(50f), y(76f), x(37f), y(72f))
                        close()
                    }
                    drawPath(scarf, cinnabar)
                    val scarfTail = Path().apply {
                        moveTo(x(57f), y(71f))
                        lineTo(x(64f), y(72f))
                        lineTo(x(61f), y(84f))
                        lineTo(x(54f), y(81f))
                        close()
                    }
                    drawPath(scarfTail, cinnabarDark)

                    val notebook = Path().apply {
                        moveTo(x(14f), y(65f))
                        quadraticBezierTo(x(28f), y(61f), x(46f), y(68f))
                        lineTo(x(46f), y(99f))
                        quadraticBezierTo(x(29f), y(93f), x(14f), y(96f))
                        close()
                    }
                    drawPath(notebook, cinnabarDark)
                    val notebookSpine = Path().apply {
                        moveTo(x(43f), y(68f))
                        lineTo(x(47f), y(67f))
                        lineTo(x(47f), y(96f))
                        lineTo(x(43f), y(97f))
                        close()
                    }
                    drawPath(notebookSpine, cream)
                    drawLine(cinnabar, p(18f, 65f), p(18f, 93f), strokeWidth = x(2f))
                    drawLine(Color(0xFFF5C5B1), p(25f, 72f), p(37f, 74f), strokeWidth = x(2f))
                    drawLine(Color(0xFFF5C5B1), p(25f, 79f), p(34f, 81f), strokeWidth = x(2f))
                    val notebookHand = Path().apply {
                        moveTo(x(16f), y(76f))
                        quadraticBezierTo(x(26f), y(74f), x(28f), y(81f))
                        quadraticBezierTo(x(28f), y(88f), x(18f), y(86f))
                        lineTo(x(13f), y(82f))
                        close()
                    }
                    drawPath(notebookHand, ink)

                    rotate(armRotation.value, pivot = p(70f, 70f)) {
                        val writingArm = Path().apply {
                            moveTo(x(69f), y(73f))
                            quadraticBezierTo(x(86f), y(76f), x(91f), y(63f))
                            lineTo(x(81f), y(57f))
                            quadraticBezierTo(x(77f), y(66f), x(67f), y(60f))
                            close()
                        }
                        drawPath(writingArm, ink)

                        rotate(10f, pivot = p(85f, 50f)) {
                            val pencilTip = Path().apply {
                                moveTo(x(81f), y(32f))
                                lineTo(x(85f), y(20f))
                                lineTo(x(89f), y(32f))
                                close()
                            }
                            drawPath(pencilTip, deep)
                            val graphite = Path().apply {
                                moveTo(x(83f), y(25f))
                                lineTo(x(85f), y(20f))
                                lineTo(x(87f), y(25f))
                                close()
                            }
                            drawPath(graphite, ink)
                            drawRoundRect(
                                gold,
                                topLeft = p(81f, 32f),
                                size = androidx.compose.ui.geometry.Size(x(8f), y(33f) - y(0f)),
                                cornerRadius = androidx.compose.ui.geometry.CornerRadius(x(1f), sy),
                            )
                            drawLine(Color(0xFFFFE28F), p(84f, 35f), p(84f, 59f), strokeWidth = x(2f))
                            drawRoundRect(
                                Color(0xFFE791A6),
                                topLeft = p(81f, 63f),
                                size = androidx.compose.ui.geometry.Size(x(8f), y(8f) - y(0f)),
                                cornerRadius = androidx.compose.ui.geometry.CornerRadius(x(2f), 2f * sy),
                            )
                            drawLine(cream, p(81f, 64f), p(89f, 64f), strokeWidth = x(3f))
                        }
                        rotate(-18f, pivot = p(84f, 59f)) { oval(84f, 59f, 7f, 5.5f, ink) }
                    }
                }
            }
        }
    }
}
