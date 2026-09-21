package com.pomp.hskai.feature.lesson

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.EaseOut
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
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.launch
import kotlin.math.cos
import kotlin.math.sin
import kotlin.random.Random

/**
 * Native Android port of the Mini App HSK character pack + motion grammar.
 * Keep cast assignment and timings in sync with:
 * app/static/assets/characters/hsk-character-pack.js
 * app/static/assets/characters/hsk-character-motion.js
 */
internal enum class LessonCharacter { Panda, Dragon, Crane, Monkey, Rabbit }
internal enum class LessonCharacterMood { Idle, Correct, Wrong, Celebrate, Proud, Dismissive, OneHeart, Loading }
internal enum class LessonCharacterReaction { Pop, Jump, Laugh, Proud, Dismiss, Wrong, OneHeart, Celebrate, Loader, Exit, Land }

internal fun lessonCharacterFor(card: com.pomp.hskai.domain.model.LessonCard): LessonCharacter = when (card) {
    is com.pomp.hskai.domain.model.GrammarCard -> LessonCharacter.Crane
    is com.pomp.hskai.domain.model.SentenceBuilderCard,
    is com.pomp.hskai.domain.model.ReverseBuilderCard,
    is com.pomp.hskai.domain.model.MatchPairsCard -> LessonCharacter.Monkey
    is com.pomp.hskai.domain.model.ChoiceCard -> when {
        card.isReviewCard -> LessonCharacter.Rabbit
        card.kind == com.pomp.hskai.domain.model.ChoiceKind.GAP_FILL -> LessonCharacter.Crane
        card.kind == com.pomp.hskai.domain.model.ChoiceKind.DIALOG_CLOZE ||
            card.kind == com.pomp.hskai.domain.model.ChoiceKind.QUICK_QUIZ -> LessonCharacter.Monkey
        else -> LessonCharacter.Panda
    }
    else -> LessonCharacter.Panda
}

internal fun lessonReactionFor(
    correct: Boolean,
    hearts: Int,
    streak: Int = 0,
): LessonCharacterReaction = when {
    !correct && hearts == 1 -> LessonCharacterReaction.OneHeart
    correct && streak >= 4 -> LessonCharacterReaction.Celebrate
    correct -> LessonCharacterReaction.Jump
    else -> LessonCharacterReaction.Wrong
}

@Composable
internal fun LessonCharacterStage(
    character: LessonCharacter,
    mood: LessonCharacterMood = LessonCharacterMood.Idle,
    reaction: LessonCharacterReaction? = null,
    reactionKey: Any? = null,
    modifier: Modifier = Modifier,
) {
    val y = remember { Animatable(0f) }
    val x = remember { Animatable(0f) }
    val scale = remember { Animatable(1f) }
    val rotation = remember { Animatable(0f) }
    val alpha = remember { Animatable(1f) }
    var burst by remember { mutableStateOf(false) }
    var warning by remember { mutableStateOf(false) }

    val density = LocalDensity.current
    val idleTransition = rememberInfiniteTransition(label = "lesson-character-idle")
    val breathe by idleTransition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 1350),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "lesson-character-breathe",
    )
    val loadingWiggle by idleTransition.animateFloat(
        initialValue = -2f,
        targetValue = 2f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 900),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "lesson-character-loading-prop",
    )
    val breathing = mood == LessonCharacterMood.Idle || mood == LessonCharacterMood.Loading

    LaunchedEffect(reaction, reactionKey) {
        if (reaction == null) return@LaunchedEffect
        y.snapTo(0f); x.snapTo(0f); scale.snapTo(1f); rotation.snapTo(0f); alpha.snapTo(1f)
        burst = false; warning = false
        when (reaction) {
            LessonCharacterReaction.Pop -> {
                alpha.snapTo(0f); y.snapTo(12f); scale.snapTo(.62f)
                coroutineScope {
                    launch {
                        alpha.animateTo(
                            1f,
                            keyframes {
                                durationMillis = 560
                                0f at 0
                                1f at 325
                                1f at 560
                            },
                        )
                    }
                    launch {
                        y.animateTo(
                            0f,
                            keyframes {
                                durationMillis = 560
                                12f at 0
                                -7f at 325
                                0f at 560
                            },
                        )
                    }
                    launch {
                        scale.animateTo(
                            1f,
                            keyframes {
                                durationMillis = 560
                                .62f at 0
                                1.08f at 325
                                1f at 560
                            },
                        )
                    }
                }
            }
            LessonCharacterReaction.Jump -> coroutineScope {
                launch {
                    y.animateTo(
                        0f,
                        keyframes {
                            durationMillis = 720
                            0f at 0
                            5f at 115
                            -24f at 346
                            2f at 590
                            0f at 720
                        },
                    )
                }
                launch {
                    scale.animateTo(
                        1f,
                        keyframes {
                            durationMillis = 720
                            1f at 0
                            .88f at 115
                            1.08f at 346
                            .94f at 590
                            1f at 720
                        },
                    )
                }
            }
            LessonCharacterReaction.Laugh -> {
                rotation.animateTo(
                    0f,
                    keyframes {
                        durationMillis = 820
                        0f at 0
                        -4f at 164
                        4f at 312
                        -3f at 459
                        3f at 607
                        0f at 820
                    },
                )
            }
            LessonCharacterReaction.Proud -> coroutineScope {
                launch {
                    y.animateTo(
                        0f,
                        keyframes {
                            durationMillis = 620
                            0f at 0
                            -5f at 236
                            -4f at 446
                            0f at 620
                        },
                    )
                }
                launch {
                    rotation.animateTo(
                        0f,
                        keyframes {
                            durationMillis = 620
                            0f at 0
                            3f at 236
                            1f at 446
                            0f at 620
                        },
                    )
                }
                launch {
                    scale.animateTo(
                        1f,
                        keyframes {
                            durationMillis = 620
                            1f at 0
                            1.03f at 236
                            1.025f at 446
                            1f at 620
                        },
                    )
                }
            }
            LessonCharacterReaction.Dismiss -> coroutineScope {
                launch {
                    x.animateTo(
                        0f,
                        keyframes {
                            durationMillis = 720
                            0f at 0
                            -5f at 245
                            -3f at 504
                            0f at 720
                        },
                    )
                }
                launch {
                    rotation.animateTo(
                        0f,
                        keyframes {
                            durationMillis = 720
                            0f at 0
                            -5f at 245
                            -3f at 504
                            0f at 720
                        },
                    )
                }
            }
            LessonCharacterReaction.Wrong -> coroutineScope {
                launch {
                    x.animateTo(
                        0f,
                        keyframes {
                            durationMillis = 540
                            0f at 0
                            -7f at 124
                            6f at 232
                            -3f at 335
                            2f at 432
                            0f at 540
                        },
                    )
                }
                launch {
                    rotation.animateTo(
                        0f,
                        keyframes {
                            durationMillis = 540
                            0f at 0
                            -3f at 124
                            2f at 232
                            -1f at 335
                            0f at 540
                        },
                    )
                }
                launch {
                    scale.animateTo(
                        1f,
                        keyframes {
                            durationMillis = 540
                            1f at 0
                            .98f at 124
                            1f at 540
                        },
                    )
                }
            }
            LessonCharacterReaction.OneHeart -> {
                warning = true
                coroutineScope {
                    launch {
                        x.animateTo(
                            0f,
                            keyframes {
                                durationMillis = 980
                                0f at 0
                                -4f at 118
                                4f at 265
                                -3f at 412
                                2f at 568
                                0f at 764
                                0f at 980
                            },
                        )
                    }
                    launch {
                        scale.animateTo(
                            1f,
                            keyframes {
                                durationMillis = 980
                                1f at 0
                                .96f at 118
                                1.07f at 265
                                .98f at 412
                                1.05f at 568
                                1f at 764
                                1f at 980
                            },
                        )
                    }
                }
                warning = false
            }
            LessonCharacterReaction.Celebrate -> {
                burst = true
                coroutineScope {
                    launch {
                        y.animateTo(
                            0f,
                            keyframes {
                                durationMillis = 1080
                                0f at 0
                                6f at 130
                                -28f at 432
                                -8f at 680
                                3f at 907
                                0f at 1080
                            },
                        )
                    }
                    launch {
                        scale.animateTo(
                            1f,
                            keyframes {
                                durationMillis = 1080
                                1f at 0
                                .86f at 130
                                1.08f at 432
                                1.02f at 680
                                .93f at 907
                                1f at 1080
                            },
                        )
                    }
                    launch {
                        rotation.animateTo(
                            0f,
                            keyframes {
                                durationMillis = 1080
                                0f at 0
                                -5f at 432
                                4f at 680
                                0f at 907
                                0f at 1080
                            },
                        )
                    }
                }
                burst = false
            }
            LessonCharacterReaction.Loader -> coroutineScope {
                launch {
                    y.animateTo(
                        0f,
                        keyframes {
                            durationMillis = 1200
                            0f at 0
                            -5f at 600
                            0f at 1200
                        },
                    )
                }
                launch {
                    rotation.animateTo(
                        -1f,
                        keyframes {
                            durationMillis = 1200
                            -1f at 0
                            1.5f at 600
                            -1f at 1200
                        },
                    )
                }
                launch {
                    scale.animateTo(
                        1f,
                        keyframes {
                            durationMillis = 1200
                            1f at 0
                            1.015f at 600
                            1f at 1200
                        },
                    )
                }
            }
            LessonCharacterReaction.Exit -> coroutineScope {
                launch { y.animateTo(-24f, tween(520, easing = EaseOut)) }
                launch { scale.animateTo(.86f, tween(520, easing = EaseOut)) }
                launch { alpha.animateTo(0f, tween(520, easing = EaseOut)) }
            }
            LessonCharacterReaction.Land -> {
                alpha.snapTo(0f); y.snapTo(-110f); scale.snapTo(.88f)
                coroutineScope {
                    launch {
                        alpha.animateTo(
                            1f,
                            keyframes {
                                durationMillis = 820
                                0f at 0
                                1f at 476
                                1f at 820
                            },
                        )
                    }
                    launch {
                        y.animateTo(
                            0f,
                            keyframes {
                                durationMillis = 820
                                -110f at 0
                                7f at 476
                                -8f at 640
                                0f at 820
                            },
                        )
                    }
                    launch {
                        scale.animateTo(
                            1f,
                            keyframes {
                                durationMillis = 820
                                .88f at 0
                                .78f at 476
                                1.04f at 640
                                1f at 820
                            },
                        )
                    }
                }
            }
        }
    }

    Box(modifier = modifier, contentAlignment = Alignment.Center) {
        if (burst) LessonBurst()
        if (warning) LessonWarningRing()
        Canvas(
            Modifier.fillMaxSize().graphicsLayer {
                translationX = with(density) { x.value.dp.toPx() }
                translationY = with(density) {
                    (y.value + if (breathing) -2f * breathe else 0f).dp.toPx()
                }
                scaleX = scale.value
                scaleY = scale.value * if (breathing) 1f + .018f * breathe else 1f
                rotationZ = rotation.value
                this.alpha = alpha.value
            }
        ) {
            when (character) {
                LessonCharacter.Panda -> drawPanda(mood)
                LessonCharacter.Dragon -> drawDragon(mood)
                LessonCharacter.Crane -> drawCrane(mood)
                LessonCharacter.Monkey -> drawMonkey(mood)
                LessonCharacter.Rabbit -> drawRabbit(mood)
            }
            if (mood == LessonCharacterMood.Loading) {
                drawLoadingBook(rotation = loadingWiggle)
            }
        }
    }
}

@Composable private fun LessonBurst() {
    val dots = remember { List(20) { Triple(Random.nextFloat() * 360f, 38f + Random.nextFloat() * 34f, it) } }
    Canvas(Modifier.fillMaxSize()) {
        val colors = listOf(Color(0xFFE04A40), Color(0xFFE9A916), Color(0xFF2FA06A), Color(0xFF2E86C1), Color(0xFFF2A9B5))
        dots.forEach { (deg, radius, i) ->
            val a = Math.toRadians(deg.toDouble())
            drawCircle(colors[i % colors.size], 3.2f, center + Offset(cos(a).toFloat() * radius, sin(a).toFloat() * radius))
        }
    }
}
@Composable private fun LessonWarningRing() {
    Canvas(Modifier.fillMaxSize()) {
        drawCircle(Color(0xFFE04A40).copy(alpha=.28f), radius=size.minDimension*.43f, style=Stroke(width=3f))
    }
}

private val Ink=Color(0xFF29241F); private val Fur=Color(0xFFFFFDF7); private val Cream=Color(0xFFFFF2D9)
private fun DrawScope.sx(v:Float)=v*size.width/110f
private fun DrawScope.sy(v:Float)=v*size.height/112f
private fun DrawScope.eyes(mood:LessonCharacterMood,l:Float,r:Float,y:Float,color:Color){
    if(mood==LessonCharacterMood.Celebrate||mood==LessonCharacterMood.Correct){
        listOf(l,r).forEach{cx-> val p=Path().apply{moveTo(sx(cx-4),sy(y));quadraticBezierTo(sx(cx),sy(y-4),sx(cx+4),sy(y))};drawPath(p,color,style=Stroke(width=sx(2f),cap=StrokeCap.Round))}
    }else{
        drawCircle(color,sx(2.4f),Offset(sx(l),sy(y)));drawCircle(color,sx(2.4f),Offset(sx(r),sy(y)))
    }
}
private fun DrawScope.mouth(mood:LessonCharacterMood,cx:Float,cy:Float,color:Color){
    when(mood){
        LessonCharacterMood.Wrong,LessonCharacterMood.OneHeart-> { val p=Path().apply{moveTo(sx(cx-5),sy(cy+3));quadraticBezierTo(sx(cx),sy(cy-2),sx(cx+5),sy(cy+3))};drawPath(p,color,style=Stroke(width=sx(2f),cap=StrokeCap.Round))}
        LessonCharacterMood.Celebrate,LessonCharacterMood.Correct->drawOval(Color(0xFF9A4036),Offset(sx(cx-5),sy(cy-2)),Size(sx(10f),sy(7f)))
        else->{val p=Path().apply{moveTo(sx(cx-5),sy(cy));quadraticBezierTo(sx(cx),sy(cy+5),sx(cx+5),sy(cy))};drawPath(p,color,style=Stroke(width=sx(2f),cap=StrokeCap.Round))}
    }
}
private fun DrawScope.drawLoadingBook(rotation: Float) {
    val cx = sx(52f)
    val cy = sy(86f)
    rotate(rotation, pivot = Offset(cx, cy)) {
        val left = Path().apply {
            moveTo(sx(35f), sy(78f))
            quadraticBezierTo(sx(44f), sy(76f), sx(52f), sy(82f))
            lineTo(sx(52f), sy(95f))
            quadraticBezierTo(sx(44f), sy(89f), sx(35f), sy(91f))
            close()
        }
        val right = Path().apply {
            moveTo(sx(52f), sy(82f))
            quadraticBezierTo(sx(61f), sy(76f), sx(70f), sy(79f))
            lineTo(sx(70f), sy(92f))
            quadraticBezierTo(sx(61f), sy(89f), sx(52f), sy(95f))
            close()
        }
        drawPath(left, Color(0xFFFFF4DE))
        drawPath(right, Color(0xFFFFE7B0))
        drawPath(left, Ink, style = Stroke(width = sx(1.6f)))
        drawPath(right, Ink, style = Stroke(width = sx(1.6f)))
        drawLine(
            color = Color(0xFFE04A40),
            start = Offset(sx(52f), sy(82f)),
            end = Offset(sx(52f), sy(95f)),
            strokeWidth = sx(1.5f),
        )
    }
}

private fun DrawScope.drawPanda(m:LessonCharacterMood){
    drawOval(Ink.copy(alpha=.18f),Offset(sx(23f),sy(103f)),Size(sx(54f),sy(6f)))
    drawOval(Fur,Offset(sx(27f),sy(56f)),Size(sx(46f),sy(43f)));drawOval(Cream,Offset(sx(36f),sy(70f)),Size(sx(28f),sy(21f)))
    drawCircle(Ink,sx(12f),Offset(sx(28f),sy(18f)));drawCircle(Ink,sx(12f),Offset(sx(72f),sy(18f)))
    drawCircle(Ink,sx(30f),Offset(sx(50f),sy(40f)));drawCircle(Fur,sx(27.5f),Offset(sx(50f),sy(40f)))
    rotate(-12f,Offset(sx(38f),sy(38f))){drawOval(Ink,Offset(sx(29f),sy(26f)),Size(sx(18f),sy(24f)))}
    rotate(12f,Offset(sx(62f),sy(38f))){drawOval(Ink,Offset(sx(53f),sy(26f)),Size(sx(18f),sy(24f)))}
    eyes(m,38f,62f,38f,Color.White);drawOval(Cream,Offset(sx(39f),sy(49f)),Size(sx(22f),sy(16f)));mouth(m,50f,59f,Ink)
    val up=m==LessonCharacterMood.Celebrate||m==LessonCharacterMood.Correct
    val p1=Path().apply{moveTo(sx(34f),sy(70f));quadraticBezierTo(sx(if(up)17f else 20f),sy(if(up)43f else 87f),sx(if(up)24f else 30f),sy(if(up)38f else 91f))}
    val p2=Path().apply{moveTo(sx(66f),sy(70f));quadraticBezierTo(sx(if(up)83f else 80f),sy(if(up)43f else 87f),sx(if(up)76f else 70f),sy(if(up)38f else 91f))}
    drawPath(p1,Ink,style=Stroke(width=sx(10f),cap=StrokeCap.Round));drawPath(p2,Ink,style=Stroke(width=sx(10f),cap=StrokeCap.Round))
}
private fun DrawScope.drawDragon(m:LessonCharacterMood){
    val red=Color(0xFFD84A3F);val dark=Color(0xFFA92F2A);val gold=Color(0xFFF1BE4A)
    drawOval(Ink.copy(alpha=.18f),Offset(sx(27f),sy(104f)),Size(sx(68f),sy(6f)))
    val tail=Path().apply{moveTo(sx(79f),sy(95f));cubicTo(sx(42f),sy(107f),sx(24f),sy(89f),sx(36f),sy(72f));cubicTo(sx(48f),sy(56f),sx(80f),sy(70f),sx(74f),sy(52f))}
    drawPath(tail,dark,style=Stroke(width=sx(21f),cap=StrokeCap.Round));drawPath(tail,red,style=Stroke(width=sx(15f),cap=StrokeCap.Round))
    drawOval(red,Offset(sx(27f),sy(32f)),Size(sx(46f),sy(38f)));drawOval(Cream,Offset(sx(36f),sy(42f)),Size(sx(28f),sy(16f)))
    eyes(m,40f,60f,48f,Ink);mouth(m,50f,65f,Ink)
    val horn=Path().apply{moveTo(sx(34f),sy(34f));lineTo(sx(26f),sy(21f));lineTo(sx(40f),sy(28f));moveTo(sx(63f),sy(33f));lineTo(sx(72f),sy(19f));lineTo(sx(70f),sy(35f))}
    drawPath(horn,gold,style=Stroke(width=sx(3f),cap=StrokeCap.Round))
}
private fun DrawScope.drawCrane(m:LessonCharacterMood){
    val white=Color(0xFFFFFDF8);val gray=Color(0xFFD8D7D2);val red=Color(0xFFD74A42);val gold=Color(0xFFE8B84B)
    drawOval(Ink.copy(alpha=.18f),Offset(sx(26f),sy(104f)),Size(sx(50f),sy(5f)))
    drawOval(white,Offset(sx(29f),sy(57f)),Size(sx(46f),sy(40f)));drawOval(gray.copy(alpha=.8f),Offset(sx(51f),sy(62f)),Size(sx(20f),sy(31f)))
    val neck=Path().apply{moveTo(sx(53f),sy(64f));cubicTo(sx(44f),sy(49f),sx(46f),sy(34f),sx(52f),sy(25f));cubicTo(sx(57f),sy(17f),sx(65f),sy(18f),sx(69f),sy(25f))}
    drawPath(neck,white,style=Stroke(width=sx(13f),cap=StrokeCap.Round));drawCircle(white,sx(10f),Offset(sx(61f),sy(25f)));drawCircle(red,sx(5f),Offset(sx(61f),sy(16f)))
    eyes(m,59f,64f,25f,Ink);val beak=Path().apply{moveTo(sx(70f),sy(25f));lineTo(sx(88f),sy(29f));lineTo(sx(70f),sy(34f));close()};drawPath(beak,gold)
}
private fun DrawScope.drawMonkey(m:LessonCharacterMood){
    val fur=Color(0xFFD7A250);val dark=Color(0xFF9D6B35);val face=Color(0xFFFFE4BB)
    val tail=Path().apply{moveTo(sx(76f),sy(78f));quadraticBezierTo(sx(99f),sy(71f),sx(94f),sy(90f));quadraticBezierTo(sx(89f),sy(107f),sx(73f),sy(98f))}
    drawPath(tail,dark,style=Stroke(width=sx(9f),cap=StrokeCap.Round));drawOval(fur,Offset(sx(25f),sy(56f)),Size(sx(50f),sy(46f)))
    drawCircle(dark,sx(10f),Offset(sx(25f),sy(39f)));drawCircle(dark,sx(10f),Offset(sx(75f),sy(39f)));drawOval(fur,Offset(sx(23f),sy(18f)),Size(sx(54f),sy(50f)));drawOval(face,Offset(sx(32f),sy(30f)),Size(sx(36f),sy(34f)))
    eyes(m,42f,58f,43f,Ink);mouth(m,50f,57f,Ink)
}
private fun DrawScope.drawRabbit(m:LessonCharacterMood){
    val white=Color(0xFFF8F3E8);val depth=Color(0xFFDDD0BD);val pink=Color(0xFFE9A8B2);val jade=Color(0xFF55A47A)
    drawOval(white,Offset(sx(27f),sy(57f)),Size(sx(46f),sy(46f)));drawOval(depth,Offset(sx(52f),sy(62f)),Size(sx(18f),sy(35f)))
    rotate(-8f,Offset(sx(37f),sy(20f))){drawOval(white,Offset(sx(27f),sy(-2f)),Size(sx(20f),sy(44f)));drawOval(pink.copy(alpha=.7f),Offset(sx(33f),sy(5f)),Size(sx(8f),sy(30f)))}
    rotate(8f,Offset(sx(63f),sy(20f))){drawOval(white,Offset(sx(53f),sy(-2f)),Size(sx(20f),sy(44f)));drawOval(pink.copy(alpha=.7f),Offset(sx(59f),sy(5f)),Size(sx(8f),sy(30f)))}
    drawCircle(white,sx(27f),Offset(sx(50f),sy(48f)));eyes(m,41f,59f,47f,Ink);drawCircle(pink,sx(3f),Offset(sx(50f),sy(55f)));mouth(m,50f,62f,Ink)
    drawCircle(jade,sx(7f),Offset(sx(80f),sy(89f)))
}
