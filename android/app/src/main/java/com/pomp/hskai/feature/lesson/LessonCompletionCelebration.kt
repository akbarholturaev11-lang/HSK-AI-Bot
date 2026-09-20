package com.pomp.hskai.feature.lesson

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.scaleIn
import androidx.compose.animation.scaleOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.BorderStroke
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
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.components.HskCelebrationPanda
import com.pomp.hskai.core.design.components.HskCelebrationStage
import com.pomp.hskai.core.design.components.HskStageInkMuted
import com.pomp.hskai.core.design.components.HskStageInkOn
import com.pomp.hskai.core.design.components.HskStageTile
import com.pomp.hskai.core.design.components.HskStageTileBorder
import com.pomp.hskai.core.design.components.HskStreakCelebration

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

    HskCelebrationStage(
        confettiSeed = when (scene) {
            CelebrationScene.COMPLETE -> gamification.xp + outcome.correct
            CelebrationScene.STREAK -> gamification.streak * 31
            CelebrationScene.RANK_UP ->
                (verifiedRankUp?.before ?: 0) * 37 + (verifiedRankUp?.after ?: 0)
        },
    ) {
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
                                CelebrationScene.STREAK -> HskStreakCelebration(outcome.gamification)
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
        HskCelebrationPanda(
            drawable = R.drawable.widget_panda_celebrate,
            pulseKey = gamification.awardedXp,
        )
        Spacer(Modifier.height(14.dp))
        Text(
            text = completionTitle(accuracy, outcome.seed()),
            style = MaterialTheme.typography.headlineMedium,
            color = HskStageInkOn,
            textAlign = TextAlign.Center,
            fontWeight = FontWeight.Bold,
        )
        completionSubtitle(accuracy)?.let { subtitle ->
            Spacer(Modifier.height(8.dp))
            Text(
                text = subtitle,
                style = MaterialTheme.typography.bodyMedium,
                color = HskStageInkMuted,
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
                color = HskStageInkMuted,
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
        color = HskStageTile,
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
                color = HskStageInkOn,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(vertical = 10.dp),
            )
        }
    }
}

/**
 * The Mini App's rank board: who is above, you, and the learner this lesson
 * overtook. Without names it stays the plain before/after line rather than
 * inventing a board nobody can read.
 */
@Composable
private fun RankUpScene(rankUp: LessonRankUp, board: LessonRankBoard?) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        HskCelebrationPanda(
            drawable = R.drawable.widget_panda_cheer,
            pulseKey = rankUp.before * 1000 + rankUp.after,
        )
        Spacer(Modifier.height(14.dp))
        Text(
            text = stringResource(R.string.lesson_rank_title),
            style = MaterialTheme.typography.headlineSmall,
            color = HskStageInkOn,
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
            color = HskStageInkMuted,
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
        color = if (row.isMe) PompColors.LightCinnabar else HskStageTile,
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
                color = if (row.isMe) Color.White else HskStageInkMuted,
                fontWeight = FontWeight.SemiBold,
            )
            Surface(
                shape = RoundedCornerShape(9.dp),
                color = if (row.isMe) Color.White else HskStageTileBorder,
                modifier = Modifier.size(32.dp),
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Text(
                        text = row.avatar,
                        style = MaterialTheme.typography.labelLarge,
                        color = if (row.isMe) PompColors.LightCinnabarDark else HskStageInkOn,
                    )
                }
            }
            Text(
                text = row.name,
                style = MaterialTheme.typography.bodyMedium,
                color = if (row.isMe) Color.White else HskStageInkOn,
                fontWeight = if (row.isMe) FontWeight.SemiBold else FontWeight.Normal,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.weight(1f),
            )
            Text(
                text = "${row.xp}",
                style = MaterialTheme.typography.bodyMedium,
                color = if (row.isMe) Color.White else HskStageInkMuted,
                fontWeight = FontWeight.SemiBold,
            )
        }
    }
}
