package com.pomp.hskai.feature.practice

import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
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

/**
 * Shared visual header for every Practice completion surface.
 *
 * It deliberately does not replace activity-specific result details. Exam
 * sections, wrong answers, placement recommendations and remaining mistakes
 * stay below this hero; only the celebratory layer is normalized here.
 */
@Composable
internal fun PracticeCompletionHero(
    outcome: PracticeCompletionOutcome,
    modifier: Modifier = Modifier,
) {
    val duplicate = outcome.isDuplicate
    val strongSuccess = when {
        outcome.passed == false -> false
        outcome.kind == PracticeCompletionKind.HSK_EXAM && outcome.passed == true -> true
        else -> outcome.percent >= 90
    }
    val haptics = LocalHapticFeedback.current

    LaunchedEffect(outcome.kind, outcome.score, outcome.total, duplicate) {
        if (!duplicate && strongSuccess) {
            haptics.performHapticFeedback(HapticFeedbackType.LongPress)
        }
    }

    Box(modifier = modifier.fillMaxWidth()) {
        if (!duplicate && strongSuccess) {
            PracticeConfetti(
                seed = outcome.score * 31 + outcome.total * 7 + outcome.kind.ordinal,
                modifier = Modifier.matchParentSize(),
            )
        }
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 8.dp, vertical = 8.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            CompletionPanda(
                drawable = pandaFor(outcome),
                pulseKey = outcome.score * 101 + outcome.total,
            )
            Spacer(Modifier.height(10.dp))
            Text(
                text = completionTitle(outcome),
                style = MaterialTheme.typography.headlineMedium,
                color = when {
                    outcome.passed == false -> PompColors.Ink
                    outcome.percent >= 70 -> PompColors.Jade
                    else -> PompColors.Ink
                },
                fontWeight = FontWeight.Bold,
                textAlign = TextAlign.Center,
            )
            Spacer(Modifier.height(6.dp))
            Text(
                text = "${outcome.score} / ${outcome.total} · ${outcome.percent}%",
                style = MaterialTheme.typography.titleMedium,
                color = PompColors.InkSecondary,
                textAlign = TextAlign.Center,
            )

            if (outcome.awardedXp > 0 || outcome.hasStreakEvent) {
                Spacer(Modifier.height(12.dp))
                Row(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    if (outcome.awardedXp > 0) {
                        CompletionPill("+${outcome.awardedXp} XP")
                    }
                    if (outcome.hasStreakEvent) {
                        CompletionPill("🔥 ${outcome.gamification.streak}")
                    }
                }
            }
        }
    }
}

@Composable
private fun completionTitle(outcome: PracticeCompletionOutcome): String = when {
    outcome.kind == PracticeCompletionKind.HSK_EXAM && outcome.passed == true ->
        stringResource(R.string.exam_result_passed)
    outcome.kind == PracticeCompletionKind.HSK_EXAM && outcome.passed == false ->
        stringResource(R.string.exam_result_failed)
    else -> stringResource(R.string.practice_result_title)
}

private fun pandaFor(outcome: PracticeCompletionOutcome): Int = when {
    outcome.kind == PracticeCompletionKind.HSK_EXAM && outcome.passed == false ->
        R.drawable.widget_panda_focus
    outcome.percent >= 90 -> R.drawable.widget_panda_celebrate
    outcome.percent >= 70 -> R.drawable.widget_panda_cheer
    outcome.percent >= 50 -> R.drawable.widget_panda_calm
    else -> R.drawable.widget_panda_focus
}

@Composable
private fun CompletionPanda(drawable: Int, pulseKey: Int) {
    var entered by remember(drawable, pulseKey) { mutableStateOf(false) }
    LaunchedEffect(drawable, pulseKey) {
        entered = false
        delay(40)
        entered = true
    }
    val scale by animateFloatAsState(
        targetValue = if (entered) 1f else 0.72f,
        animationSpec = tween(480, easing = FastOutSlowInEasing),
        label = "practice-panda-scale",
    )
    val alpha by animateFloatAsState(
        targetValue = if (entered) 1f else 0f,
        animationSpec = tween(240),
        label = "practice-panda-alpha",
    )
    Image(
        painter = painterResource(drawable),
        contentDescription = null,
        modifier = Modifier
            .size(152.dp)
            .scale(scale)
            .alpha(alpha),
    )
}

@Composable
private fun CompletionPill(text: String) {
    Surface(
        shape = RoundedCornerShape(999.dp),
        color = PompColors.Gold.copy(alpha = 0.18f),
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.titleSmall,
            color = PompColors.Ink,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 7.dp),
        )
    }
}

@Composable
private fun PracticeConfetti(seed: Int, modifier: Modifier = Modifier) {
    val symbols = listOf("★", "✦", "◆", "●", "✺")
    val particles = remember(seed) {
        List(16) { index ->
            Triple(
                ((index * 37 + seed * 11) % 100) / 100f,
                ((index * 53 + seed * 7) % 90) / 100f,
                symbols[(index + seed.absoluteSafe()) % symbols.size],
            )
        }
    }
    Box(modifier = modifier) {
        particles.forEachIndexed { index, (x, y, symbol) ->
            Text(
                text = symbol,
                color = when (index % 3) {
                    0 -> PompColors.Gold
                    1 -> PompColors.Jade
                    else -> PompColors.Cinnabar
                },
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier
                    .align(Alignment.TopStart)
                    .offset(x = (x * 280).dp, y = (y * 240).dp)
                    .alpha(0.68f),
            )
        }
    }
}

private fun Int.absoluteSafe(): Int = if (this == Int.MIN_VALUE) 0 else kotlin.math.abs(this)
