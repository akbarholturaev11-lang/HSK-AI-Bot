package com.pomp.hskai.core.design.components

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.EaseOut
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.keyframes
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
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
import androidx.compose.ui.unit.sp
import com.pomp.hskai.core.design.PompColors
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.launch
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.tan
import kotlin.random.Random

/**
 * Native Android port of the Mini App HSK character pack + motion grammar.
 *
 * This lives in `core/design` rather than in the lesson, because the lesson is
 * no longer the only place the cast appears: practice, mistake review and the
 * word drills use the very same renderer. Two copies of a character would
 * drift apart the moment one of them is retimed — the same reason
 * [HskCelebrationStage] was lifted out of the lesson in the first place.
 *
 * Keep cast assignment and timings in sync with:
 * app/static/assets/characters/hsk-character-pack.js
 * app/static/assets/characters/hsk-character-motion.js
 *
 * The cast roles come from `CAST` in that pack and are what the per-screen
 * mappers key off, so a screen picks a character by MEANING, not by taste:
 * - [HskCharacter.Panda]  熊猫     `main_coach`
 * - [HskCharacter.Dragon] 龙龙     `energy_milestone`
 * - [HskCharacter.Crane]  鹤鹤     `grammar_precision`
 * - [HskCharacter.Monkey] 悟悟     `drill_dialogue`
 * - [HskCharacter.Rabbit] 月月     `memory_warning`
 */
internal enum class HskCharacter { Panda, Dragon, Crane, Monkey, Rabbit }
internal enum class HskCharacterMood { Idle, Correct, Wrong, Celebrate, Proud, Dismissive, OneHeart, Loading }
internal enum class HskCharacterReaction { Pop, Jump, Laugh, Proud, Dismiss, Wrong, OneHeart, Celebrate, Loader, Exit, Land }

/**
 * The shared reaction ladder: a lost last heart outranks a streak, and a
 * streak outranks a plain correct answer.
 *
 * [hearts] is the lesson's currency and no other screen has it. Passing 0 —
 * which every practice screen does — simply never reaches the [OneHeart]
 * rung, so the ladder does not have to be forked per screen.
 */
internal fun hskReactionFor(
    correct: Boolean,
    hearts: Int = 0,
    streak: Int = 0,
): HskCharacterReaction = when {
    !correct && hearts == 1 -> HskCharacterReaction.OneHeart
    correct && streak >= 4 -> HskCharacterReaction.Celebrate
    correct -> HskCharacterReaction.Jump
    else -> HskCharacterReaction.Wrong
}

@Composable
internal fun HskCharacterStage(
    character: HskCharacter,
    mood: HskCharacterMood = HskCharacterMood.Idle,
    reaction: HskCharacterReaction? = null,
    reactionKey: Any? = null,
    modifier: Modifier = Modifier,
    /**
     * The red cape from the Mini App's flying pose, fluttering behind the
     * panda. Only the panda wears one, and only in a celebration.
     */
    cape: Boolean = false,
) {
    val y = remember { Animatable(0f) }
    val x = remember { Animatable(0f) }
    val scale = remember { Animatable(1f) }
    val rotation = remember { Animatable(0f) }
    val alpha = remember { Animatable(1f) }
    var burst by remember { mutableStateOf(false) }
    var warning by remember { mutableStateOf(false) }

    val density = LocalDensity.current
    // Keep the persistent coach cheap and deterministic (origin/main 7e88bc00).
    // The idle transitions ran forever on every card — including audio and
    // microphone ones — even with no reaction in flight; that is work the
    // lesson hot path does not need, and it can destabilize older or emulated
    // devices. Reactions themselves still animate: they are one-shot and only
    // run when an answer lands.
    val breathing = false
    val breathe = 0f
    val loadingWiggle = 0f
    // `.pd-cape`: one flutter every 900 ms. It exists only while a cape is
    // worn, so the lesson's everyday coach stays free of idle animation.
    val capeWave = if (cape && character == HskCharacter.Panda) {
        rememberInfiniteTransition(label = "panda-cape").animateFloat(
            initialValue = 0f,
            targetValue = 1f,
            animationSpec = infiniteRepeatable(tween(durationMillis = 900, easing = LinearEasing)),
            label = "panda-cape-wave",
        )
    } else {
        null
    }

    LaunchedEffect(reaction, reactionKey) {
        if (reaction == null) return@LaunchedEffect
        y.snapTo(0f); x.snapTo(0f); scale.snapTo(1f); rotation.snapTo(0f); alpha.snapTo(1f)
        burst = false; warning = false
        when (reaction) {
            HskCharacterReaction.Pop -> {
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
            HskCharacterReaction.Jump -> coroutineScope {
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
            HskCharacterReaction.Laugh -> {
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
            HskCharacterReaction.Proud -> coroutineScope {
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
            HskCharacterReaction.Dismiss -> coroutineScope {
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
            HskCharacterReaction.Wrong -> coroutineScope {
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
            HskCharacterReaction.OneHeart -> {
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
            HskCharacterReaction.Celebrate -> {
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
            HskCharacterReaction.Loader -> coroutineScope {
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
            HskCharacterReaction.Exit -> coroutineScope {
                launch { y.animateTo(-24f, tween(520, easing = EaseOut)) }
                launch { scale.animateTo(.86f, tween(520, easing = EaseOut)) }
                launch { alpha.animateTo(0f, tween(520, easing = EaseOut)) }
            }
            HskCharacterReaction.Land -> {
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
        if (burst) HskCharacterBurst()
        if (warning) HskCharacterWarningRing()
        Canvas(
            Modifier.fillMaxSize().graphicsLayer {
                val breathScale = if (breathing) 1f + .018f * breathe else 1f
                translationX = with(density) { x.value.dp.toPx() }
                translationY = with(density) {
                    (y.value + if (breathing) -2f * breathe else 0f).dp.toPx()
                }
                // Clamped so a mid-flight animation value can never hand the
                // compositor a degenerate transform (origin/main bf559138).
                scaleX = scale.value.coerceIn(.05f, 2f)
                scaleY = (scale.value * breathScale).coerceIn(.05f, 2f)
                rotationZ = rotation.value.coerceIn(-180f, 180f)
                this.alpha = alpha.value.coerceIn(0f, 1f)
            }
        ) {
            // A zero or non-finite box would divide straight into NaN inside
            // CharPen and hand NaN coordinates to every draw call.
            if (
                !size.width.isFinite() ||
                !size.height.isFinite() ||
                size.width <= 0f ||
                size.height <= 0f
            ) return@Canvas

            // Character art is presentation only. A malformed or unsupported
            // Canvas operation must never take the lesson process down — it
            // leaves a faint placeholder instead (origin/main bf559138).
            runCatching {
                when (character) {
                    // The book each character reads while loading sits at a
                    // different spot on each of them, so it is drawn inside the
                    // character rather than pasted at one shared coordinate.
                    HskCharacter.Panda -> drawPanda(mood, loadingWiggle, capePhase = capeWave?.value)
                    HskCharacter.Dragon -> drawDragon(mood, loadingWiggle)
                    HskCharacter.Crane -> drawCrane(mood, loadingWiggle)
                    HskCharacter.Monkey -> drawMonkey(mood, loadingWiggle)
                    HskCharacter.Rabbit -> drawRabbit(mood, loadingWiggle)
                }
            }.onFailure {
                drawCircle(
                    color = ShadowInk.copy(alpha = .10f),
                    radius = size.minDimension * .28f,
                    center = center,
                )
            }
        }
    }
}

/**
 * The coach row: character on the left, what it is saying on the right.
 *
 * It replaced a dock that put the character alone at the right edge beside a
 * tag with its name on it. That read as a sticker: the character floated in
 * empty space, and the tag said who it was rather than anything useful. Here
 * the character is attached to a sentence, and the sentence is the screen's
 * own context line — text that was already on screen, moved rather than
 * added, so nothing new needs translating into three languages.
 *
 * The notched top-left corner is the Mini App's existing speech-bubble shape
 * (`.teach-bub`, and `.fcoach-bubble` / `.pcoach-bubble` since), reused so a
 * lesson and a drill speak in the same shape on both clients. The character
 * deliberately sits outside any clipping box: a jump or a celebration would
 * otherwise be cut off at its edge.
 *
 * [text] being blank drops the bubble and leaves the character alone, so
 * pass one unless there is genuinely nothing to say.
 */
@Composable
internal fun HskCoachRow(
    character: HskCharacter,
    mood: HskCharacterMood,
    reaction: HskCharacterReaction?,
    reactionKey: Any?,
    text: String,
    modifier: Modifier = Modifier,
    showCharacter: Boolean = true,
) {
    Row(
        modifier = modifier.fillMaxWidth().padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.spacedBy(10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        // Big enough to be a character rather than an icon: at 62.dp the face
        // was a smudge and the point of having a cast was lost. The bubble
        // takes whatever is left, which is still ~200.dp on a 360.dp screen.
        if (showCharacter) {
            HskCharacterStage(
                character = character,
                mood = mood,
                reaction = reaction,
                reactionKey = reactionKey,
                modifier = Modifier.size(96.dp),
            )
        } else {
            Spacer(Modifier.size(96.dp))
        }
        if (text.isNotBlank()) HskCoachBubble(text, Modifier.weight(1f))
    }
}

/**
 * The coach standing BESIDE the question rather than above it: a tall
 * character down the left, and to its right the line it is saying with the
 * question itself underneath.
 *
 * The answers stay full width below this row — they are the widest thing on
 * the screen and squeezing them into the remaining column would cost more
 * than the character gains.
 */
@Composable
internal fun HskCoachBeside(
    character: HskCharacter,
    mood: HskCharacterMood,
    reaction: HskCharacterReaction?,
    reactionKey: Any?,
    text: String,
    modifier: Modifier = Modifier,
    showCharacter: Boolean = true,
    content: @Composable ColumnScope.() -> Unit,
) {
    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        if (showCharacter) {
            HskCharacterStage(
                character = character,
                mood = mood,
                reaction = reaction,
                reactionKey = reactionKey,
                modifier = Modifier.size(width = 120.dp, height = 152.dp),
            )
        } else {
            // The slot is held open so nothing shifts when the character
            // arrives; only the composition is skipped.
            Spacer(Modifier.size(width = 120.dp, height = 152.dp))
        }
        Column(
            modifier = Modifier.weight(1f),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            HskCoachBubble(text)
            content()
        }
    }
}

/** The coach's speech bubble on its own, for layouts that place it by hand. */
@Composable
internal fun HskCoachBubble(text: String, modifier: Modifier = Modifier) {
    if (text.isBlank()) return
    Surface(
        color = PompColors.PaperRaised,
        border = BorderStroke(1.dp, PompColors.Divider),
        shape = RoundedCornerShape(
            topStart = 4.dp,
            topEnd = 16.dp,
            bottomEnd = 16.dp,
            bottomStart = 16.dp,
        ),
        modifier = modifier,
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.bodyMedium.copy(fontSize = 13.sp),
            lineHeight = 19.sp,
            color = PompColors.InkSecondary,
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 11.dp),
        )
    }
}

@Composable private fun HskCharacterBurst() {
    val dots = remember { List(20) { Triple(Random.nextFloat() * 360f, 38f + Random.nextFloat() * 34f, it) } }
    Canvas(Modifier.fillMaxSize()) {
        val colors = listOf(Color(0xFFE04A40), Color(0xFFE9A916), Color(0xFF2FA06A), Color(0xFF2E86C1), Color(0xFFF2A9B5))
        dots.forEach { (deg, radius, i) ->
            val a = Math.toRadians(deg.toDouble())
            drawCircle(colors[i % colors.size], 3.2f, center + Offset(cos(a).toFloat() * radius, sin(a).toFloat() * radius))
        }
    }
}
@Composable private fun HskCharacterWarningRing() {
    Canvas(Modifier.fillMaxSize()) {
        drawCircle(Color(0xFFE04A40).copy(alpha=.28f), radius=size.minDimension*.43f, style=Stroke(width=3f))
    }
}

/*
 * The cast, drawn.
 *
 * This is a port of the SVG in `app/static/assets/characters/hsk-character-pack.js`,
 * and it is deliberately literal: the same coordinates, the same outlines, the
 * same viewBox per character. The first port dropped all three and the result
 * showed it — the crane and the rabbit are white animals, and without their
 * outlines they simply vanished into the cream page, while a single shared
 * viewBox of 110 squashed the panda (100 wide) by a tenth.
 *
 * Two rules keep it honest:
 *  - every character declares the viewBox its SVG declares;
 *  - a shape that is stroked in the SVG is stroked here, at the same width.
 */

/**
 * Maps the SVG's viewBox onto the Canvas.
 *
 * The scale is UNIFORM and the drawing is centred, so a character keeps its
 * proportions whatever box the layout hands it — a tall slot makes the
 * character bigger, never stretched. Getting this wrong is subtle and ugly:
 * a crane in a 118x150 box came out a tenth too long in the neck.
 */
private class CharPen(val ds: DrawScope, vw: Float, vh: Float) {
    private val s = minOf(ds.size.width / vw, ds.size.height / vh)
    private val ox = (ds.size.width - vw * s) / 2f
    private val oy = (ds.size.height - vh * s) / 2f

    /** viewBox point -> pixels (absolute). */
    fun px(v: Float) = ox + v * s
    fun py(v: Float) = oy + v * s

    /** viewBox length -> pixels. Use for sizes, deltas and stroke widths. */
    fun w(v: Float) = v * s

    fun oval(color: Color, cx: Float, cy: Float, rx: Float, ry: Float) {
        ds.drawOval(color, Offset(px(cx - rx), py(cy - ry)), Size(w(rx * 2), w(ry * 2)))
    }

    fun ovalOutlined(fill: Color, stroke: Color, width: Float, cx: Float, cy: Float, rx: Float, ry: Float) {
        oval(fill, cx, cy, rx, ry)
        ds.drawOval(
            stroke,
            Offset(px(cx - rx), py(cy - ry)),
            Size(w(rx * 2), w(ry * 2)),
            style = Stroke(width = w(width)),
        )
    }

    fun fill(path: Path, color: Color) = ds.drawPath(path, color)

    fun outline(path: Path, color: Color, width: Float, cap: StrokeCap = StrokeCap.Butt) =
        ds.drawPath(path, color, style = Stroke(width = w(width), cap = cap))

    fun stroked(path: Path, color: Color, width: Float, cap: StrokeCap = StrokeCap.Round) =
        ds.drawPath(path, color, style = Stroke(width = w(width), cap = cap))

    fun path(build: PathBuilder.() -> Unit): Path {
        val p = Path()
        PathBuilder(this, p).build()
        return p
    }

    fun rotated(degrees: Float, cx: Float, cy: Float, block: () -> Unit) {
        ds.rotate(degrees, Offset(px(cx), py(cy))) { block() }
    }
}

/**
 * Mirrors the SVG path commands so the coordinates can be copied verbatim.
 * Absolute commands go through [CharPen.px]/[CharPen.py]; relative ones are
 * lengths and go through [CharPen.w], which is why they are kept apart.
 */
private class PathBuilder(private val pen: CharPen, private val p: Path) {
    fun m(vx: Float, vy: Float) = p.moveTo(pen.px(vx), pen.py(vy))
    fun l(vx: Float, vy: Float) = p.lineTo(pen.px(vx), pen.py(vy))
    fun rl(dx: Float, dy: Float) = p.relativeLineTo(pen.w(dx), pen.w(dy))
    fun rq(dx1: Float, dy1: Float, dx2: Float, dy2: Float) =
        p.relativeQuadraticTo(pen.w(dx1), pen.w(dy1), pen.w(dx2), pen.w(dy2))
    fun c(x1: Float, y1: Float, x2: Float, y2: Float, x3: Float, y3: Float) =
        p.cubicTo(pen.px(x1), pen.py(y1), pen.px(x2), pen.py(y2), pen.px(x3), pen.py(y3))
    fun close() = p.close()
}

private val ShadowInk = Color(0xFF211D17)

private fun CharPen.shadow(cx: Float, cy: Float, rx: Float, ry: Float) {
    oval(ShadowInk.copy(alpha = .16f), cx, cy, rx, ry)
}

/**
 * Eyes, by mood — the SVG's `eyes()`, including the white catchlight that
 * makes a face look alive rather than printed.
 */
private fun CharPen.eyes(mood: HskCharacterMood, x1: Float, x2: Float, yv: Float, ink: Color) {
    when (mood) {
        HskCharacterMood.Celebrate, HskCharacterMood.Proud -> {
            listOf(x1, x2).forEach { cx ->
                stroked(path { m(cx - 5f, yv + 1f); rq(5f, -6f, 10f, 0f) }, ink, 2.7f)
            }
        }
        HskCharacterMood.Wrong, HskCharacterMood.OneHeart -> {
            oval(ink, x1, yv, 3.3f, 4.4f)
            oval(ink, x2, yv, 3.3f, 4.4f)
            listOf(x1, x2).forEach { cx ->
                stroked(path { m(cx - 5f, yv - 7f); rq(5f, -3f, 10f, 0f) }, ink, 2f)
            }
        }
        HskCharacterMood.Dismissive -> {
            stroked(path { m(x1 - 5f, yv); rl(10f, 0f) }, ink, 2.5f)
            oval(ink, x2 + 1f, yv, 3.2f, 4f)
        }
        else -> {
            oval(ink, x1, yv, 3.5f, 4.5f)
            oval(ink, x2, yv, 3.5f, 4.5f)
            oval(Color.White, x1 + 1f, yv - 1f, 1f, 1f)
            oval(Color.White, x2 + 1f, yv - 1f, 1f, 1f)
        }
    }
}

/** Mouth, by mood — the SVG's `mouth()`. */
private fun CharPen.mouth(mood: HskCharacterMood, cx: Float, cy: Float, ink: Color, accent: Color) {
    when (mood) {
        HskCharacterMood.Celebrate, HskCharacterMood.Correct ->
            fill(
                path {
                    m(cx - 7f, cy - 2f); rq(7f, 10f, 14f, 0f); rq(-7f, 4f, -14f, 0f); close()
                },
                accent,
            )
        HskCharacterMood.Wrong, HskCharacterMood.OneHeart ->
            stroked(path { m(cx - 6f, cy + 3f); rq(6f, -6f, 12f, 0f) }, ink, 2.3f)
        HskCharacterMood.Dismissive ->
            stroked(path { m(cx - 6f, cy); rq(6f, 2f, 12f, 0f) }, ink, 2.2f)
        else ->
            stroked(path { m(cx - 6f, cy); rq(6f, 5f, 12f, 0f) }, ink, 2.3f)
    }
}

private fun CharPen.loadingBook(cxv: Float, cyv: Float, rotation: Float) {
    rotated(rotation, cxv, cyv) {
        val left = path {
            m(cxv - 19f, cyv - 10f); rq(10f, -5f, 19f, 1f); rl(0f, 25f); rq(-9f, -6f, -19f, -1f); close()
        }
        val right = path {
            m(cxv + 19f, cyv - 10f); rq(-10f, -5f, -19f, 1f); rl(0f, 25f); rq(9f, -6f, 19f, -1f); close()
        }
        fill(left, Color(0xFFFFF8E8)); fill(right, Color(0xFFFFF8E8))
        outline(left, Color(0xFFA8782B), 2f); outline(right, Color(0xFFA8782B), 2f)
        stroked(path { m(cxv, cyv - 9f); rl(0f, 25f) }, Color(0xFFD5A84C), 1.5f)
    }
}

// `pdCape`: the cape sways (skewX) and breathes (scaleY) around its collar.
private val CAPE_SKEW = arrayOf(
    HskKey(0f, 5f, HskEaseInOut), HskKey(.35f, -6f, HskEaseInOut), HskKey(.7f, 3f, HskEaseInOut), HskKey(1f, 5f),
)
private val CAPE_STRETCH = arrayOf(
    HskKey(0f, 1f, HskEaseInOut), HskKey(.35f, 1.06f, HskEaseInOut), HskKey(.7f, .96f, HskEaseInOut), HskKey(1f, 1f),
)
private val CapeRed = Color(0xFFD9433C)
private val CapeFold = Color(0xFFB4342E)

/**
 * The Mini App's flying-pose cape (`pandaChar("fly")`), drawn behind the
 * body. The flutter is applied to the path's own points — skew around the
 * collar at y 60, then stretch — so the SVG coordinates stay verbatim.
 */
private fun CharPen.drawCape(skewDegrees: Float, stretch: Float) {
    val collar = 60f
    val k = tan(Math.toRadians(skewDegrees.toDouble())).toFloat() * stretch
    fun PathBuilder.from(x: Float, y: Float) = m(x + k * (y - collar), collar + stretch * (y - collar))
    fun PathBuilder.q(dx1: Float, dy1: Float, dx2: Float, dy2: Float) =
        rq(dx1 + k * dy1, stretch * dy1, dx2 + k * dy2, stretch * dy2)
    fill(
        path { from(35f, 58f); q(-19f, 24f, -13f, 46f); q(13f, -11f, 28f, -8f); q(15f, -3f, 28f, 8f); q(6f, -22f, -13f, -46f); close() },
        CapeRed,
    )
    fill(
        path { from(42f, 60f); q(-13f, 20f, -9f, 38f); q(10f, -8f, 17f, -7f); q(7f, -1f, 17f, 7f); q(4f, -18f, -9f, -38f); close() },
        CapeFold.copy(alpha = .55f),
    )
}

// --------------------------------------------------------------------------
// panda — viewBox 0 0 100 110, role main_coach
// --------------------------------------------------------------------------
private fun DrawScope.drawPanda(m: HskCharacterMood, wiggle: Float, capePhase: Float? = null) {
    val pen = CharPen(this, 100f, 110f)
    val ink = Color(0xFF29241F); val fur = Color(0xFFFFFDF7)
    val depth = Color(0xFFD9BE94); val cream = Color(0xFFFFF2D9); val accent = Color(0xFF9A4036)
    with(pen) {
        shadow(50f, 103f, 27f, 5f)
        if (capePhase != null) drawCape(hskTrack(CAPE_SKEW, capePhase), hskTrack(CAPE_STRETCH, capePhase))

        val up = m == HskCharacterMood.Celebrate || m == HskCharacterMood.Correct
        val proud = m == HskCharacterMood.Proud
        val armL = when {
            up -> path { m(35f, 69f); rq(-17f, -8f, -18f, -26f); rq(7f, -5f, 12f, 1f); rq(2f, 12f, 12f, 18f); close() }
            proud -> path { m(34f, 70f); rq(4f, 14f, 16f, 12f); rq(-5f, -8f, -11f, -15f); close() }
            else -> path { m(34f, 70f); rq(-13f, 3f, -14f, 17f); rq(7f, 5f, 13f, 0f); rq(1f, -9f, 5f, -13f); close() }
        }
        val armR = when {
            up -> path { m(65f, 69f); rq(17f, -8f, 18f, -26f); rq(-7f, -5f, -12f, 1f); rq(-2f, 12f, -12f, 18f); close() }
            proud -> path { m(66f, 70f); rq(-4f, 14f, -16f, 12f); rq(5f, -8f, 11f, -15f); close() }
            else -> path { m(66f, 70f); rq(13f, 3f, 14f, 17f); rq(-7f, 5f, -13f, 0f); rq(-1f, -9f, -5f, -13f); close() }
        }
        fill(armL, ink); fill(armR, ink)
        oval(ink, 38f, 98f, 9f, 6f); oval(ink, 62f, 98f, 9f, 6f)

        fill(path { m(31f, 96f); rq(-6f, -28f, 9f, -39f); rl(22f, 0f); rq(16f, 10f, 9f, 39f); rq(-20f, 9f, -40f, 0f); close() }, depth)
        val belly = path { m(28f, 94f); rq(-4f, -26f, 9f, -35f); rl(26f, 0f); rq(13f, 9f, 9f, 35f); rq(-22f, 8f, -44f, 0f); close() }
        fill(belly, fur); outline(belly, ink, 3f)
        oval(cream, 50f, 80f, 14f, 10f)
        oval(Color.White.copy(alpha = .75f), 43f, 71f, 9f, 4f)

        oval(ink, 28f, 18f, 12f, 12f); oval(ink, 72f, 18f, 12f, 12f)
        ovalOutlined(fur, ink, 3f, 50f, 40f, 29f, 29f)
        fill(path { m(62f, 14f); rq(17f, 13f, 16f, 28f); rq(-2f, 18f, -19f, 25f); rq(12f, -18f, 3f, -53f); close() }, depth)

        rotated(-12f, 38f, 38f) { oval(ink, 38f, 38f, 9f, 12f) }
        rotated(12f, 62f, 38f) { oval(ink, 62f, 38f, 9f, 12f) }
        eyes(m, 38f, 62f, 38f, Color.White)
        oval(cream, 50f, 53f, 11f, 8f)
        fill(path { m(46f, 49f); rq(4f, -3f, 8f, 0f); rq(-2f, 4f, -4f, 4f); rq(-2f, 0f, -4f, -4f); close() }, ink)
        mouth(m, 50f, 57f, ink, accent)
        oval(Color(0xFFF2B4BC), 30f, 50f, 4.5f, 3f); oval(Color(0xFFF2B4BC), 70f, 50f, 4.5f, 3f)
        if (m == HskCharacterMood.Loading) loadingBook(50f, 82f, wiggle)
    }
}

// --------------------------------------------------------------------------
// dragon — viewBox 0 0 110 112, role energy_milestone
// --------------------------------------------------------------------------
private fun DrawScope.drawDragon(m: HskCharacterMood, wiggle: Float) {
    val pen = CharPen(this, 110f, 112f)
    val red = Color(0xFFD84A3F); val deep = Color(0xFFA92F2A); val gold = Color(0xFFF1BE4A)
    val ink = Color(0xFF30251F); val cream = Color(0xFFFFF3D7)
    with(pen) {
        shadow(61f, 104f, 34f, 5f)
        stroked(path { m(79f, 95f); c(42f, 107f, 24f, 89f, 36f, 72f); c(48f, 56f, 80f, 70f, 74f, 52f); c(68f, 34f, 40f, 42f, 34f, 58f) }, deep, 21f)
        stroked(path { m(79f, 92f); c(46f, 102f, 31f, 87f, 41f, 74f); c(51f, 62f, 75f, 73f, 69f, 53f); c(64f, 39f, 45f, 44f, 39f, 58f) }, red, 15f)
        stroked(path { m(77f, 91f); c(49f, 97f, 39f, 86f, 46f, 76f); c(52f, 68f, 69f, 76f, 64f, 54f) }, gold.copy(alpha = .8f), 4f)

        val spikes = path {
            m(31f, 58f); rq(-12f, -9f, -8f, -22f); rl(8f, 6f); rq(-2f, -13f, 8f, -20f); rl(4f, 10f)
            rq(6f, -13f, 17f, -11f); rl(-1f, 11f); rq(14f, -6f, 20f, 4f); rl(-9f, 7f); rq(11f, 4f, 8f, 14f); rl(-12f, -2f)
        }
        fill(spikes, red); outline(spikes, deep, 2.5f)

        oval(red, 50f, 51f, 23f, 19f)
        oval(Color(0xFFF37A6D), 42f, 43f, 10f, 6f)
        val horns = path { m(34f, 34f); l(26f, 21f); l(40f, 28f); m(63f, 33f); l(72f, 19f); l(70f, 35f) }
        fill(horns, gold); outline(horns, ink, 2f)
        oval(cream, 39f, 48f, 7f, 8f); oval(cream, 61f, 48f, 7f, 8f)
        eyes(m, 40f, 60f, 48f, ink)
        oval(cream, 50f, 61f, 14f, 9f)
        oval(ink, 44f, 59f, 1.6f, 1.6f); oval(ink, 56f, 59f, 1.6f, 1.6f)
        mouth(m, 50f, 65f, ink, Color(0xFF742820))
        stroked(path { m(30f, 58f); rq(-14f, 1f, -20f, -6f) }, ink, 1.4f)
        stroked(path { m(31f, 62f); rq(-14f, 6f, -21f, 3f) }, ink, 1.4f)
        stroked(path { m(70f, 58f); rq(14f, 1f, 20f, -6f) }, ink, 1.4f)
        stroked(path { m(69f, 62f); rq(14f, 6f, 21f, 3f) }, ink, 1.4f)
        if (m == HskCharacterMood.Loading) loadingBook(57f, 87f, wiggle)
    }
}

// --------------------------------------------------------------------------
// crane — viewBox 0 0 100 112, role grammar_precision
// --------------------------------------------------------------------------
private fun DrawScope.drawCrane(m: HskCharacterMood, wiggle: Float) {
    val pen = CharPen(this, 100f, 112f)
    val white = Color(0xFFFFFDF8); val shade = Color(0xFFD8D7D2)
    val ink = Color(0xFF28231F); val red = Color(0xFFD74A42); val gold = Color(0xFFE8B84B)
    val leg = Color(0xFF9E7040)
    with(pen) {
        shadow(51f, 105f, 25f, 4f)
        // Legs and feet: without these the bird floats, and it is the first
        // thing the eye reads as "wrong" even before the missing outlines.
        stroked(path { m(50f, 93f); rq(-4f, 11f, -3f, 15f) }, leg, 3f)
        stroked(path { m(58f, 92f); rq(3f, 11f, 2f, 16f) }, leg, 3f)
        stroked(path { m(44f, 108f); rl(-10f, 0f) }, leg, 2f)
        stroked(path { m(46f, 108f); rl(8f, 0f) }, leg, 2f)
        stroked(path { m(60f, 108f); rl(-7f, 0f) }, leg, 2f)
        stroked(path { m(60f, 108f); rl(11f, 0f) }, leg, 2f)

        val celebrating = m == HskCharacterMood.Celebrate
        val wingL = if (celebrating) {
            path { m(48f, 69f); rq(-27f, -20f, -34f, -3f); rq(15f, 12f, 35f, 15f); close() }
        } else {
            path { m(42f, 71f); rq(-20f, 3f, -22f, 19f); rq(16f, 2f, 29f, -7f); close() }
        }
        val wingR = if (celebrating) {
            path { m(55f, 69f); rq(28f, -20f, 35f, -3f); rq(-16f, 12f, -36f, 15f); close() }
        } else {
            path { m(59f, 71f); rq(18f, 4f, 20f, 18f); rq(-14f, 3f, -27f, -6f); close() }
        }
        fill(wingL, white); outline(wingL, ink, 2f)
        fill(wingR, white); outline(wingR, ink, 2f)

        ovalOutlined(white, ink, 2.4f, 52f, 77f, 23f, 20f)
        fill(path { m(57f, 59f); rq(18f, 8f, 18f, 23f); rq(-8f, 14f, -24f, 15f); rq(12f, -17f, 6f, -38f); close() }, shade)

        val neck = path { m(53f, 64f); c(44f, 49f, 46f, 34f, 52f, 25f); c(57f, 17f, 65f, 18f, 69f, 25f); c(62f, 31f, 61f, 42f, 64f, 58f) }
        fill(neck, white); outline(neck, ink, 2.5f)

        ovalOutlined(white, ink, 2.4f, 61f, 25f, 10f, 10f)
        fill(path { m(55f, 17f); rq(7f, -8f, 14f, 0f) }, red)
        eyes(m, 59f, 64f, 25f, ink)
        val beak = path { m(70f, 25f); rl(18f, 4f); rl(-18f, 5f); close() }
        fill(beak, gold); outline(beak, ink, 1.7f)
        mouth(m, 62f, 33f, ink, red)
        if (m == HskCharacterMood.Loading) loadingBook(48f, 83f, wiggle)
    }
}

// --------------------------------------------------------------------------
// monkey — viewBox 0 0 105 112, role drill_dialogue
// --------------------------------------------------------------------------
private fun DrawScope.drawMonkey(m: HskCharacterMood, wiggle: Float) {
    val pen = CharPen(this, 105f, 112f)
    val fur = Color(0xFFD7A250); val deep = Color(0xFF9D6B35)
    val ink = Color(0xFF30251E); val face = Color(0xFFFFE4BB); val accent = Color(0xFF8C3E32)
    with(pen) {
        shadow(50f, 104f, 28f, 5f)
        stroked(path { m(76f, 78f); rq(23f, -7f, 18f, 12f); rq(-5f, 17f, -21f, 8f) }, deep, 9f)

        val celebrating = m == HskCharacterMood.Celebrate
        if (celebrating) {
            stroked(path { m(34f, 70f); rq(-15f, -10f, -13f, -26f) }, deep, 10f)
            stroked(path { m(66f, 70f); rq(15f, -10f, 13f, -26f) }, deep, 10f)
        } else {
            stroked(path { m(34f, 70f); rq(-12f, 6f, -10f, 18f) }, deep, 10f)
            stroked(path { m(66f, 70f); rq(12f, 6f, 10f, 18f) }, deep, 10f)
        }

        ovalOutlined(fur, ink, 2.6f, 50f, 79f, 25f, 23f)
        oval(deep, 60f, 82f, 13f, 18f)
        oval(deep, 38f, 99f, 9f, 6f); oval(deep, 62f, 99f, 9f, 6f)
        oval(deep, 25f, 39f, 10f, 10f); oval(deep, 75f, 39f, 10f, 10f)
        ovalOutlined(fur, ink, 2.6f, 50f, 43f, 27f, 25f)
        fill(
            path { m(31f, 35f); rq(19f, -22f, 38f, 0f); rq(-6f, -7f, -10f, 1f); rq(-9f, -8f, -18f, 0f); rq(-5f, -8f, -10f, -1f); close() },
            Color(0xFFF0C77D),
        )
        oval(face, 50f, 47f, 18f, 17f)
        eyes(m, 42f, 58f, 43f, ink)
        oval(ink, 50f, 51f, 4f, 3f)
        mouth(m, 50f, 57f, ink, accent)
        if (m == HskCharacterMood.Loading) loadingBook(51f, 84f, wiggle)
    }
}

// --------------------------------------------------------------------------
// rabbit — viewBox 0 0 100 112, role memory_warning
// --------------------------------------------------------------------------
private fun DrawScope.drawRabbit(m: HskCharacterMood, wiggle: Float) {
    val pen = CharPen(this, 100f, 112f)
    val white = Color(0xFFF8F3E8); val depth = Color(0xFFDDD0BD)
    val ink = Color(0xFF302A24); val pink = Color(0xFFE9A8B2)
    val jade = Color(0xFF55A47A); val accent = Color(0xFF8D4038)
    with(pen) {
        shadow(50f, 105f, 27f, 5f)
        rotated(-8f, 37f, 20f) {
            ovalOutlined(white, ink, 2.4f, 37f, 20f, 10f, 22f)
            oval(pink.copy(alpha = .7f), 37f, 20f, 4f, 15f)
        }
        rotated(8f, 63f, 20f) {
            ovalOutlined(white, ink, 2.4f, 63f, 20f, 10f, 22f)
            oval(pink.copy(alpha = .7f), 63f, 20f, 4f, 15f)
        }
        ovalOutlined(white, ink, 2.6f, 50f, 80f, 25f, 23f)
        fill(path { m(58f, 59f); rq(18f, 10f, 16f, 29f); rq(-9f, 11f, -24f, 14f); rq(12f, -20f, 8f, -43f); close() }, depth)
        ovalOutlined(white, ink, 2f, 34f, 100f, 10f, 6f)
        ovalOutlined(white, ink, 2f, 66f, 100f, 10f, 6f)
        ovalOutlined(white, ink, 2.6f, 50f, 48f, 27f, 27f)
        oval(Color.White.copy(alpha = .8f), 41f, 37f, 10f, 6f)
        eyes(m, 41f, 59f, 47f, ink)
        fill(path { m(46f, 55f); rq(4f, -3f, 8f, 0f); rq(-2f, 4f, -4f, 4f); rq(-2f, 0f, -4f, -4f); close() }, pink)
        mouth(m, 50f, 62f, ink, accent)
        val arm = path { m(69f, 71f); rq(12f, 4f, 15f, 15f); rq(-8f, 4f, -15f, -2f); close() }
        fill(arm, white); outline(arm, ink, 2f)
        oval(jade, 80f, 89f, 7f, 7f)
        stroked(path { m(80f, 82f); rl(0f, 14f) }, Color(0xFFD9F0E3).copy(alpha = .7f), 1.5f)
        stroked(path { m(73f, 89f); rl(14f, 0f) }, Color(0xFFD9F0E3).copy(alpha = .7f), 1.5f)
        if (m == HskCharacterMood.Loading) loadingBook(49f, 84f, wiggle)
    }
}
