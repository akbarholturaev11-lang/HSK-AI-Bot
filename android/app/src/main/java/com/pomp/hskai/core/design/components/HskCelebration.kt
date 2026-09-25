package com.pomp.hskai.core.design.components

import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shadow
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.res.stringArrayResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.data.api.CourseGamificationDto
import com.pomp.hskai.feature.profile.weekCalendarMeta

/**
 * The Mini App's `.levelup` overlay, shared by every celebration in the app.
 *
 * A lesson and a practice round end with the same kind of moment, so they use
 * one stage rather than two that slowly stop looking alike. The stage stays
 * dark in both themes — that is what the rays and the flame are drawn against.
 *
 * [raysVisible] is false during a cinematic entrance: the Mini App hides its
 * rays for the close-up and fades them back in with the scene. Each new
 * [rainKey] lets one shower of confetti fall over everything (`luRain()`).
 */
@Composable
fun HskCelebrationStage(
    modifier: Modifier = Modifier,
    raysVisible: Boolean = true,
    rainKey: Any? = null,
    content: @Composable () -> Unit,
) {
    val rays by animateFloatAsState(
        targetValue = if (raysVisible) 1f else 0f,
        animationSpec = tween(durationMillis = 400),
        label = "stage-rays",
    )
    Box(
        modifier = modifier
            .fillMaxSize()
            .background(HskStageInk),
    ) {
        HskRayBurst(modifier = Modifier.fillMaxSize().graphicsLayer { alpha = rays })
        content()
        HskConfettiRain(key = rainKey, modifier = Modifier.fillMaxSize())
    }
}

/**
 * The Mini App's flame screen: the streak, the seven days of this week and how
 * much of the week is already closed.
 *
 * Which days are lit is the server's answer (`week_start` +
 * `week_activity_dates`), read through the same helper the profile calendar
 * uses — the two must never disagree about the same week.
 *
 * A lesson and a practice round both report the same gamification snapshot,
 * so both get the same screen rather than two that drift apart. The lines
 * come in one after another (`luReveal`); the flame ignites, the number pops
 * and today's flame is stamped onto the week, as in the Mini App.
 */
@Composable
fun HskStreakCelebration(gamification: CourseGamificationDto) {
    val streak = gamification.streak
    val meta = remember(gamification) {
        weekCalendarMeta(
            weekStart = gamification.weekStart,
            activityDates = gamification.weekActivityDates.takeIf { it.isNotEmpty() },
            localDate = gamification.localDate,
        )
    }
    val done = meta.activeCount(streak).coerceIn(0, 7)
    val days = stringArrayResource(R.array.profile_week_days)

    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        HskReveal(delayMillis = 0) {
            // `.sk-flame` with `.sk-panda` sitting at its lower right.
            Box(modifier = Modifier.size(150.dp)) {
                HskStreakFlame(modifier = Modifier.fillMaxSize())
                HskCharacterStage(
                    character = HskCharacter.Panda,
                    mood = HskCharacterMood.Celebrate,
                    reaction = HskCharacterReaction.Pop,
                    reactionKey = streak,
                    modifier = Modifier
                        .align(Alignment.BottomEnd)
                        .offset(x = 52.dp, y = 8.dp)
                        .size(86.dp),
                )
            }
        }
        HskReveal(delayMillis = 90) {
            HskNumberPop(delayMillis = 90) {
                Text(
                    text = "$streak",
                    style = TextStyle(
                        fontSize = 74.sp,
                        lineHeight = 78.sp,
                        fontWeight = FontWeight.ExtraBold,
                        shadow = Shadow(color = Color.Black.copy(alpha = .35f), offset = Offset(0f, 6f)),
                    ),
                    color = PompColors.LightGold,
                    textAlign = TextAlign.Center,
                )
            }
        }
        HskReveal(delayMillis = 170) {
            Text(
                text = stringResource(R.string.lesson_streak_days),
                style = MaterialTheme.typography.headlineSmall,
                color = HskStageInkOn,
                fontWeight = FontWeight.Bold,
                textAlign = TextAlign.Center,
            )
        }
        HskReveal(delayMillis = 250) {
            Text(
                text = streakCopy(streak, gamification.streakReset),
                style = MaterialTheme.typography.bodyMedium,
                color = HskStageInkMuted,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = 8.dp),
            )
        }
        HskReveal(delayMillis = 320) {
            Row(
                horizontalArrangement = Arrangement.spacedBy(9.dp),
                modifier = Modifier.padding(top = 18.dp),
            ) {
                for (index in 0 until 7) {
                    val studied = meta.studied(index, streak)
                    StreakDay(
                        label = days.getOrNull(index).orEmpty(),
                        flame = when {
                            studied -> HskDayFlame.Lit
                            index < meta.todayIndex -> HskDayFlame.Frozen
                            else -> HskDayFlame.Ahead
                        },
                        isToday = index == meta.todayIndex,
                    )
                }
            }
        }
        HskReveal(delayMillis = 380) {
            WeekGoalCard(done = done, modifier = Modifier.padding(top = 16.dp))
        }
    }
}

/**
 * One weekday (`.sk-day`): lit when studied, frozen when missed, dim when
 * still ahead. Today's lit flame is stamped in once the row is in place.
 */
@Composable
private fun StreakDay(label: String, flame: HskDayFlame, isToday: Boolean) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall,
            color = when {
                isToday -> HskStageInkOn
                flame == HskDayFlame.Lit -> PompColors.LightGold
                flame == HskDayFlame.Frozen -> HskStageIceLabel
                else -> HskStageInkDay
            },
            fontWeight = FontWeight.SemiBold,
        )
        Spacer(Modifier.height(4.dp))
        Box(
            modifier = Modifier.size(width = 34.dp, height = 36.dp),
            contentAlignment = Alignment.BottomCenter,
        ) {
            if (isToday && flame == HskDayFlame.Lit) {
                HskStamp(delayMillis = 450) { HskMiniFlame(state = flame) }
            } else {
                HskMiniFlame(state = flame)
            }
        }
    }
}

/** `.sk-weekgoal` — how much of this week is already closed. */
@Composable
private fun WeekGoalCard(done: Int, modifier: Modifier = Modifier) {
    val left = (7 - done).coerceAtLeast(0)
    Surface(
        shape = RoundedCornerShape(15.dp),
        color = HskStageTile,
        border = BorderStroke(1.dp, HskStageTileBorder),
        modifier = modifier.fillMaxWidth(),
    ) {
        Column(modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = stringResource(R.string.lesson_week_title),
                    style = MaterialTheme.typography.labelLarge,
                    color = HskStageInkOn,
                    fontWeight = FontWeight.SemiBold,
                )
                Text(
                    text = stringResource(R.string.lesson_week_count, done),
                    style = MaterialTheme.typography.labelLarge,
                    color = PompColors.LightGold,
                    fontWeight = FontWeight.Bold,
                )
            }
            Spacer(Modifier.height(9.dp))
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(8.dp)
                    .clip(RoundedCornerShape(999.dp))
                    .background(HskStageTrack),
            ) {
                val width by animateFloatAsState(
                    targetValue = done / 7f,
                    animationSpec = tween(durationMillis = 800, easing = FastOutSlowInEasing),
                    label = "week-goal-fill",
                )
                if (width > 0f) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth(width.coerceIn(0.01f, 1f))
                            .height(8.dp)
                            .clip(RoundedCornerShape(999.dp))
                            .background(PompColors.LightGold),
                    )
                }
            }
            Spacer(Modifier.height(7.dp))
            Text(
                text = if (done >= 7) {
                    stringResource(R.string.lesson_week_done)
                } else {
                    stringResource(R.string.lesson_week_left, left)
                },
                style = MaterialTheme.typography.bodySmall,
                color = HskStageInkMuted,
            )
        }
    }
}

/**
 * The streak sentence, ported from the Mini App's `streakCopy()`. Coming back
 * after a break is its own message: the day count would otherwise read as a
 * loss rather than a return.
 */
@Composable
private fun streakCopy(streak: Int, reset: Boolean): String = stringResource(
    when {
        reset -> R.string.lesson_streak_reset
        streak >= 100 -> R.string.lesson_streak_d100
        streak >= 30 -> R.string.lesson_streak_d30
        streak >= 14 -> R.string.lesson_streak_d14
        streak >= 7 -> R.string.lesson_streak_d7
        streak >= 3 -> R.string.lesson_streak_d3
        streak >= 2 -> R.string.lesson_streak_d2
        else -> R.string.lesson_streak_d1
    },
)

/**
 * The Mini App's `#lu-rays`: 24 gold spokes turning slowly behind the stage.
 *
 * Drawn rather than shipped as an asset because it is 24 rectangles around one
 * centre — the same construction the Mini App builds in JavaScript.
 */
@Composable
fun HskRayBurst(modifier: Modifier = Modifier) {
    val spin = rememberInfiniteTransition(label = "ray-spin")
    val angle by spin.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 28_000, easing = LinearEasing),
        ),
        label = "ray-spin-angle",
    )
    Canvas(modifier = modifier) {
        val centre = Offset(size.width / 2f, size.height * 0.24f)
        val length = size.maxDimension
        val width = 2.dp.toPx()
        rotate(degrees = angle, pivot = centre) {
            for (index in 0 until 24) {
                rotate(degrees = index * 15f, pivot = centre) {
                    drawRect(
                        color = HskRayGold,
                        topLeft = Offset(centre.x - width / 2f, centre.y - length),
                        size = Size(width, length),
                    )
                }
            }
        }
    }
}

// The stage is the Mini App's `.levelup`: `--ink` behind, white on top. These
// stay the light-palette values in both themes, because the stage is dark by
// design rather than by theme.
internal val HskStageInk = PompColors.LightInk
internal val HskStageInkOn = Color.White
internal val HskStageInkMuted = Color.White.copy(alpha = 0.72f)
internal val HskStageInkFaint = Color.White.copy(alpha = 0.22f)
internal val HskStageTile = Color.White.copy(alpha = 0.08f)
internal val HskStageTileBorder = Color.White.copy(alpha = 0.16f)
internal val HskStageTrack = Color.White.copy(alpha = 0.12f)
internal val HskStageIce = Color(0xFF7FB4D6)
/** `.sk-day` label: `rgba(255,255,255,.55)`, and `#9CC6DF` on a frozen day. */
internal val HskStageInkDay = Color.White.copy(alpha = 0.55f)
internal val HskStageIceLabel = Color(0xFF9CC6DF)
/** `fill="#FFC800"` on the Mini App's rays, at its own `.5` opacity. */
internal val HskRayGold = Color(0xFFFFC800).copy(alpha = 0.16f)
