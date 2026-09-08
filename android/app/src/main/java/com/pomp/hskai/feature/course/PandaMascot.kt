package com.pomp.hskai.feature.course

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.StartOffset
import androidx.compose.animation.core.StartOffsetType
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.keyframes
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.TransformOrigin
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.unit.dp

/**
 * 阿宝 — the panda who teaches this course.
 *
 * Not decoration: it is the same character on the path, in the lesson and on
 * the AI Voice screen, so it has to read as one person rather than a shape
 * that happens to be black and white. What makes it a character rather than a
 * mascot-shaped blob is what it does with its face and hands: a mood picks
 * the eyes, the mouth and the arms together, and the whole body breathes,
 * nods and blinks on its own timing.
 *
 * The drawing is a native port of the Mini App's `pandaChar()`, kept in the
 * same 100×106 coordinate space so the two clients show the same animal, plus
 * the red scarf that is this persona's own.
 */
enum class PandaMood {
    /** Standing, breathing, arms down. The default on the course path. */
    Happy,

    /** Arms up, eyes shut with joy, sparkles. Rewards and level-ups. */
    Celebrate,

    /** Mouth open, one arm raised as if explaining. AI Voice. */
    Talk,
}

private val INK = Color(0xFF2B2620)
private val EAR_INNER = Color(0xFF4A443C)
private val FUR = Color(0xFFFFFDF7)
private val FUR_DEEP = Color(0xFFD4B27C)
private val BODY_DEEP = Color(0xFFB98442)
private val CREAM = Color(0xFFFFF4DE)
private val MOUTH = Color(0xFF8E3A31)
private val TONGUE = Color(0xFFE07B72)
private val BLUSH = Color(0xFFF5B8C0)
private val SPARKLE = Color(0xFFE8B84B)
private val SCARF = Color(0xFFE04A40)
private val SCARF_DARK = Color(0xFFB23530)

/** The drawing's own coordinate space, matching the Mini App's viewBox. */
private const val ART_W = 100f
private const val ART_H = 106f

@Composable
fun CoursePandaMascot(
    modifier: Modifier = Modifier,
    mood: PandaMood = PandaMood.Happy,
    animationDelayMillis: Int = 0,
) {
    val transition = rememberInfiniteTransition(label = "panda")
    val delay = animationDelayMillis.coerceAtLeast(0)
    fun offset() = StartOffset(delay, StartOffsetType.Delay)

    val celebrating = mood == PandaMood.Celebrate

    // The whole body rises and falls. Faster and shallower when celebrating —
    // an excited bounce rather than a calm breath.
    val bob = transition.animateFloat(
        initialValue = 0f,
        targetValue = if (celebrating) -7f else -4f,
        animationSpec = infiniteRepeatable(
            animation = tween(if (celebrating) 620 else 1700),
            repeatMode = RepeatMode.Reverse,
            initialStartOffset = offset(),
        ),
        label = "panda-bob",
    ).value

    val nod = transition.animateFloat(
        initialValue = if (celebrating) -6f else -3f,
        targetValue = if (celebrating) 6f else 3f,
        animationSpec = infiniteRepeatable(
            animation = tween(if (celebrating) 780 else 2300),
            repeatMode = RepeatMode.Reverse,
            initialStartOffset = offset(),
        ),
        label = "panda-nod",
    ).value

    val breathe = transition.animateFloat(
        initialValue = 1f,
        targetValue = 1.025f,
        animationSpec = infiniteRepeatable(
            animation = tween(1300),
            repeatMode = RepeatMode.Reverse,
            initialStartOffset = offset(),
        ),
        label = "panda-breathe",
    ).value

    val shadow = transition.animateFloat(
        initialValue = 1f,
        targetValue = 0.80f,
        animationSpec = infiniteRepeatable(
            animation = tween(if (celebrating) 620 else 1700),
            repeatMode = RepeatMode.Reverse,
            initialStartOffset = offset(),
        ),
        label = "panda-shadow",
    ).value

    // Eyes shut for a moment, rarely. A character that never blinks reads as
    // a sticker; one that blinks constantly reads as broken.
    val blink = transition.animateFloat(
        initialValue = 1f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = keyframes {
                durationMillis = 4200
                1f at 0
                1f at 3780
                0.08f at 3940
                1f at 4060
            },
            repeatMode = RepeatMode.Restart,
            initialStartOffset = offset(),
        ),
        label = "panda-blink",
    ).value

    // Only while talking: the mouth opens and closes.
    val speak = transition.animateFloat(
        initialValue = 0.45f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(360),
            repeatMode = RepeatMode.Reverse,
            initialStartOffset = offset(),
        ),
        label = "panda-speak",
    ).value

    // O'lchamni CHAQIRUVCHI beradi. Ilgari bu yerda `.size(72.dp)` turardi va
    // u chaqiruvchining o'lchamini bosib ketardi — mukofot ekrani 104dp,
    // ovozli suhbat 130dp so'ragan bo'lsa ham panda hamma joyda 72dp chiqardi.
    Box(modifier = modifier, contentAlignment = Alignment.Center) {
        Canvas(
            Modifier
                .fillMaxSize()
                .graphicsLayer {
                    translationY = bob.dp.toPx()
                    scaleY = breathe
                    transformOrigin = TransformOrigin(0.5f, 1f)
                },
        ) {
            val unit = size.width / ART_W
            fun x(v: Float) = v * unit
            fun y(v: Float) = v * (size.height / ART_H)

            // The ground shadow does not travel with the body — it flattens as
            // the body rises, which is what sells the hop.
            drawOval(
                color = INK.copy(alpha = 0.20f),
                topLeft = Offset(x(50f - 30f * shadow), y(98f)),
                size = Size(x(60f * shadow), y(9f)),
            )

            rotate(nod, pivot = Offset(x(50f), y(95f))) {
                drawFeet(::x, ::y, mood)
                // Osilgan qo'l tanadan OLDIN — yelkasi tanaga kirib turadi.
                drawLoweredArms(::x, ::y, mood)
                drawBody(::x, ::y)
                drawScarf(::x, ::y)
                drawEars(::x, ::y)
                drawHead(::x, ::y)
                drawFace(::x, ::y, mood, blink, speak)
                // Ko'tarilgan qo'l bosh CHIZILGANDAN KEYIN — aks holda u
                // boshning ortida qolib ko'rinmaydi va quvonch yo'qoladi.
                drawRaisedArms(::x, ::y, mood)
                if (celebrating) drawSparkles(::x, ::y)
            }
        }
    }
}

private fun DrawScope.drawFeet(x: (Float) -> Float, y: (Float) -> Float, mood: PandaMood) {
    val spread = if (mood == PandaMood.Celebrate) 3f else 0f
    drawOval(INK, Offset(x(28.5f - spread), y(90.5f)), Size(x(19f), y(13f)))
    drawOval(INK, Offset(x(52.5f + spread), y(90.5f)), Size(x(19f), y(13f)))
}

private fun DrawScope.armDown(
    x: (Float) -> Float,
    y: (Float) -> Float,
    shoulderX: Float,
    sign: Float,
) {
    val path = Path().apply {
        moveTo(x(shoulderX), y(62f))
        quadraticBezierTo(x(shoulderX + 14f * sign), y(66f), x(shoulderX + 15f * sign), y(82f))
        quadraticBezierTo(x(shoulderX + 7f * sign), y(89f), x(shoulderX - 1f * sign), y(84f))
        quadraticBezierTo(x(shoulderX - 2f * sign), y(72f), x(shoulderX - 6f * sign), y(66f))
        close()
    }
    drawPath(path, INK)
    // Panjaning uchi — usiz qo'l tananing bir bo'lagiday ko'rinadi.
    drawCircle(EAR_INNER, x(3.2f), Offset(x(shoulderX + 9f * sign), y(83f)))
}

private fun DrawScope.armUp(
    x: (Float) -> Float,
    y: (Float) -> Float,
    shoulderX: Float,
    sign: Float,
) {
    // Tashqariga va yuqoriga. Ichkariga qaytsa qo'l boshning ustiga tushadi
    // va quloqchinga o'xshab qoladi — bir marta aynan shunday chiqqan.
    val path = Path().apply {
        moveTo(x(shoulderX - 4f * sign), y(68f))
        quadraticBezierTo(x(shoulderX + 12f * sign), y(64f), x(shoulderX + 20f * sign), y(46f))
        quadraticBezierTo(x(shoulderX + 24f * sign), y(34f), x(shoulderX + 21f * sign), y(29f))
        quadraticBezierTo(x(shoulderX + 13f * sign), y(33f), x(shoulderX + 11f * sign), y(48f))
        quadraticBezierTo(x(shoulderX + 7f * sign), y(60f), x(shoulderX - 4f * sign), y(68f))
        close()
    }
    drawPath(path, INK)
    drawCircle(INK, x(6f), Offset(x(shoulderX + 20f * sign), y(27f)))
    drawCircle(EAR_INNER, x(2.2f), Offset(x(shoulderX + 22f * sign), y(25f)))
}

private fun DrawScope.drawLoweredArms(
    x: (Float) -> Float,
    y: (Float) -> Float,
    mood: PandaMood,
) {
    when (mood) {
        PandaMood.Celebrate -> Unit
        // Chap qo'l tinch turadi, o'ngi ko'tariladi.
        PandaMood.Talk -> armDown(x, y, 30f, -1f)
        PandaMood.Happy -> {
            armDown(x, y, 30f, -1f)
            armDown(x, y, 70f, 1f)
        }
    }
}

private fun DrawScope.drawRaisedArms(
    x: (Float) -> Float,
    y: (Float) -> Float,
    mood: PandaMood,
) {
    when (mood) {
        PandaMood.Celebrate -> {
            armUp(x, y, 30f, -1f)
            armUp(x, y, 70f, 1f)
        }
        PandaMood.Talk -> armUp(x, y, 70f, 1f)
        PandaMood.Happy -> Unit
    }
}

private fun DrawScope.drawBody(x: (Float) -> Float, y: (Float) -> Float) {
    val shell = Path().apply {
        moveTo(x(28f), y(94f))
        quadraticBezierTo(x(23f), y(66f), x(37f), y(58f))
        lineTo(x(63f), y(58f))
        quadraticBezierTo(x(77f), y(66f), x(72f), y(94f))
        quadraticBezierTo(x(50f), y(101f), x(28f), y(94f))
        close()
    }
    // A flat white shape has no volume; the warm edge on the right is what
    // makes the belly read as round rather than as a sticker.
    val depth = Path().apply {
        moveTo(x(61f), y(61f))
        quadraticBezierTo(x(74f), y(71f), x(70f), y(92f))
        quadraticBezierTo(x(62f), y(96f), x(52f), y(97f))
        quadraticBezierTo(x(62f), y(84f), x(61f), y(61f))
        close()
    }
    drawPath(shell, FUR)
    drawPath(depth, BODY_DEEP.copy(alpha = 0.30f))
    drawPath(shell, INK, style = Stroke(width = x(3f)))
    drawOval(CREAM, Offset(x(36f), y(70f)), Size(x(28f), y(21f)))
}

/** The red scarf. It is the only thing 阿宝 wears, so it is the character. */
private fun DrawScope.drawScarf(x: (Float) -> Float, y: (Float) -> Float) {
    val band = Path().apply {
        moveTo(x(31f), y(59f))
        quadraticBezierTo(x(50f), y(70f), x(69f), y(59f))
        quadraticBezierTo(x(71f), y(66f), x(69f), y(69f))
        quadraticBezierTo(x(50f), y(79f), x(31f), y(69f))
        quadraticBezierTo(x(29f), y(66f), x(31f), y(59f))
        close()
    }
    val tail = Path().apply {
        moveTo(x(63f), y(66f))
        lineTo(x(76f), y(88f))
        lineTo(x(65f), y(87f))
        lineTo(x(58f), y(72f))
        close()
    }
    drawPath(tail, SCARF_DARK)
    drawPath(band, SCARF)
}

private fun DrawScope.drawEars(x: (Float) -> Float, y: (Float) -> Float) {
    drawCircle(INK, x(12f), Offset(x(27f), y(15f)))
    drawCircle(INK, x(12f), Offset(x(73f), y(15f)))
    drawCircle(EAR_INNER, x(5f), Offset(x(27f), y(15f)))
    drawCircle(EAR_INNER, x(5f), Offset(x(73f), y(15f)))
}

private fun DrawScope.drawHead(x: (Float) -> Float, y: (Float) -> Float) {
    drawCircle(FUR, x(30f), Offset(x(50f), y(38f)))
    val depth = Path().apply {
        moveTo(x(61f), y(12f))
        quadraticBezierTo(x(79f), y(24f), x(78f), y(40f))
        quadraticBezierTo(x(77f), y(59f), x(58f), y(67f))
        quadraticBezierTo(x(71f), y(50f), x(61f), y(12f))
        close()
    }
    drawPath(depth, FUR_DEEP.copy(alpha = 0.45f))
    drawOval(Color.White.copy(alpha = 0.75f), Offset(x(27f), y(16f)), Size(x(26f), y(16f)))
    drawCircle(INK, x(30f), Offset(x(50f), y(38f)), style = Stroke(width = x(3f)))
}

private fun DrawScope.drawFace(
    x: (Float) -> Float,
    y: (Float) -> Float,
    mood: PandaMood,
    blink: Float,
    speak: Float,
) {
    // Eye patches — the panda's whole expression hangs off their angle.
    rotate(-12f, Offset(x(38f), y(35f))) {
        drawOval(INK, Offset(x(29f), y(23f)), Size(x(18f), y(24f)))
    }
    rotate(12f, Offset(x(62f), y(35f))) {
        drawOval(INK, Offset(x(53f), y(23f)), Size(x(18f), y(24f)))
    }

    if (mood == PandaMood.Celebrate) {
        // Shut, curved upward: the face is doing the smiling, not the mouth.
        listOf(38f, 62f).forEach { cx ->
            val arc = Path().apply {
                moveTo(x(cx - 6f), y(36f))
                quadraticBezierTo(x(cx), y(29f), x(cx + 6f), y(36f))
            }
            drawPath(arc, Color.White, style = Stroke(width = x(3f), cap = StrokeCap.Round))
        }
    } else {
        val lidScale = blink.coerceAtLeast(0.08f)
        listOf(38f, 62f).forEach { cx ->
            val h = y(9.6f) * lidScale
            drawOval(Color.White, Offset(x(cx - 4.8f), y(34f) - h / 2f), Size(x(9.6f), h))
        }
        val pupilOffset = if (mood == PandaMood.Talk) 0.8f else 0f
        listOf(38.6f to 1f, 61.4f to -1f).forEach { (cx, dir) ->
            val h = y(5.4f) * lidScale
            drawOval(
                INK,
                Offset(x(cx - 2.7f + pupilOffset * dir), y(34.8f) - h / 2f),
                Size(x(5.4f), h),
            )
            if (lidScale > 0.5f) {
                drawCircle(
                    Color.White,
                    x(1.1f),
                    Offset(x(cx + 1.2f + pupilOffset * dir), y(33.2f)),
                )
            }
        }
    }

    drawOval(CREAM.copy(alpha = 0.94f), Offset(x(39f), y(43f)), Size(x(22f), y(16f)))

    val nose = Path().apply {
        moveTo(x(46f), y(46.5f))
        quadraticBezierTo(x(50f), y(43.5f), x(54f), y(46.5f))
        quadraticBezierTo(x(52f), y(50.5f), x(50f), y(50.5f))
        quadraticBezierTo(x(48f), y(50.5f), x(46f), y(46.5f))
        close()
    }
    drawPath(nose, INK)

    when (mood) {
        PandaMood.Celebrate -> {
            val open = Path().apply {
                moveTo(x(41f), y(52f))
                quadraticBezierTo(x(50f), y(63f), x(59f), y(52f))
                close()
            }
            drawPath(open, MOUTH)
            drawOval(TONGUE, Offset(x(45.5f), y(55f)), Size(x(9f), y(4.5f)))
        }
        PandaMood.Talk -> {
            val h = y(4f) + y(4f) * speak
            drawOval(MOUTH, Offset(x(44f), y(52f)), Size(x(12f), h))
            drawOval(TONGUE, Offset(x(47f), y(52f) + h * 0.45f), Size(x(6f), y(2.6f)))
        }
        PandaMood.Happy -> {
            val smile = Path().apply {
                moveTo(x(43f), y(53f))
                quadraticBezierTo(x(50f), y(58f), x(57f), y(53f))
            }
            drawPath(smile, INK, style = Stroke(width = x(2.6f), cap = StrokeCap.Round))
        }
    }

    drawOval(BLUSH.copy(alpha = 0.85f), Offset(x(24.2f), y(42.8f)), Size(x(9.6f), y(6.4f)))
    drawOval(BLUSH.copy(alpha = 0.85f), Offset(x(66.2f), y(42.8f)), Size(x(9.6f), y(6.4f)))
}

private fun DrawScope.drawSparkles(x: (Float) -> Float, y: (Float) -> Float) {
    fun star(cx: Float, cy: Float, r: Float) {
        val path = Path().apply {
            moveTo(x(cx), y(cy - r))
            lineTo(x(cx + r * 0.24f), y(cy - r * 0.24f))
            lineTo(x(cx + r), y(cy))
            lineTo(x(cx + r * 0.24f), y(cy + r * 0.24f))
            lineTo(x(cx), y(cy + r))
            lineTo(x(cx - r * 0.24f), y(cy + r * 0.24f))
            lineTo(x(cx - r), y(cy))
            lineTo(x(cx - r * 0.24f), y(cy - r * 0.24f))
            close()
        }
        drawPath(path, SPARKLE)
    }
    star(13f, 20f, 5f)
    star(88f, 13f, 4f)
    star(52f, 5f, 3.4f)
}
