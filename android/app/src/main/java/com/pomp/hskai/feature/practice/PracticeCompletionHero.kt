package com.pomp.hskai.feature.practice

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.BoxWithConstraints
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
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.components.HskCelebrationStage
import com.pomp.hskai.core.design.components.HskCharacterStage
import com.pomp.hskai.core.design.components.HskPrimaryButton
import com.pomp.hskai.core.design.components.HskStreakCelebration

/**
 * The flame screen after a practice round, on the same stage a lesson uses.
 *
 * Practice completions carry the very same gamification snapshot as a lesson,
 * so the streak is celebrated the same way. What they do not carry is a
 * leaderboard move — `rank_before` / `rank_after` exist only on lesson
 * completion — so there is no rank scene here rather than one guessed from XP.
 */
@Composable
internal fun PracticeStreakStep(
    outcome: PracticeCompletionOutcome,
    onDone: () -> Unit,
) {
    HskCelebrationStage(confettiSeed = outcome.gamification.streak * 31 + outcome.score) {
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
                val minHeight = maxHeight
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .verticalScroll(rememberScrollState()),
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .heightIn(min = minHeight)
                            .padding(vertical = 12.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.Center,
                    ) {
                        HskStreakCelebration(outcome.gamification)
                    }
                }
            }
            HskPrimaryButton(
                text = stringResource(R.string.lesson_next),
                onClick = onDone,
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(20.dp))
        }
    }
}

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
    val haptics = LocalHapticFeedback.current

    LaunchedEffect(
        outcome.kind,
        outcome.score,
        outcome.total,
        outcome.isDuplicate,
        outcome.strongHaptic,
    ) {
        if (outcome.strongHaptic) {
            haptics.performHapticFeedback(HapticFeedbackType.LongPress)
        }
    }

    Box(modifier = modifier.fillMaxWidth()) {
        if (outcome.showConfetti) {
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
            CompletionCharacter(
                reaction = outcome.reaction,
                pulseKey = outcome.score * 101 + outcome.total,
            )
            Spacer(Modifier.height(10.dp))
            Text(
                text = completionTitle(outcome),
                style = MaterialTheme.typography.headlineMedium,
                color = when {
                    outcome.passed == false -> PompColors.Ink
                    outcome.reaction == PracticeCompletionReaction.CELEBRATE ||
                        outcome.reaction == PracticeCompletionReaction.CHEER -> PompColors.Jade
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

/**
 * The face that closes a session.
 *
 * This used to be one of four flat `widget_panda_*` drawables — the widget's
 * artwork, borrowed. The lesson now ends on the live cast, and a session that
 * ended with a drawn panda while the lesson ended with a moving one read as
 * two different apps. Same renderer, same timings, one character system.
 */
@Composable
private fun CompletionCharacter(reaction: PracticeCompletionReaction, pulseKey: Int) {
    HskCharacterStage(
        character = completionCharacterFor(reaction),
        mood = completionMoodFor(reaction),
        reaction = completionReactionFor(reaction),
        reactionKey = reaction to pulseKey,
        modifier = Modifier.size(152.dp),
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
