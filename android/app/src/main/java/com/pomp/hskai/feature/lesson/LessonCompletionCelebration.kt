package com.pomp.hskai.feature.lesson

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.scaleIn
import androidx.compose.animation.scaleOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AcUnit
import androidx.compose.material.icons.filled.LocalFireDepartment
import androidx.compose.material3.Icon
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
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringArrayResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.feature.profile.weekCalendarMeta
import kotlinx.coroutines.delay

data class LessonRankUp(
    val before: Int,
    val after: Int,
)

/**
 * Native counterpart of the Mini App's lesson-complete celebration queue.
 * Rank is never inferred from XP: it is shown only when the server-provided
 * before/after weekly leaderboard positions prove a real improvement.
 */
@Composable
internal fun LessonCompletionCelebration(
    outcome: LessonOutcome.Completed,
    /** Named rows for the board; null while it loads, or when it never came. */
    rankBoard: LessonRankBoard? = null,
    rankUp: LessonRankUp? = null,
    onExit: () -> Unit,
) {
    val gamification = outcome.gamification
    val verifiedRankUp = rankUp ?: outcome.let {
        if (
            !it.duplicate &&
            it.rankBefore > 0 &&
            it.rankAfter > 0 &&
            it.rankAfter < it.rankBefore
        ) {
            LessonRankUp(before = it.rankBefore, after = it.rankAfter)
        } else {
            null
        }
    }
    val scenes = remember(outcome, verifiedRankUp) {
        buildList {
            add(CelebrationScene.COMPLETE)
            if (
                !outcome.duplicate &&
                !gamification.duplicate &&
                gamification.streakUpdated &&
                gamification.streak > 0
            ) {
                add(CelebrationScene.STREAK)
            }
            if (verifiedRankUp != null) add(CelebrationScene.RANK_UP)
        }
    }
    var sceneIndex by remember(outcome) { mutableStateOf(0) }
    val scene = scenes[sceneIndex.coerceIn(0, scenes.lastIndex)]
    val haptics = LocalHapticFeedback.current

    LaunchedEffect(scene) {
        haptics.performHapticFeedback(HapticFeedbackType.LongPress)
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            // The Mini App's `.levelup` is `--ink` in both themes: the stage is
            // dark so the rays and the flame have somewhere to burn. The rays
            // and the confetti fill it edge to edge; only the content is inset.
            .background(StageInk),
    ) {
        RayBurst(modifier = Modifier.fillMaxSize())
        ConfettiField(
            seed = when (scene) {
                CelebrationScene.COMPLETE -> gamification.xp + outcome.correct
                CelebrationScene.STREAK -> gamification.streak * 31
                CelebrationScene.RANK_UP ->
                    (verifiedRankUp?.before ?: 0) * 37 + (verifiedRankUp?.after ?: 0)
            },
            modifier = Modifier.fillMaxSize(),
        )

        // The scene and the button share the column rather than being stacked
        // in a Box: the streak screen carries a week row and a goal card now,
        // and on a short phone the two would otherwise overlap.
        Column(
            modifier = Modifier
                .fillMaxSize()
                .systemBarsPadding()
                .padding(horizontal = 24.dp),
        ) {
            BoxWithConstraints(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth(),
            ) {
                // Centred while the scene fits and scrollable once it does not:
                // inside a scroll the height is unbounded, so the inner column
                // is given the viewport as its minimum for Center to mean
                // anything.
                val sceneMinHeight = maxHeight
                AnimatedContent(
                    targetState = scene,
                    transitionSpec = {
                        (fadeIn(tween(220)) + scaleIn(initialScale = 0.92f)) togetherWith
                            (fadeOut(tween(160)) + scaleOut(targetScale = 1.04f))
                    },
                    modifier = Modifier.fillMaxSize(),
                    label = "lesson-celebration-scene",
                ) { active ->
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .verticalScroll(rememberScrollState()),
                    ) {
                        Column(
                            modifier = Modifier
                                .fillMaxWidth()
                                .heightIn(min = sceneMinHeight)
                                .padding(vertical = 12.dp),
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.Center,
                        ) {
                            when (active) {
                                CelebrationScene.COMPLETE -> CompletionScene(outcome)
                                CelebrationScene.STREAK -> StreakScene(outcome)
                                CelebrationScene.RANK_UP ->
                                    verifiedRankUp?.let { RankUpScene(it, rankBoard) }
                            }
                        }
                    }
                }
            }

            PrimaryAction(
                text = if (sceneIndex < scenes.lastIndex) {
                    stringResource(R.string.lesson_next)
                } else {
                    stringResource(R.string.lesson_back_to_course)
                },
                onClick = {
                    if (sceneIndex < scenes.lastIndex) sceneIndex++ else onExit()
                },
            )
            Spacer(Modifier.height(20.dp))
        }
    }
}

private enum class CelebrationScene { COMPLETE, STREAK, RANK_UP }

@Composable
private fun CompletionScene(outcome: LessonOutcome.Completed) {
    val gamification = outcome.gamification
    val graded = outcome.graded
    val accuracy = if (graded > 0) outcome.correct * 100 / graded else -1
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        CelebrationPanda(
            drawable = R.drawable.widget_panda_celebrate,
            pulseKey = gamification.awardedXp,
        )
        Spacer(Modifier.height(14.dp))
        Text(
            text = completionTitle(accuracy, outcome.seed()),
            style = MaterialTheme.typography.headlineMedium,
            color = StageInkOn,
            textAlign = TextAlign.Center,
            fontWeight = FontWeight.Bold,
        )
        completionSubtitle(accuracy)?.let { subtitle ->
            Spacer(Modifier.height(8.dp))
            Text(
                text = subtitle,
                style = MaterialTheme.typography.bodyMedium,
                color = StageInkMuted,
                textAlign = TextAlign.Center,
            )
        }
        Spacer(Modifier.height(18.dp))
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            StatTile(
                label = stringResource(R.string.lesson_stat_xp),
                value = if (outcome.duplicate) "0" else "${gamification.awardedXp}",
                accent = PompColors.Gold,
                modifier = Modifier.weight(1f),
            )
            if (accuracy >= 0) StatTile(
                label = stringResource(R.string.lesson_stat_accuracy),
                value = "$accuracy%",
                accent = PompColors.Jade,
                modifier = Modifier.weight(1f),
            )
            StatTile(
                label = stringResource(R.string.lesson_stat_time),
                value = formatElapsed(outcome.elapsedSeconds),
                accent = PompColors.Blue,
                modifier = Modifier.weight(1f),
            )
        }
        if (gamification.league.isNotBlank()) {
            Spacer(Modifier.height(12.dp))
            Text(
                text = "${gamification.league} · ${gamification.weeklyXp} XP",
                style = MaterialTheme.typography.bodyMedium,
                color = StageInkMuted,
                textAlign = TextAlign.Center,
            )
        }
    }
}

/** Stable per completion, so the headline does not reshuffle on recomposition. */
private fun LessonOutcome.Completed.seed(): Int =
    correct * 31 + graded * 7 + gamification.awardedXp

@Composable
private fun completionTitle(accuracy: Int, seed: Int): String {
    val variants = when {
        accuracy < 0 -> return stringResource(R.string.lesson_done_title)
        accuracy >= 100 -> listOf(
            R.string.lesson_done_perfect_1,
            R.string.lesson_done_perfect_2,
            R.string.lesson_done_perfect_3,
        )
        accuracy >= 80 -> listOf(
            R.string.lesson_done_high_1,
            R.string.lesson_done_high_2,
            R.string.lesson_done_high_3,
        )
        accuracy >= 50 -> listOf(
            R.string.lesson_done_mid_1,
            R.string.lesson_done_mid_2,
            R.string.lesson_done_mid_3,
        )
        else -> listOf(
            R.string.lesson_done_low_1,
            R.string.lesson_done_low_2,
            R.string.lesson_done_low_3,
        )
    }
    return stringResource(variants[seed.mod(variants.size)])
}

@Composable
private fun completionSubtitle(accuracy: Int): String? = when {
    accuracy < 0 -> null
    accuracy >= 100 -> stringResource(R.string.lesson_done_perfect_sub)
    accuracy >= 80 -> stringResource(R.string.lesson_done_high_sub)
    accuracy >= 50 -> stringResource(R.string.lesson_done_mid_sub)
    else -> stringResource(R.string.lesson_done_low_sub)
}

private fun formatElapsed(seconds: Int): String {
    val safe = seconds.coerceAtLeast(0)
    return "${safe / 60}:${(safe % 60).toString().padStart(2, '0')}"
}

@Composable
private fun StatTile(label: String, value: String, accent: Color, modifier: Modifier = Modifier) {
    Surface(
        shape = RoundedCornerShape(14.dp),
        color = StageTile,
        border = BorderStroke(2.dp, accent),
        modifier = modifier,
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(
                text = label,
                style = MaterialTheme.typography.labelSmall,
                color = accent,
                fontWeight = FontWeight.Bold,
                textAlign = TextAlign.Center,
                modifier = Modifier
                    .fillMaxWidth()
                    .background(accent.copy(alpha = 0.16f))
                    .padding(vertical = 5.dp),
            )
            Text(
                text = value,
                style = MaterialTheme.typography.titleMedium,
                color = StageInkOn,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(vertical = 10.dp),
            )
        }
    }
}

/**
 * The Mini App's flame screen: the streak, the seven days of this week and how
 * much of the week is already closed.
 *
 * Which days are lit is the server's answer (`week_start` +
 * `week_activity_dates`), read through the same helper the profile calendar
 * uses — the two must never disagree about the same week.
 */
@Composable
private fun StreakScene(outcome: LessonOutcome.Completed) {
    val gamification = outcome.gamification
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
        Box(contentAlignment = Alignment.Center) {
            Icon(
                imageVector = Icons.Filled.LocalFireDepartment,
                contentDescription = null,
                tint = PompColors.LightCinnabar,
                modifier = Modifier.size(104.dp),
            )
            CelebrationPanda(
                drawable = R.drawable.widget_panda_streak,
                pulseKey = streak,
                modifier = Modifier.offset(x = 46.dp, y = 8.dp),
                size = 52.dp,
            )
        }
        Text(
            text = "$streak",
            style = MaterialTheme.typography.displayLarge,
            color = PompColors.LightGold,
            fontWeight = FontWeight.Black,
            textAlign = TextAlign.Center,
        )
        Text(
            text = stringResource(R.string.lesson_streak_days),
            style = MaterialTheme.typography.headlineSmall,
            color = StageInkOn,
            fontWeight = FontWeight.Bold,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(8.dp))
        Text(
            text = streakCopy(streak, gamification.streakReset),
            style = MaterialTheme.typography.bodyMedium,
            color = StageInkMuted,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(18.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            for (index in 0 until 7) {
                val studied = meta.studied(index, streak)
                StreakDay(
                    label = days.getOrNull(index).orEmpty(),
                    studied = studied,
                    missed = !studied && index < meta.todayIndex,
                    isToday = index == meta.todayIndex,
                )
            }
        }
        Spacer(Modifier.height(16.dp))
        WeekGoalCard(done = done)
    }
}

/** One weekday: lit when studied, frozen when missed, dim when still ahead. */
@Composable
private fun StreakDay(label: String, studied: Boolean, missed: Boolean, isToday: Boolean) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall,
            color = if (isToday) PompColors.LightGold else StageInkMuted,
            fontWeight = if (isToday) FontWeight.Bold else FontWeight.Medium,
        )
        Spacer(Modifier.height(4.dp))
        Box(
            modifier = Modifier.size(width = 30.dp, height = 34.dp),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                imageVector = if (missed) Icons.Filled.AcUnit else Icons.Filled.LocalFireDepartment,
                contentDescription = null,
                tint = when {
                    studied -> PompColors.LightCinnabar
                    missed -> StageIce
                    else -> StageInkFaint
                },
                modifier = Modifier.size(24.dp),
            )
        }
    }
}

/** `.sk-weekgoal` — how much of this week is already closed. */
@Composable
private fun WeekGoalCard(done: Int) {
    val left = (7 - done).coerceAtLeast(0)
    Surface(
        shape = RoundedCornerShape(15.dp),
        color = StageTile,
        border = BorderStroke(1.dp, StageTileBorder),
        modifier = Modifier.fillMaxWidth(),
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
                    color = StageInkOn,
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
                    .background(StageTrack),
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
                color = StageInkMuted,
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
 * The Mini App's rank board: who is above, you, and the learner this lesson
 * overtook. Without names it stays the plain before/after line rather than
 * inventing a board nobody can read.
 */
@Composable
private fun RankUpScene(rankUp: LessonRankUp, board: LessonRankBoard?) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        CelebrationPanda(
            drawable = R.drawable.widget_panda_cheer,
            pulseKey = rankUp.before * 1000 + rankUp.after,
        )
        Spacer(Modifier.height(14.dp))
        Text(
            text = stringResource(R.string.lesson_rank_title),
            style = MaterialTheme.typography.headlineSmall,
            color = StageInkOn,
            fontWeight = FontWeight.Bold,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(8.dp))
        Text(
            text = if (board != null) {
                stringResource(R.string.lesson_rank_sub, board.passedName)
            } else {
                "#${rankUp.before} → #${rankUp.after}"
            },
            style = MaterialTheme.typography.bodyMedium,
            color = StageInkMuted,
            textAlign = TextAlign.Center,
        )
        if (board != null) {
            Spacer(Modifier.height(18.dp))
            board.rows.forEach { row -> RankRow(row) }
        }
    }
}

@Composable
private fun RankRow(row: LessonRankRow) {
    Surface(
        shape = RoundedCornerShape(12.dp),
        color = if (row.isMe) PompColors.LightCinnabar else StageTile,
        modifier = Modifier
            .fillMaxWidth()
            .padding(bottom = 6.dp),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 13.dp, vertical = 11.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(11.dp),
        ) {
            Text(
                text = "${row.rank}",
                style = MaterialTheme.typography.bodyMedium,
                color = if (row.isMe) Color.White else StageInkMuted,
                fontWeight = FontWeight.SemiBold,
            )
            Surface(
                shape = RoundedCornerShape(9.dp),
                color = if (row.isMe) Color.White else StageTileBorder,
                modifier = Modifier.size(32.dp),
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Text(
                        text = row.avatar,
                        style = MaterialTheme.typography.labelLarge,
                        color = if (row.isMe) PompColors.LightCinnabarDark else StageInkOn,
                    )
                }
            }
            Text(
                text = row.name,
                style = MaterialTheme.typography.bodyMedium,
                color = if (row.isMe) Color.White else StageInkOn,
                fontWeight = if (row.isMe) FontWeight.SemiBold else FontWeight.Normal,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.weight(1f),
            )
            Text(
                text = "${row.xp}",
                style = MaterialTheme.typography.bodyMedium,
                color = if (row.isMe) Color.White else StageInkMuted,
                fontWeight = FontWeight.SemiBold,
            )
        }
    }
}

@Composable
private fun CelebrationPanda(
    drawable: Int,
    pulseKey: Int,
    modifier: Modifier = Modifier,
    size: Dp = 164.dp,
) {
    var entered by remember(drawable, pulseKey) { mutableStateOf(false) }
    LaunchedEffect(drawable, pulseKey) {
        entered = false
        delay(40)
        entered = true
    }
    val scale by animateFloatAsState(
        targetValue = if (entered) 1f else 0.68f,
        animationSpec = tween(520, easing = FastOutSlowInEasing),
        label = "panda-pop-scale",
    )
    val alpha by animateFloatAsState(
        targetValue = if (entered) 1f else 0f,
        animationSpec = tween(260),
        label = "panda-pop-alpha",
    )
    Image(
        painter = painterResource(drawable),
        contentDescription = null,
        modifier = modifier
            .size(size)
            .scale(scale)
            .alpha(alpha),
    )
}

/**
 * The Mini App's `#lu-rays`: 24 gold spokes turning slowly behind the stage.
 *
 * Drawn rather than shipped as an asset because it is 24 rectangles around one
 * centre — the same construction the Mini App builds in JavaScript.
 */
@Composable
private fun RayBurst(modifier: Modifier = Modifier) {
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
                        color = RayGold,
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
private val StageInk = PompColors.LightInk
private val StageInkOn = Color.White
private val StageInkMuted = Color.White.copy(alpha = 0.72f)
private val StageInkFaint = Color.White.copy(alpha = 0.22f)
private val StageTile = Color.White.copy(alpha = 0.08f)
private val StageTileBorder = Color.White.copy(alpha = 0.16f)
private val StageTrack = Color.White.copy(alpha = 0.12f)
private val StageIce = Color(0xFF7FB4D6)
/** `fill="#FFC800"` on the Mini App's rays, at its own `.5` opacity. */
private val RayGold = Color(0xFFFFC800).copy(alpha = 0.16f)

@Composable
private fun ConfettiField(seed: Int, modifier: Modifier = Modifier) {
    val particles = remember(seed) {
        List(18) { index ->
            ConfettiParticle(
                x = ((index * 37 + seed * 11) % 100) / 100f,
                y = ((index * 53 + seed * 7) % 92) / 100f,
                symbol = CONFETTI_SYMBOLS[(index + seed.absoluteSafe()) % CONFETTI_SYMBOLS.size],
            )
        }
    }
    Box(modifier = modifier) {
        particles.forEachIndexed { index, particle ->
            Text(
                text = particle.symbol,
                color = CONFETTI_COLORS[index % CONFETTI_COLORS.size],
                modifier = Modifier
                    .align(Alignment.TopStart)
                    .offset(
                        x = (particle.x * 280).dp,
                        y = (particle.y * 620).dp,
                    )
                    .alpha(0.72f),
                style = MaterialTheme.typography.bodyMedium,
            )
        }
    }
}

private data class ConfettiParticle(
    val x: Float,
    val y: Float,
    val symbol: String,
)

private val CONFETTI_SYMBOLS = listOf("★", "✦", "✧", "◆", "●", "✺")
private val CONFETTI_COLORS = listOf(
    Color(0xFFF2B84B),
    Color(0xFF3CBF86),
    Color(0xFFE65B4B),
    Color(0xFF4B82D8),
)

private fun Int.absoluteSafe(): Int = if (this == Int.MIN_VALUE) 0 else kotlin.math.abs(this)