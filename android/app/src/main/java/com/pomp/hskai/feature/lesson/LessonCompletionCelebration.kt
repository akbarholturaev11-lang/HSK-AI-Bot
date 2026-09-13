package com.pomp.hskai.feature.lesson

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.scaleIn
import androidx.compose.animation.scaleOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
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
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import kotlinx.coroutines.delay

data class LessonRankUp(
    val before: Int,
    val after: Int,
)

/**
 * Native counterpart of the Mini App's lesson-complete celebration queue.
 * Rank is never inferred from XP: [rankUp] only arrives after a server
 * leaderboard refresh proves that the new rank is numerically better.
 */
@Composable
internal fun LessonCompletionCelebration(
    outcome: LessonOutcome.Completed,
    rankUp: LessonRankUp? = null,
    onExit: () -> Unit,
) {
    val gamification = outcome.gamification
    val scenes = remember(outcome, rankUp) {
        buildList {
            add(CelebrationScene.COMPLETE)
            if (!outcome.duplicate && gamification.streakUpdated) add(CelebrationScene.STREAK)
            if (!outcome.duplicate && rankUp != null) add(CelebrationScene.RANK_UP)
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
            .background(PompColors.Paper)
            .padding(horizontal = 24.dp),
    ) {
        ConfettiField(
            seed = when (scene) {
                CelebrationScene.COMPLETE -> gamification.xp + outcome.correct
                CelebrationScene.STREAK -> gamification.streak * 31
                CelebrationScene.RANK_UP -> (rankUp?.before ?: 0) * 37 + (rankUp?.after ?: 0)
            },
            modifier = Modifier.fillMaxSize(),
        )

        AnimatedContent(
            targetState = scene,
            transitionSpec = {
                (fadeIn(tween(220)) + scaleIn(initialScale = 0.92f)) togetherWith
                    (fadeOut(tween(160)) + scaleOut(targetScale = 1.04f))
            },
            modifier = Modifier.align(Alignment.Center),
            label = "lesson-celebration-scene",
        ) { active ->
            when (active) {
                CelebrationScene.COMPLETE -> CompletionScene(outcome)
                CelebrationScene.STREAK -> StreakScene(outcome)
                CelebrationScene.RANK_UP -> rankUp?.let { RankUpScene(it) }
            }
        }

        Column(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .fillMaxWidth()
                .padding(bottom = 28.dp),
        ) {
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
        }
    }
}

private enum class CelebrationScene { COMPLETE, STREAK, RANK_UP }

@Composable
private fun CompletionScene(outcome: LessonOutcome.Completed) {
    val gamification = outcome.gamification
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        CelebrationPanda(
            drawable = R.drawable.widget_panda_celebrate,
            pulseKey = gamification.awardedXp,
        )
        Spacer(Modifier.height(14.dp))
        Text(
            text = stringResource(R.string.lesson_done_title),
            style = MaterialTheme.typography.headlineMedium,
            color = PompColors.Jade,
            textAlign = TextAlign.Center,
            fontWeight = FontWeight.Bold,
        )
        if (!outcome.duplicate && gamification.awardedXp > 0) {
            Spacer(Modifier.height(10.dp))
            RewardPill("+${gamification.awardedXp} XP")
        }
        if (outcome.graded > 0) {
            Spacer(Modifier.height(12.dp))
            Text(
                text = stringResource(R.string.lesson_done_accuracy, outcome.correct, outcome.graded),
                style = MaterialTheme.typography.titleMedium,
                color = PompColors.Ink,
                textAlign = TextAlign.Center,
            )
        }
        if (gamification.league.isNotBlank()) {
            Spacer(Modifier.height(8.dp))
            Text(
                text = "${gamification.league} · ${gamification.weeklyXp} XP",
                style = MaterialTheme.typography.bodyMedium,
                color = PompColors.InkSecondary,
                textAlign = TextAlign.Center,
            )
        }
    }
}

@Composable
private fun StreakScene(outcome: LessonOutcome.Completed) {
    val gamification = outcome.gamification
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        CelebrationPanda(
            drawable = R.drawable.widget_panda_streak,
            pulseKey = gamification.streak,
        )
        Spacer(Modifier.height(14.dp))
        Text(
            text = "🔥 ${gamification.streak}",
            style = MaterialTheme.typography.headlineMedium,
            color = PompColors.Ink,
            textAlign = TextAlign.Center,
            fontWeight = FontWeight.Bold,
        )
        Spacer(Modifier.height(8.dp))
        Text(
            text = "${gamification.previousStreak} → ${gamification.streak}",
            style = MaterialTheme.typography.titleMedium,
            color = PompColors.InkSecondary,
            textAlign = TextAlign.Center,
        )
    }
}

@Composable
private fun RankUpScene(rankUp: LessonRankUp) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        CelebrationPanda(
            drawable = R.drawable.widget_panda_cheer,
            pulseKey = rankUp.before * 1000 + rankUp.after,
        )
        Spacer(Modifier.height(14.dp))
        Text(
            text = "🏆 #${rankUp.after}",
            style = MaterialTheme.typography.headlineMedium,
            color = PompColors.Gold,
            textAlign = TextAlign.Center,
            fontWeight = FontWeight.Bold,
        )
        Spacer(Modifier.height(8.dp))
        Text(
            text = "#${rankUp.before} → #${rankUp.after}",
            style = MaterialTheme.typography.titleMedium,
            color = PompColors.Ink,
            textAlign = TextAlign.Center,
            fontWeight = FontWeight.SemiBold,
        )
    }
}

@Composable
private fun CelebrationPanda(drawable: Int, pulseKey: Int) {
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
        modifier = Modifier
            .size(164.dp)
            .scale(scale)
            .alpha(alpha),
    )
}

@Composable
private fun RewardPill(text: String) {
    Surface(
        shape = RoundedCornerShape(999.dp),
        color = PompColors.Gold.copy(alpha = 0.18f),
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.titleMedium,
            color = PompColors.Ink,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(horizontal = 18.dp, vertical = 8.dp),
        )
    }
}

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
