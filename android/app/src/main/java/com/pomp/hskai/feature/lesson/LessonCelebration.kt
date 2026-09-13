package com.pomp.hskai.feature.lesson

import androidx.annotation.DrawableRes
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.scaleIn
import androidx.compose.animation.scaleOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.scale
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import kotlinx.coroutines.delay

/**
 * Native counterpart of Course v3's level-up chain.
 *
 * Mini App order is preserved here: lesson result first, then a streak screen
 * only when the server says the streak was extended. Rank-up is intentionally
 * a following stage; it is fed after the rating refresh rather than guessed
 * from XP on the client.
 */
@Composable
internal fun LessonCelebration(
    outcome: LessonOutcome.Completed,
    rankUp: LessonRankUp? = null,
    onDone: () -> Unit,
) {
    val gamification = outcome.gamification
    val showStreak = !outcome.duplicate &&
        !gamification.duplicate &&
        gamification.streakUpdated &&
        gamification.streak > 0
    val showRank = rankUp != null && rankUp.after in 1 until rankUp.before

    var stage by remember(outcome) { mutableIntStateOf(STAGE_LESSON) }
    val haptics = LocalHapticFeedback.current

    LaunchedEffect(stage) {
        haptics.performHapticFeedback(HapticFeedbackType.LongPress)
    }

    AnimatedContent(
        targetState = stage,
        transitionSpec = {
            (fadeIn(tween(220)) + scaleIn(initialScale = 0.92f)) togetherWith
                (fadeOut(tween(150)) + scaleOut(targetScale = 0.96f))
        },
        label = "lessonCelebrationStage",
    ) { current ->
        when (current) {
            STAGE_STREAK -> CelebrationStage(
                panda = R.drawable.widget_panda_streak,
                title = "${gamification.streak} 🔥",
                body = stringResource(R.string.profile_streak),
                metric = if (gamification.awardedXp > 0) "+${gamification.awardedXp} XP" else null,
                onContinue = {
                    if (showRank) stage = STAGE_RANK else onDone()
                },
            )

            STAGE_RANK -> CelebrationStage(
                panda = R.drawable.widget_panda_celebrate,
                title = "#${rankUp?.after ?: 0}",
                body = "↑ ${((rankUp?.before ?: 0) - (rankUp?.after ?: 0)).coerceAtLeast(1)}",
                metric = null,
                onContinue = onDone,
            )

            else -> CelebrationStage(
                panda = R.drawable.widget_panda_celebrate,
                title = stringResource(R.string.lesson_done_title),
                body = stringResource(
                    R.string.lesson_done_accuracy,
                    outcome.correct,
                    outcome.graded,
                ),
                metric = gamification.awardedXp
                    .takeIf { it > 0 && !outcome.duplicate }
                    ?.let { "+$it XP" },
                onContinue = {
                    when {
                        showStreak -> stage = STAGE_STREAK
                        showRank -> stage = STAGE_RANK
                        else -> onDone()
                    }
                },
            )
        }
    }
}

@Composable
private fun CelebrationStage(
    @DrawableRes panda: Int,
    title: String,
    body: String,
    metric: String?,
    onContinue: () -> Unit,
) {
    var entered by remember(panda, title) { mutableIntStateOf(0) }
    LaunchedEffect(panda, title) {
        entered = 0
        delay(40)
        entered = 1
    }
    val pandaScale by animateFloatAsState(
        targetValue = if (entered == 1) 1f else 0.72f,
        animationSpec = tween(420),
        label = "celebrationPandaScale",
    )

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 28.dp, vertical = 32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Image(
            painter = painterResource(panda),
            contentDescription = null,
            modifier = Modifier.size(178.dp).scale(pandaScale),
        )
        Spacer(Modifier.height(18.dp))
        Text(
            text = title,
            style = MaterialTheme.typography.headlineMedium.copy(fontSize = 28.sp),
            fontWeight = FontWeight.Bold,
            color = PompColors.Ink,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(8.dp))
        Text(
            text = body,
            style = MaterialTheme.typography.bodyLarge,
            color = PompColors.InkSecondary,
            textAlign = TextAlign.Center,
        )
        metric?.let {
            Spacer(Modifier.height(16.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.Center,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = it,
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                    color = PompColors.Gold,
                )
            }
        }
        Spacer(Modifier.height(30.dp))
        PrimaryAction(
            text = stringResource(R.string.action_continue),
            onClick = onContinue,
        )
    }
}

internal data class LessonRankUp(
    val before: Int,
    val after: Int,
)

private const val STAGE_LESSON = 0
private const val STAGE_STREAK = 1
private const val STAGE_RANK = 2
