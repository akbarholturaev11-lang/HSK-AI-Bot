package com.pomp.hskai.core.design.components

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioTrack
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.provider.Settings
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.Easing
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.requiredSize
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.State
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.geometry.RoundRect
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.CompositingStrategy
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.withTransform
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompTextStyles
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlin.math.PI
import kotlin.math.pow
import kotlin.math.roundToInt
import kotlin.math.sin
import kotlin.random.Random

/*
 * The Mini App's lesson-end clip, ported: the character's cinematic entrance,
 * the sky it flies through, the dust and the thud it lands with, the confetti,
 * the emblem, the staggered reveal, the streak flame — and the tones and the
 * vibration that go with them.
 *
 * It is a port rather than a re-imagining, so the numbers are the Mini App's
 * own. Keep them in sync with app/static/course-v3.html:
 * `beep()`, `haptic()`, `PANDA_FX`, `cinePanda()`, `skyScene()`,
 * `pandaDust()`, `stageQuake()`, `luRain()`, `.lu-emb`, `luReveal`,
 * `flameSvg()`, `miniFlameSvg()` and the `sk*` keyframes.
 */

// --------------------------------------------------------------------------
// Timing
// --------------------------------------------------------------------------

/** One keyframe: [value] at [at] (0..1 of the run), eased into the next one by [easing]. */
internal class HskKey(val at: Float, val value: Float, val easing: Easing = LinearEasing)

/**
 * Samples a keyframe track at [t] the way a CSS keyframe list does: each
 * keyframe's easing shapes the segment that starts at it. That is what lets
 * the Mini App's keyframes be copied here value for value.
 */
internal fun hskTrack(keys: Array<HskKey>, t: Float): Float {
    val first = keys.first()
    if (t <= first.at) return first.value
    for (index in 0 until keys.lastIndex) {
        val from = keys[index]
        val to = keys[index + 1]
        if (t <= to.at) {
            val span = to.at - from.at
            if (span <= 0f) return to.value
            val eased = from.easing.transform(((t - from.at) / span).coerceIn(0f, 1f))
            return from.value + (to.value - from.value) * eased
        }
    }
    return keys.last().value
}

private fun bezier(a: Float, b: Float, c: Float, d: Float) = CubicBezierEasing(a, b, c, d)

// CSS's named timing functions.
private val CssEase = bezier(.25f, .1f, .25f, 1f)
private val CssEaseIn = bezier(.42f, 0f, 1f, 1f)
private val CssEaseOut = bezier(0f, 0f, .58f, 1f)
internal val HskEaseInOut = bezier(.42f, 0f, .58f, 1f)

/** The system's "remove animations" switch — the Mini App's `prefers-reduced-motion`. */
internal fun hskMotionOff(context: Context): Boolean = runCatching {
    Settings.Global.getFloat(context.contentResolver, Settings.Global.ANIMATOR_DURATION_SCALE, 1f) == 0f
}.getOrDefault(false)

// --------------------------------------------------------------------------
// Sound and vibration
// --------------------------------------------------------------------------

/**
 * A celebration beat: the Mini App's `beep()` notes, and a vibration that
 * pulses on each note so the phone "plays" the same rhythm in the hand.
 *
 * [timings] and [amplitudes] are a [VibrationEffect.createWaveform] pattern.
 * Notes start every 90 ms, so the pulses do too.
 */
internal enum class HskCue(
    val notes: IntArray,
    val timings: LongArray,
    val amplitudes: IntArray,
) {
    /** `beep([523,659,784,1046])` + `haptic("ok")`: the lesson is done. */
    LESSON_DONE(
        notes = intArrayOf(523, 659, 784, 1046),
        timings = longArrayOf(0, 40, 50, 40, 50, 40, 50, 60),
        amplitudes = intArrayOf(0, 90, 0, 120, 0, 150, 0, 200),
    ),

    /** `beep([392,523,659,784])` + `haptic("heavy")`: the flame is lit. */
    STREAK(
        notes = intArrayOf(392, 523, 659, 784),
        timings = longArrayOf(0, 45, 45, 45, 45, 45, 45, 90),
        amplitudes = intArrayOf(0, 130, 0, 170, 0, 210, 0, 255),
    ),

    /** `beep([784,988,1175,1318])` + `haptic("ok")`: moved up the league. */
    RANK_UP(
        notes = intArrayOf(784, 988, 1175, 1318),
        timings = longArrayOf(0, 40, 50, 40, 50, 40, 50, 60),
        amplitudes = intArrayOf(0, 90, 0, 120, 0, 150, 0, 200),
    ),

    /** `beep([120,90])` + `haptic("med")`: landing from the lesson's drop. */
    LANDING(
        notes = intArrayOf(120, 90),
        timings = longArrayOf(0, 55, 35, 35),
        amplitudes = intArrayOf(0, 190, 0, 110),
    ),

    /** `beep([110,82])` + `haptic("heavy")`: landing after the flight. */
    FLY_LANDING(
        notes = intArrayOf(110, 82),
        timings = longArrayOf(0, 70, 20, 50),
        amplitudes = intArrayOf(0, 255, 0, 150),
    ),

    /** `haptic("light")` alone: the zoom-in pops into place. */
    POP(
        notes = intArrayOf(),
        timings = longArrayOf(0, 18),
        amplitudes = intArrayOf(0, 90),
    ),
}

/**
 * Plays [cue] the way the phone is set: silent mode is silent, vibrate mode
 * only vibrates, and sound goes through the media volume like a game's would.
 * Presentation only — a missing vibrator or a busy audio output is ignored.
 */
internal suspend fun hskPlayCue(context: Context, cue: HskCue) {
    val ringer = runCatching {
        context.getSystemService(AudioManager::class.java)?.ringerMode
    }.getOrNull() ?: AudioManager.RINGER_MODE_NORMAL
    if (ringer == AudioManager.RINGER_MODE_SILENT) return
    hskVibrate(context, cue)
    if (ringer == AudioManager.RINGER_MODE_NORMAL && cue.notes.isNotEmpty()) hskTone(cue.notes)
}

private fun hskVibrate(context: Context, cue: HskCue) {
    runCatching {
        val vibrator = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            context.getSystemService(VibratorManager::class.java)?.defaultVibrator
        } else {
            context.getSystemService(Vibrator::class.java)
        }
        if (vibrator != null && vibrator.hasVibrator()) {
            vibrator.vibrate(VibrationEffect.createWaveform(cue.timings, cue.amplitudes, -1))
        }
    }
}

private const val TONE_RATE = 44_100
private const val TONE_STEP = 0.09
private const val TONE_LENGTH = 0.18
private const val TONE_PEAK = 0.12
private const val TONE_FLOOR = 0.0001

private suspend fun hskTone(notes: IntArray) {
    val pcm = withContext(Dispatchers.Default) { hskSynth(notes) }
    val track = runCatching {
        AudioTrack.Builder()
            .setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_GAME)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                    .build(),
            )
            .setAudioFormat(
                AudioFormat.Builder()
                    .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                    .setSampleRate(TONE_RATE)
                    .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                    .build(),
            )
            .setTransferMode(AudioTrack.MODE_STATIC)
            .setBufferSizeInBytes(pcm.size * 2)
            .build()
    }.getOrNull() ?: return
    try {
        if (track.write(pcm, 0, pcm.size) != pcm.size) return
        if (track.state != AudioTrack.STATE_INITIALIZED) return
        track.play()
        delay(pcm.size * 1000L / TONE_RATE + 80L)
    } catch (ignored: IllegalStateException) {
        // No output right now: the clip simply plays on without its sound.
    } finally {
        runCatching { track.release() }
    }
}

/**
 * The Mini App's `beep()`, rendered to PCM: a sine per note, one every 90 ms,
 * each rising to its peak in 20 ms and dying away by 160 ms.
 */
private fun hskSynth(notes: IntArray): ShortArray {
    val total = ((notes.size - 1) * TONE_STEP + TONE_LENGTH) * TONE_RATE
    val mix = FloatArray(total.roundToInt())
    val noteSamples = (TONE_LENGTH * TONE_RATE).roundToInt()
    notes.forEachIndexed { k, frequency ->
        val start = (k * TONE_STEP * TONE_RATE).roundToInt()
        for (i in 0 until noteSamples) {
            val index = start + i
            if (index >= mix.size) break
            val t = i.toDouble() / TONE_RATE
            mix[index] += (toneGain(t) * sin(2.0 * PI * frequency * t)).toFloat()
        }
    }
    return ShortArray(mix.size) { (mix[it].coerceIn(-1f, 1f) * Short.MAX_VALUE).roundToInt().toShort() }
}

private fun toneGain(t: Double): Double = when {
    t < 0.02 -> TONE_FLOOR * (TONE_PEAK / TONE_FLOOR).pow(t / 0.02)
    t < 0.16 -> TONE_PEAK * (TONE_FLOOR / TONE_PEAK).pow((t - 0.02) / 0.14)
    else -> TONE_FLOOR
}

// --------------------------------------------------------------------------
// Cinematic entrance
// --------------------------------------------------------------------------

/**
 * How the character arrives before a celebration opens (`PANDA_FX`).
 *
 * [revealMillis] is when the scene behind it opens — the Mini App's
 * duration + 300 ms (`cinePanda`), + 260 ms for the lesson's own landing.
 * [impactAt] is the landing thud as a fraction of the run.
 */
internal enum class HskEntrance(
    val durationMillis: Int,
    val revealMillis: Int,
    val impactAt: Float,
    val cue: HskCue,
    val dust: Int,
    val dustSpread: Float,
) {
    /** Drops from above and lands in a puff of dust — a lesson is done. */
    LAND(980, 1240, .7f, HskCue.LANDING, 9, 38f),

    /** Superman: shoots up through the clouds and lands back — the streak. */
    FLY(2600, 2900, .9f, HskCue.FLY_LANDING, 14, 52f),

    /** Bursts out of the distance — moved up the league. */
    ZOOM(760, 1060, 420f / 760f, HskCue.POP, 0, 0f),
}

private val LandIn = bezier(.55f, 0f, .85f, .45f)
private val LandFall = bezier(.6f, 0f, .9f, .4f)
private val LandSquash = bezier(.2f, 1.5f, .4f, 1f)
private val LandSettle = bezier(.4f, 0f, .4f, 1f)
private val LAND_Y = arrayOf(
    HskKey(0f, -300f, LandIn), HskKey(.55f, -40f, LandFall), HskKey(.72f, 6f, LandSquash),
    HskKey(.86f, -9f, LandSettle), HskKey(1f, 0f),
)
private val LAND_SX = arrayOf(
    HskKey(0f, .82f, LandIn), HskKey(.55f, .96f, LandFall), HskKey(.72f, 1.22f, LandSquash),
    HskKey(.86f, .96f, LandSettle), HskKey(1f, 1f),
)
private val LAND_SY = arrayOf(
    HskKey(0f, .82f, LandIn), HskKey(.55f, .96f, LandFall), HskKey(.72f, .72f, LandSquash),
    HskKey(.86f, 1.06f, LandSettle), HskKey(1f, 1f),
)
private val LAND_ROT = arrayOf(HskKey(0f, -7f, LandIn), HskKey(.55f, -2f, LandFall), HskKey(.72f, 0f))
private val LAND_ALPHA = arrayOf(HskKey(0f, 0f, LandIn), HskKey(.55f, 1f))

private val FlyCrouch = bezier(.4f, 0f, .9f, .5f)
private val FlyLaunch = bezier(.1f, .95f, .3f, 1f)
private val FlyDrop = bezier(.45f, 0f, .9f, .5f)
private val FlyLand = bezier(.2f, 1.4f, .4f, 1f)
private val FLY_Y = arrayOf(
    HskKey(0f, 0f, FlyCrouch), HskKey(.09f, 16f, FlyLaunch), HskKey(.28f, -86f, CssEaseOut),
    HskKey(.46f, -104f, HskEaseInOut), HskKey(.6f, -96f, FlyDrop), HskKey(.9f, 14f, FlyLand), HskKey(1f, 0f),
)
private val FLY_SX = arrayOf(
    HskKey(0f, 1f, FlyCrouch), HskKey(.09f, 1.22f, FlyLaunch), HskKey(.28f, .95f, CssEaseOut),
    HskKey(.46f, .93f, HskEaseInOut), HskKey(.6f, .94f, FlyDrop), HskKey(.9f, 1.28f, FlyLand), HskKey(1f, 1f),
)
private val FLY_SY = arrayOf(
    HskKey(0f, 1f, FlyCrouch), HskKey(.09f, .72f, FlyLaunch), HskKey(.28f, .95f, CssEaseOut),
    HskKey(.46f, .93f, HskEaseInOut), HskKey(.6f, .94f, FlyDrop), HskKey(.9f, .68f, FlyLand), HskKey(1f, 1f),
)
private val FLY_ROT = arrayOf(
    HskKey(0f, 0f, FlyCrouch), HskKey(.09f, 0f, FlyLaunch), HskKey(.28f, -7f, CssEaseOut),
    HskKey(.46f, 5f, HskEaseInOut), HskKey(.6f, -3f, FlyDrop), HskKey(.9f, 0f, FlyLand), HskKey(1f, 0f),
)

/** Where the world rests: its ground in view (`translateY(-66.7%)`). */
private const val FLY_REST = -.667f

/** The world moves instead of the panda — the camera rises with it. */
private val FLY_WORLD = arrayOf(
    HskKey(0f, FLY_REST, bezier(.35f, 0f, .6f, .35f)), HskKey(.09f, -.66f), HskKey(.44f, -.155f, HskEaseInOut),
    HskKey(.58f, -.135f, bezier(.4f, 0f, .75f, .45f)), HskKey(.9f, FLY_REST), HskKey(1f, FLY_REST),
)
private val FLY_WIND = arrayOf(
    HskKey(0f, 0f), HskKey(.24f, .9f), HskKey(.5f, .12f), HskKey(.8f, .95f), HskKey(.92f, 0f), HskKey(1f, 0f),
)
private val FLY_SHADOW_SCALE = arrayOf(
    HskKey(0f, 1f), HskKey(.45f, .3f), HskKey(.6f, .35f), HskKey(.9f, 1f), HskKey(1f, 1f),
)
private val FLY_SHADOW_ALPHA = arrayOf(
    HskKey(0f, .55f), HskKey(.45f, .15f), HskKey(.6f, .18f), HskKey(.9f, .55f), HskKey(1f, .55f),
)

private val ZoomOut = bezier(.2f, .7f, .3f, 1f)
private val ZoomOver = bezier(.3f, 1.4f, .5f, 1f)
private val ZOOM_S = arrayOf(HskKey(0f, .12f, ZoomOut), HskKey(.62f, 1.2f, ZoomOver), HskKey(.82f, .94f), HskKey(1f, 1f))
private val ZOOM_ROT = arrayOf(HskKey(0f, -16f, ZoomOut), HskKey(.62f, 5f, ZoomOver), HskKey(.82f, -2f), HskKey(1f, 0f))
private val ZOOM_ALPHA = arrayOf(HskKey(0f, 0f, ZoomOut), HskKey(.62f, 1f))

/** `luQuake`: the landing shakes the shot. */
private val QuakeEase = bezier(.3f, .1f, .3f, 1f)
private val QUAKE = arrayOf(
    HskKey(0f, 0f, QuakeEase), HskKey(.22f, 6f, QuakeEase), HskKey(.5f, -3f, QuakeEase),
    HskKey(.76f, 2f, QuakeEase), HskKey(1f, 0f),
)

/** The character's feet in its box: the cast is drawn in a 100x110 viewBox, feet at 104. */
private const val FEET = 104f / 110f

/**
 * The close-up before a celebration: only the character is on stage, and
 * the scene behind it opens when the entrance is over. A tap skips it, as in
 * the Mini App — nobody is made to wait for a clip they have already seen.
 *
 * [onReveal] is called once, when it is time to show the scene.
 */
@Composable
internal fun HskCinematicEntrance(
    entrance: HskEntrance,
    character: HskCharacter,
    onReveal: () -> Unit,
    modifier: Modifier = Modifier,
    cape: Boolean = false,
) {
    val context = LocalContext.current
    val reveal by rememberUpdatedState(onReveal)
    val clock = remember(entrance) { Animatable(0f) }
    val quake = remember(entrance) { Animatable(0f) }
    val dustClock = remember(entrance) { Animatable(0f) }
    var landed by remember(entrance) { mutableStateOf(false) }
    var done by remember(entrance) { mutableStateOf(false) }
    val motes = remember(entrance) { hskDust(entrance) }
    val wind = remember { hskWind() }

    LaunchedEffect(entrance) {
        if (hskMotionOff(context)) {
            done = true
            reveal()
            return@LaunchedEffect
        }
        launch {
            delay((entrance.durationMillis * entrance.impactAt).toLong())
            if (done) return@launch
            landed = true
            launch { hskPlayCue(context, entrance.cue) }
            if (entrance.dust > 0) {
                launch { quake.animateTo(1f, tween(durationMillis = 420, easing = LinearEasing)) }
                dustClock.animateTo(DUST_LIFE_MS, tween(durationMillis = DUST_LIFE_MS.toInt(), easing = LinearEasing))
            }
        }
        clock.animateTo(
            entrance.revealMillis.toFloat(),
            tween(durationMillis = entrance.revealMillis, easing = LinearEasing),
        )
        if (!done) {
            done = true
            reveal()
        }
    }

    BoxWithConstraints(
        modifier = modifier
            .fillMaxSize()
            .clickable(
                interactionSource = remember { MutableInteractionSource() },
                indication = null,
            ) {
                if (!done) {
                    done = true
                    reveal()
                }
            },
    ) {
        val flying = entrance == HskEntrance.FLY
        val box = if (flying) minOf(maxWidth * .62f, 240.dp) else minOf(maxWidth * .72f, 260.dp)
        val duration = entrance.durationMillis.toFloat()
        if (flying) {
            Canvas(
                Modifier
                    .fillMaxSize()
                    .graphicsLayer { alpha = skyAlpha(clock.value, duration) },
            ) {
                drawSky(t = (clock.value / duration).coerceIn(0f, 1f), ms = clock.value, wind = wind)
            }
        }
        // While it flies the panda stands on the horizon; otherwise the shot
        // is centred (`.lu-cine` / `.levelup.cine.flying .lu-cine`).
        val top = if (flying) {
            maxHeight * ((0.9f + FLY_REST) * 3f) + 5.dp - box * FEET
        } else {
            (maxHeight - box) / 2
        }
        Box(
            modifier = Modifier
                .align(Alignment.TopCenter)
                .offset(y = top)
                .size(box)
                .graphicsLayer { translationY = hskTrack(QUAKE, quake.value).dp.toPx() },
        ) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .graphicsLayer {
                        val t = (clock.value / duration).coerceIn(0f, 1f)
                        when (entrance) {
                            HskEntrance.LAND -> {
                                translationY = hskTrack(LAND_Y, t).dp.toPx()
                                scaleX = hskTrack(LAND_SX, t)
                                scaleY = hskTrack(LAND_SY, t)
                                rotationZ = hskTrack(LAND_ROT, t)
                                alpha = hskTrack(LAND_ALPHA, t).coerceIn(0f, 1f)
                            }
                            HskEntrance.FLY -> {
                                translationY = hskTrack(FLY_Y, t).dp.toPx()
                                scaleX = hskTrack(FLY_SX, t)
                                scaleY = hskTrack(FLY_SY, t)
                                rotationZ = hskTrack(FLY_ROT, t)
                            }
                            HskEntrance.ZOOM -> {
                                val zoom = hskTrack(ZOOM_S, t).coerceAtLeast(.05f)
                                scaleX = zoom
                                scaleY = zoom
                                rotationZ = hskTrack(ZOOM_ROT, t)
                                alpha = hskTrack(ZOOM_ALPHA, t).coerceIn(0f, 1f)
                            }
                        }
                    },
            ) {
                HskCharacterStage(
                    character = character,
                    mood = HskCharacterMood.Celebrate,
                    modifier = Modifier.fillMaxSize(),
                    cape = cape,
                )
            }
            if (landed && motes.isNotEmpty()) {
                Canvas(Modifier.fillMaxSize()) {
                    drawDust(motes, dustClock.value, Offset(size.width / 2f, size.height * FEET))
                }
            }
        }
    }
}

/** The sky fades in with the shot and out just before the landing settles. */
private fun skyAlpha(ms: Float, duration: Float): Float {
    val fadeIn = (ms / 400f).coerceIn(0f, 1f)
    val fadeOut = 1f - ((ms - (duration - 260f)) / 400f).coerceIn(0f, 1f)
    return minOf(fadeIn, fadeOut)
}

// --------------------------------------------------------------------------
// The sky (`skyScene()`): a world three screens tall that slides past
// --------------------------------------------------------------------------

private val SKY_STOPS = arrayOf(
    0f to Color(0xFF08122A),
    .16f to Color(0xFF123A63),
    .4f to Color(0xFF2E7BB5),
    .64f to Color(0xFF74B9E0),
    .82f to Color(0xFFB7DFF4),
    .91f to Color(0xFFE9F5FC),
    1f to Color(0xFFF3FAFE),
)

/** left %, top %, opacity, width dp. */
private val CLOUDS = arrayOf(
    floatArrayOf(6f, 14f, .95f, 78f),
    floatArrayOf(62f, 21f, .8f, 58f),
    floatArrayOf(16f, 30f, .9f, 96f),
    floatArrayOf(68f, 38f, .75f, 66f),
    floatArrayOf(8f, 47f, .7f, 74f),
    floatArrayOf(56f, 55f, .6f, 54f),
    floatArrayOf(30f, 62f, .5f, 46f),
)

/** left % of the ground, width dp, which `_DECOR` drawing. */
private val SCENERY = arrayOf(
    floatArrayOf(3f, 78f, 0f),
    floatArrayOf(17f, 54f, 3f),
    floatArrayOf(76f, 92f, 4f),
    floatArrayOf(64f, 62f, 1f),
    floatArrayOf(90f, 58f, 0f),
    floatArrayOf(28f, 40f, 5f),
    floatArrayOf(57f, 44f, 5f),
)

private val GroundLight = Color(0xFF6FBF8D)
private val GroundMid = Color(0xFF4C9C6C)
private val GroundDark = Color(0xFF3B7F57)
private val GroundShadow = Color(0xFF183424)
private val CloudShade = Color(0xFFDCEDF8)

private class WindStreak(val x: Float, val length: Float, val delayMs: Float, val periodMs: Float)

private fun hskWind(): List<WindStreak> {
    val random = Random(26)
    return List(15) {
        WindStreak(
            x = (3f + random.nextFloat() * 94f) / 100f,
            length = 38f + random.nextFloat() * 95f,
            delayMs = random.nextFloat() * 1100f,
            periodMs = 720f + random.nextFloat() * 550f,
        )
    }
}

private fun DrawScope.drawSky(t: Float, ms: Float, wind: List<WindStreak>) {
    val w = size.width
    val h = size.height
    val worldHeight = h * 3f
    val top = hskTrack(FLY_WORLD, t) * worldHeight

    drawRect(brush = Brush.verticalGradient(*SKY_STOPS, startY = top, endY = top + worldHeight))

    for (cloud in CLOUDS) {
        val width = cloud[3].dp.toPx()
        val x = cloud[0] / 100f * w
        val y = top + cloud[1] / 100f * worldHeight
        if (y > h || y + width < 0f) continue
        drawCloud(x, y, width, cloud[2])
    }

    // The ground: the bottom tenth of the world, gently domed on top.
    val groundTop = top + worldHeight * .9f
    if (groundTop < h) {
        val left = -.04f * w
        val right = 1.04f * w
        val groundWidth = right - left
        val bottom = top + worldHeight
        val dome = worldHeight * .1f * .09f
        val ground = Path().apply {
            moveTo(left, bottom)
            lineTo(left, groundTop + dome)
            arcTo(Rect(left, groundTop, left + groundWidth * .92f, groundTop + dome * 2f), 180f, 90f, false)
            arcTo(Rect(right - groundWidth * 1.08f, groundTop, right, groundTop + dome * 2f), 270f, 90f, false)
            lineTo(right, bottom)
            close()
        }
        drawPath(
            path = ground,
            brush = Brush.verticalGradient(
                0f to GroundLight,
                .34f to GroundMid,
                1f to GroundDark,
                startY = groundTop,
                endY = bottom,
            ),
        )
        for (item in SCENERY) {
            val width = item[1].dp.toPx()
            val x = left + item[0] / 100f * groundWidth
            val itemBottom = groundTop + 6.dp.toPx()
            drawScenery(item[2].toInt(), x, itemBottom - width, width / 64f)
        }
        // The panda's shadow shrinks as it leaves the ground.
        val shadowCentre = Offset(w / 2f, groundTop + 1.dp.toPx())
        val shadowRadius = 48.dp.toPx() * hskTrack(FLY_SHADOW_SCALE, t)
        withTransform({ scale(scaleX = 1f, scaleY = 22f / 96f, pivot = shadowCentre) }) {
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(GroundShadow.copy(alpha = .5f), GroundShadow.copy(alpha = 0f)),
                    center = shadowCentre,
                    radius = shadowRadius,
                ),
                radius = shadowRadius,
                center = shadowCentre,
                alpha = hskTrack(FLY_SHADOW_ALPHA, t),
            )
        }
    }

    // Wind: white streaks rushing past on the way up and down.
    val windAlpha = hskTrack(FLY_WIND, t)
    if (windAlpha > .01f) {
        val streakWidth = 2.dp.toPx()
        for (streak in wind) {
            val local = ms - streak.delayMs
            if (local < 0f) continue
            val p = (local % streak.periodMs) / streak.periodMs
            val y = -.45f * h + p * 1.7f * h
            val length = streak.length.dp.toPx()
            drawRect(
                brush = Brush.verticalGradient(
                    colors = listOf(Color.White.copy(alpha = 0f), Color.White.copy(alpha = .9f), Color.White.copy(alpha = 0f)),
                    startY = y,
                    endY = y + length,
                ),
                topLeft = Offset(streak.x * w, y),
                size = Size(streakWidth, length),
                alpha = windAlpha,
            )
        }
    }
}

/** `cloudSvg()`, viewBox 130x62. One path, so a see-through cloud has no seams. */
private fun DrawScope.drawCloud(x: Float, y: Float, width: Float, alpha: Float) {
    val s = width / 130f
    fun box(cx: Float, cy: Float, rx: Float, ry: Float) =
        Rect(x + (cx - rx) * s, y + (cy - ry) * s, x + (cx + rx) * s, y + (cy + ry) * s)
    val body = Path().apply {
        addOval(box(40f, 38f, 27f, 18f))
        addOval(box(68f, 28f, 24f, 21f))
        addOval(box(94f, 39f, 21f, 16f))
        addRoundRect(RoundRect(Rect(x + 32f * s, y + 38f * s, x + 102f * s, y + 55f * s), CornerRadius(8.5f * s)))
    }
    drawPath(body, Color.White, alpha = alpha)
    drawOval(CloudShade, topLeft = box(66f, 55f, 40f, 5f).topLeft, size = box(66f, 55f, 40f, 5f).size, alpha = alpha)
}

/** `_DECOR`, viewBox 64x64: pine, bamboo, rocks, flower bush, red-roofed house, grass. */
private fun DrawScope.drawScenery(kind: Int, x: Float, y: Float, s: Float) {
    fun px(v: Float) = x + v * s
    fun py(v: Float) = y + v * s
    fun oval(color: Color, cx: Float, cy: Float, rx: Float, ry: Float, alpha: Float = 1f) =
        drawOval(color, topLeft = Offset(px(cx - rx), py(cy - ry)), size = Size(rx * 2f * s, ry * 2f * s), alpha = alpha)
    fun block(color: Color, left: Float, top: Float, width: Float, height: Float, radius: Float = 0f) =
        drawRoundRect(
            color,
            topLeft = Offset(px(left), py(top)),
            size = Size(width * s, height * s),
            cornerRadius = CornerRadius(radius * s),
        )
    when (kind) {
        0 -> {
            drawPath(
                Path().apply {
                    moveTo(px(32f), py(6f)); lineTo(px(46f), py(28f)); lineTo(px(38f), py(28f))
                    lineTo(px(50f), py(46f)); lineTo(px(14f), py(46f)); lineTo(px(26f), py(28f))
                    lineTo(px(18f), py(28f)); close()
                },
                Color(0xFF3E8E5A),
            )
            drawPath(
                Path().apply {
                    moveTo(px(32f), py(6f)); lineTo(px(46f), py(28f)); lineTo(px(38f), py(28f))
                    lineTo(px(50f), py(46f)); lineTo(px(32f), py(46f)); close()
                },
                Color(0xFF337A4C),
            )
            block(Color(0xFF8A5A2B), 29f, 46f, 6f, 10f, 2f)
        }
        1 -> {
            block(Color(0xFF57A773), 18f, 10f, 6f, 46f, 3f)
            block(Color(0xFF6BBF8A), 30f, 4f, 6f, 52f, 3f)
            block(Color(0xFF57A773), 42f, 14f, 6f, 42f, 3f)
            drawPath(
                Path().apply { moveTo(px(36f), py(14f)); quadraticTo(px(46f), py(6f), px(50f), py(10f)) },
                Color(0xFF6BBF8A),
                style = Stroke(width = 3f * s, cap = StrokeCap.Round),
            )
        }
        2 -> {
            oval(Color(0xFFBFB4A2), 24f, 48f, 14f, 9f)
            oval(Color(0xFFD2C8B7), 43f, 51f, 10f, 6f)
            oval(Color(0xFFD2C8B7), 23f, 45f, 10f, 6f)
        }
        3 -> {
            oval(Color(0xFF5FA97C), 32f, 48f, 18f, 10f)
            oval(Color(0xFF6FBF8D), 20f, 43f, 9f, 7f)
            oval(Color(0xFF6FBF8D), 43f, 43f, 9f, 7f)
            oval(Color(0xFFF2A9B5), 26f, 44f, 2.5f, 2.5f)
            oval(Color(0xFFF2A9B5), 38f, 47f, 2.5f, 2.5f)
            oval(Color(0xFFFFD66B), 32f, 40f, 2.5f, 2.5f)
        }
        4 -> {
            drawPath(Path().apply { moveTo(px(10f), py(24f)); quadraticTo(px(32f), py(4f), px(54f), py(24f)); close() }, Color(0xFFD95A50))
            drawPath(Path().apply { moveTo(px(16f), py(24f)); quadraticTo(px(32f), py(12f), px(48f), py(24f)); close() }, Color(0xFFC0453C))
            block(Color(0xFFF6E7CC), 24f, 24f, 16f, 9f)
            drawPath(Path().apply { moveTo(px(12f), py(40f)); quadraticTo(px(32f), py(26f), px(52f), py(40f)); close() }, Color(0xFFD95A50))
            block(Color(0xFFF6E7CC), 21f, 40f, 22f, 12f)
            block(Color(0xFF8A5A2B), 29f, 44f, 6f, 8f)
        }
        else -> {
            drawPath(
                Path().apply { moveTo(px(20f), py(54f)); quadraticTo(px(18f), py(42f), px(24f), py(36f)); quadraticTo(px(26f), py(46f), px(26f), py(54f)); close() },
                Color(0xFF69B586),
            )
            drawPath(
                Path().apply { moveTo(px(30f), py(54f)); quadraticTo(px(30f), py(38f), px(36f), py(32f)); quadraticTo(px(38f), py(44f), px(36f), py(54f)); close() },
                Color(0xFF57A773),
            )
            drawPath(
                Path().apply { moveTo(px(42f), py(54f)); quadraticTo(px(46f), py(44f), px(42f), py(38f)); quadraticTo(px(38f), py(46f), px(38f), py(54f)); close() },
                Color(0xFF69B586),
            )
            oval(Color(0xFF7CC79A), 32f, 55f, 16f, 4f, alpha = .5f)
        }
    }
}

// --------------------------------------------------------------------------
// Dust (`pandaDust()`)
// --------------------------------------------------------------------------

private const val DUST_LIFE_MS = 900f
private val DustEase = bezier(.2f, .7f, .4f, 1f)
private val DustLight = Color(0xFFD8CBB6)
private val DustDark = Color(0xFFA08F76)
private val DUST_ALPHA = arrayOf(HskKey(0f, 0f), HskKey(.32f, .85f), HskKey(1f, 0f))
private val DUST_X = arrayOf(HskKey(0f, 0f), HskKey(.32f, .55f), HskKey(1f, 1f))
private val DUST_Y = arrayOf(HskKey(0f, 0f), HskKey(.32f, 1f), HskKey(1f, .4f))

private class DustMote(val dx: Float, val dy: Float, val grow: Float, val lifeMs: Float)

private fun hskDust(entrance: HskEntrance): List<DustMote> {
    val random = Random(entrance.ordinal * 31 + 5)
    return List(entrance.dust) { index ->
        val side = if (index % 2 == 1) 1f else -1f
        DustMote(
            dx = side * (12f + random.nextFloat() * entrance.dustSpread),
            dy = -(2f + random.nextFloat() * 12f),
            grow = .6f + random.nextFloat() * 1.4f,
            lifeMs = 640f + random.nextFloat() * 260f,
        )
    }
}

private fun DrawScope.drawDust(motes: List<DustMote>, ms: Float, feet: Offset) {
    val radius = 6.5.dp.toPx()
    for (mote in motes) {
        if (ms >= mote.lifeMs) continue
        val p = DustEase.transform((ms / mote.lifeMs).coerceIn(0f, 1f))
        val grow = if (p < .32f) {
            .35f + (mote.grow - .35f) * (p / .32f)
        } else {
            mote.grow + (mote.grow * .3f) * ((p - .32f) / .68f)
        }
        val r = radius * grow
        val centre = Offset(
            feet.x + mote.dx.dp.toPx() * hskTrack(DUST_X, p),
            feet.y - radius + mote.dy.dp.toPx() * hskTrack(DUST_Y, p),
        )
        drawCircle(
            brush = Brush.radialGradient(
                colors = listOf(DustLight, DustDark),
                center = Offset(centre.x - r * .2f, centre.y - r * .3f),
                radius = r * 1.75f,
            ),
            radius = r,
            center = centre,
            alpha = hskTrack(DUST_ALPHA, p),
        )
    }
}

// --------------------------------------------------------------------------
// Confetti (`luRain()`)
// --------------------------------------------------------------------------

private val RainColors = listOf(
    Color(0xFFFF5A4E),
    Color(0xFFFFC800),
    Color(0xFF58CC02),
    Color(0xFF49C0F8),
    Color.White,
)

private class ConfettiPiece(val x: Float, val dx: Float, val spin: Float, val color: Color)

private fun hskConfetti(seed: Int): List<ConfettiPiece> {
    val random = Random(seed)
    return List(24) { index ->
        ConfettiPiece(
            x = (4f + random.nextFloat() * 92f) / 100f,
            dx = random.nextFloat() * 70f - 35f,
            spin = random.nextFloat() * 720f - 360f,
            color = RainColors[index % RainColors.size],
        )
    }
}

/**
 * One shower of confetti falling from the top of the stage. Each new [key]
 * lets another one fall; null keeps the sky clear.
 */
@Composable
internal fun HskConfettiRain(key: Any?, modifier: Modifier = Modifier) {
    if (key == null) return
    val fall = remember(key) { Animatable(0f) }
    val pieces = remember(key) { hskConfetti(key.hashCode()) }
    LaunchedEffect(key) {
        fall.animateTo(1f, tween(durationMillis = 1700, easing = LinearEasing))
    }
    Canvas(modifier.fillMaxSize()) {
        val p = fall.value
        if (p >= 1f) return@Canvas
        val move = CssEaseIn.transform(p)
        val fade = (1f - CssEase.transform(p)).coerceIn(0f, 1f)
        val travel = 760.dp.toPx()
        val pieceWidth = 9.dp.toPx()
        val pieceHeight = 13.dp.toPx()
        val corner = CornerRadius(2.dp.toPx())
        val startY = -14.dp.toPx()
        for (piece in pieces) {
            withTransform({
                translate(left = piece.x * size.width + piece.dx.dp.toPx() * move, top = startY + travel * move)
                rotate(degrees = piece.spin * move, pivot = Offset(pieceWidth / 2f, pieceHeight / 2f))
            }) {
                drawRoundRect(color = piece.color, size = Size(pieceWidth, pieceHeight), cornerRadius = corner, alpha = fade)
            }
        }
    }
}

// --------------------------------------------------------------------------
// Emblem and reveal
// --------------------------------------------------------------------------

/** `.lu-emb`: the cinnabar tile with a gold rim that pops in at the top of the scene. */
@Composable
internal fun HskCelebrationEmblem(glyph: String, modifier: Modifier = Modifier) {
    val pop = remember(glyph) { Animatable(0f) }
    LaunchedEffect(glyph) {
        delay(60)
        pop.animateTo(1f, tween(durationMillis = 500, easing = bezier(.2f, 1.5f, .4f, 1f)))
    }
    val shape = RoundedCornerShape(34.dp)
    Box(
        modifier = modifier
            .size(138.dp)
            .graphicsLayer {
                scaleX = pop.value
                scaleY = pop.value
            }
            .clip(shape)
            .background(PompColors.LightCinnabar)
            .border(3.dp, PompColors.LightGold, shape),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = glyph,
            style = PompTextStyles.hanziLarge.copy(
                fontSize = 58.sp,
                lineHeight = 64.sp,
                fontWeight = FontWeight.Medium,
            ),
            color = Color.White,
        )
    }
}

/**
 * `luReveal`: a line of the scene rises 16 dp into place as it fades in.
 * The Mini App staggers them 0 / 90 / 170 / 250 / 320 ms.
 */
@Composable
internal fun HskReveal(
    delayMillis: Int,
    modifier: Modifier = Modifier,
    content: @Composable () -> Unit,
) {
    val progress = remember { Animatable(0f) }
    LaunchedEffect(Unit) {
        delay(delayMillis.toLong())
        progress.animateTo(1f, tween(durationMillis = 500, easing = CssEase))
    }
    Box(
        modifier = modifier.graphicsLayer {
            alpha = progress.value
            translationY = (1f - progress.value) * 16.dp.toPx()
            // No offscreen layer: that would clip whatever a line lets hang
            // over its edge while it fades — the panda by the flame, the glow.
            compositingStrategy = CompositingStrategy.ModulateAlpha
        },
    ) {
        content()
    }
}

/** A plain fade-in — the stage's button and rays come back this way after the close-up. */
@Composable
internal fun HskFadeIn(
    durationMillis: Int,
    modifier: Modifier = Modifier,
    content: @Composable () -> Unit,
) {
    val progress = remember { Animatable(0f) }
    LaunchedEffect(Unit) {
        progress.animateTo(1f, tween(durationMillis = durationMillis, easing = LinearEasing))
    }
    Box(modifier = modifier.graphicsLayer { alpha = progress.value }) {
        content()
    }
}

// --------------------------------------------------------------------------
// The flame (`flameSvg()` / `miniFlameSvg()`)
// --------------------------------------------------------------------------

/** The flame's layers in its 100x100 viewBox. */
private class FlamePaths(val outer: Path, val inner: Path, val frost: Path, val shards: Path)

private fun flamePaths(): FlamePaths {
    val outer = Path().apply {
        moveTo(50f, 6f)
        cubicTo(57f, 22f, 76f, 32f, 76f, 56f)
        // A26 28 0 0 1 24 56: the lower half of an ellipse centred on (50, 56).
        arcTo(Rect(24f, 28f, 76f, 84f), 0f, 180f, false)
        cubicTo(24f, 42f, 34f, 33f, 39f, 20f)
        cubicTo(43f, 29f, 48f, 30f, 50f, 6f)
        close()
    }
    val inner = Path().apply {
        moveTo(50f, 36f)
        cubicTo(55f, 47f, 66f, 51f, 66f, 64f)
        // A16 17 0 0 1 34 64: the lower half of an ellipse centred on (50, 64).
        arcTo(Rect(34f, 47f, 66f, 81f), 0f, 180f, false)
        cubicTo(34f, 54f, 43f, 50f, 46f, 41f)
        cubicTo(48f, 46f, 49f, 44f, 50f, 36f)
        close()
    }
    val frost = Path().apply {
        moveTo(26f, 44f); lineTo(74f, 40f); lineTo(76f, 52f); lineTo(24f, 57f); close()
    }
    val shards = Path().apply {
        moveTo(30f, 34f); lineTo(37f, 39f); lineTo(30f, 44f); close()
        moveTo(70f, 62f); lineTo(77f, 67f); lineTo(70f, 72f); close()
    }
    return FlamePaths(outer, inner, frost, shards)
}

private class FlameColors(val outer: Color, val inner: Color, val core: Color)

private val FlameLit = FlameColors(Color(0xFFE04A40), Color(0xFFE9A916), Color(0xFFFFF3D6))
private val FlameIce = FlameColors(Color(0xFF7FB4D6), Color(0xFFBEE3F5), Color(0xFFEAF7FF))
private val FlameAhead = FlameColors(Color(0xFF4A4A4A), Color(0xFF5E5E5E), Color(0xFF6E6E6E))
private val FlameGlow = Color(0xFFE9A916)

/**
 * Draws the flame fitted into the canvas. [flickerX]/[flickerY] sway it
 * around its base ([pivotY], in viewBox units); [grow] is the ignite scale.
 */
private fun DrawScope.drawFlame(
    paths: FlamePaths,
    colors: FlameColors,
    frozen: Boolean,
    flickerX: Float,
    flickerY: Float,
    pivotY: Float,
    grow: Float = 1f,
) {
    val s = size.minDimension / 100f
    val left = (size.width - 100f * s) / 2f
    val top = (size.height - 100f * s) / 2f
    withTransform({
        translate(left = left, top = top)
        scale(scaleX = s, scaleY = s, pivot = Offset.Zero)
        scale(scaleX = grow, scaleY = grow, pivot = Offset(50f, 50f))
        scale(scaleX = flickerX, scaleY = flickerY, pivot = Offset(50f, pivotY))
    }) {
        drawPath(paths.outer, colors.outer)
        drawPath(paths.inner, colors.inner)
        drawOval(colors.core, topLeft = Offset(41f, 57f), size = Size(18f, 20f))
        if (frozen) {
            drawPath(paths.frost, Color(0xFFDCF1FB), alpha = .55f)
            drawPath(paths.shards, Color(0xFFEAF7FF), alpha = .8f)
        }
    }
}

private val IgniteEase = bezier(.2f, 1.5f, .4f, 1f)
private val IGNITE_SCALE = arrayOf(HskKey(0f, .3f, IgniteEase), HskKey(.6f, 1.15f, IgniteEase), HskKey(1f, 1f))
private val IGNITE_ALPHA = arrayOf(HskKey(0f, 0f, IgniteEase), HskKey(1f, 1f))
private val FLICKER_Y = arrayOf(
    HskKey(0f, 1f, HskEaseInOut), HskKey(.3f, 1.05f, HskEaseInOut), HskKey(.6f, .96f, HskEaseInOut), HskKey(1f, 1f),
)
private val FLICKER_X = arrayOf(
    HskKey(0f, 1f, HskEaseInOut), HskKey(.3f, .97f, HskEaseInOut), HskKey(.6f, 1.03f, HskEaseInOut), HskKey(1f, 1f),
)
private val GLOW_ALPHA = arrayOf(HskKey(0f, .7f, HskEaseInOut), HskKey(.5f, 1f, HskEaseInOut), HskKey(1f, .7f))
private val GLOW_SCALE = arrayOf(HskKey(0f, 1f, HskEaseInOut), HskKey(.5f, 1.08f, HskEaseInOut), HskKey(1f, 1f))
private val MINI_FLICKER_Y = arrayOf(
    HskKey(0f, 1f, HskEaseInOut), HskKey(.45f, 1.08f, HskEaseInOut), HskKey(.7f, .94f, HskEaseInOut), HskKey(1f, 1f),
)
private val MINI_FLICKER_X = arrayOf(
    HskKey(0f, 1f, HskEaseInOut), HskKey(.45f, .95f, HskEaseInOut), HskKey(.7f, 1.05f, HskEaseInOut), HskKey(1f, 1f),
)

/** `.sk-flame.lit`: ignites, flickers, and glows gold behind. */
@Composable
internal fun HskStreakFlame(modifier: Modifier = Modifier) {
    val paths = remember { flamePaths() }
    val ignite = remember { Animatable(0f) }
    LaunchedEffect(Unit) {
        ignite.animateTo(1f, tween(durationMillis = 700, easing = LinearEasing))
    }
    val loop = rememberInfiniteTransition(label = "streak-flame")
    val flicker by loop.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(durationMillis = 1300, easing = LinearEasing)),
        label = "streak-flame-flicker",
    )
    val glow by loop.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(durationMillis = 1600, easing = LinearEasing)),
        label = "streak-flame-glow",
    )
    Box(modifier = modifier.size(150.dp), contentAlignment = Alignment.Center) {
        Canvas(Modifier.requiredSize(202.dp)) {
            val radius = size.minDimension / 2f * hskTrack(GLOW_SCALE, glow)
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(FlameGlow.copy(alpha = .4f), FlameGlow.copy(alpha = 0f)),
                    center = center,
                    radius = radius,
                ),
                radius = radius,
                alpha = hskTrack(GLOW_ALPHA, glow) * hskTrack(IGNITE_ALPHA, ignite.value).coerceIn(0f, 1f),
            )
        }
        Canvas(
            Modifier
                .fillMaxSize()
                .graphicsLayer {
                    alpha = hskTrack(IGNITE_ALPHA, ignite.value).coerceIn(0f, 1f)
                    // The ignite overshoots the canvas; an offscreen layer would clip it.
                    compositingStrategy = CompositingStrategy.ModulateAlpha
                },
        ) {
            drawFlame(
                paths = paths,
                colors = FlameLit,
                frozen = false,
                flickerX = hskTrack(FLICKER_X, flicker),
                flickerY = hskTrack(FLICKER_Y, flicker),
                pivotY = 88f,
                grow = hskTrack(IGNITE_SCALE, ignite.value).coerceAtLeast(.05f),
            )
        }
    }
}

/** A weekday's small flame: lit when studied, frozen when missed, dim when still ahead. */
internal enum class HskDayFlame { Lit, Frozen, Ahead }

@Composable
internal fun HskMiniFlame(state: HskDayFlame, modifier: Modifier = Modifier) {
    val paths = remember { flamePaths() }
    val flicker: State<Float>? = if (state == HskDayFlame.Lit) {
        rememberInfiniteTransition(label = "day-flame").animateFloat(
            initialValue = 0f,
            targetValue = 1f,
            animationSpec = infiniteRepeatable(tween(durationMillis = 1500, easing = LinearEasing)),
            label = "day-flame-flicker",
        )
    } else {
        null
    }
    Canvas(
        modifier
            .size(30.dp)
            .then(
                when (state) {
                    HskDayFlame.Lit -> Modifier
                    HskDayFlame.Frozen -> Modifier.alpha(.92f)
                    HskDayFlame.Ahead -> Modifier.alpha(.26f)
                },
            ),
    ) {
        val phase = flicker?.value ?: 0f
        if (state == HskDayFlame.Lit) {
            // `drop-shadow(0 0 8px rgba(233,169,22,.55))`, as a soft halo.
            val glowCentre = Offset(center.x, size.height * .6f)
            val glowRadius = size.minDimension * .75f
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(FlameGlow.copy(alpha = .45f), FlameGlow.copy(alpha = 0f)),
                    center = glowCentre,
                    radius = glowRadius,
                ),
                radius = glowRadius,
                center = glowCentre,
            )
        }
        drawFlame(
            paths = paths,
            colors = when (state) {
                HskDayFlame.Lit -> FlameLit
                HskDayFlame.Frozen -> FlameIce
                HskDayFlame.Ahead -> FlameAhead
            },
            frozen = state == HskDayFlame.Frozen,
            flickerX = hskTrack(MINI_FLICKER_X, phase),
            flickerY = hskTrack(MINI_FLICKER_Y, phase),
            pivotY = 90f,
        )
    }
}

private val StampEase = bezier(.15f, 1.5f, .35f, 1f)
private val STAMP_SCALE = arrayOf(HskKey(0f, 2.1f, StampEase), HskKey(.58f, .88f, StampEase), HskKey(1f, 1f))
private val STAMP_ROT = arrayOf(HskKey(0f, -12f, StampEase), HskKey(.58f, 3f, StampEase), HskKey(1f, 0f))
private val STAMP_ALPHA = arrayOf(HskKey(0f, 0f, StampEase), HskKey(1f, 1f))

/**
 * `.sk-day.just`: today's flame is stamped onto the week — big and tilted,
 * then pressed into place. [delayMillis] lets the row settle first.
 */
@Composable
internal fun HskStamp(
    delayMillis: Int,
    modifier: Modifier = Modifier,
    content: @Composable () -> Unit,
) {
    val stamp = remember { Animatable(0f) }
    LaunchedEffect(Unit) {
        delay(delayMillis.toLong())
        stamp.animateTo(1f, tween(durationMillis = 650, easing = LinearEasing))
    }
    Box(
        modifier = modifier.graphicsLayer {
            val grow = hskTrack(STAMP_SCALE, stamp.value).coerceAtLeast(.05f)
            scaleX = grow
            scaleY = grow
            rotationZ = hskTrack(STAMP_ROT, stamp.value)
            alpha = hskTrack(STAMP_ALPHA, stamp.value).coerceIn(0f, 1f)
        },
        contentAlignment = Alignment.Center,
    ) {
        content()
    }
}

private val NumberPopEase = bezier(.2f, 1.6f, .4f, 1f)
private val NUMBER_POP_SCALE = arrayOf(HskKey(0f, .35f, NumberPopEase), HskKey(.55f, 1.12f, NumberPopEase), HskKey(1f, 1f))
private val NUMBER_POP_ALPHA = arrayOf(HskKey(0f, 0f, NumberPopEase), HskKey(1f, 1f))

/** `skNumPop`: the streak number bursts in. */
@Composable
internal fun HskNumberPop(
    delayMillis: Int,
    modifier: Modifier = Modifier,
    content: @Composable () -> Unit,
) {
    val pop = remember { Animatable(0f) }
    LaunchedEffect(Unit) {
        delay(delayMillis.toLong())
        pop.animateTo(1f, tween(durationMillis = 600, easing = LinearEasing))
    }
    Box(
        modifier = modifier.graphicsLayer {
            val grow = hskTrack(NUMBER_POP_SCALE, pop.value).coerceAtLeast(.05f)
            scaleX = grow
            scaleY = grow
            alpha = hskTrack(NUMBER_POP_ALPHA, pop.value).coerceIn(0f, 1f)
        },
        contentAlignment = Alignment.Center,
    ) {
        content()
    }
}
