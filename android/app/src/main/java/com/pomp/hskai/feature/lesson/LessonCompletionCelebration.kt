package com.pomp.hskai.feature.lesson

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.BorderStroke
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
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
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
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.zIndex
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.components.HskCelebrationEmblem
import com.pomp.hskai.core.design.components.HskCelebrationStage
import com.pomp.hskai.core.design.components.HskCinematicEntrance
import com.pomp.hskai.core.design.components.HskCue
import com.pomp.hskai.core.design.components.HskEntrance
import com.pomp.hskai.core.design.components.HskFadeIn
import com.pomp.hskai.core.design.components.HskReveal
import com.pomp.hskai.core.design.components.HskStageInkMuted
import com.pomp.hskai.core.design.components.HskStageInkOn
import com.pomp.hskai.core.design.components.HskStageTile
import com.pomp.hskai.core.design.components.HskStageTileBorder
import com.pomp.hskai.core.design.components.HskStreakCelebration
import com.pomp.hskai.core.design.components.hskPlayCue
import kotlinx.coroutines.delay

data class LessonRankUp(
    val before: Int,
    val after: Int,
)

/**
 * Native counterpart of the Mini App's lesson-complete celebration queue.
 * Rank is never inferred from XP: it is shown only when the server-provided
 * before/after weekly leaderboard positions prove a real improvement.
 *
 * Every scene opens the Mini App's way: a close-up of the character first —
 * it lands after a lesson, flies up through the sky for the streak, bursts
 * out of the distance for a rank-up — and only then the scene itself, line
 * by line, with its tones and the vibration that follows them.
 */
@Composable
internal fun LessonCompletionCelebration(
    outcome: LessonOutcome.Completed,
    isCheckpoint: Boolean = false,
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
    // The scene whose entrance is over. Until then only the character is on
    // stage — no rays, no text, no button (`.levelup.cine`).
    var revealedIndex by remember(outcome) { mutableStateOf(-1) }
    val revealed = revealedIndex == sceneIndex
    var rain by remember(outcome) { mutableStateOf(0) }
    val context = LocalContext.current

    // What each scene sounds like once it opens (`luRain()`, `beep()`, `haptic()`).
    LaunchedEffect(sceneIndex, revealed) {
        if (!revealed) return@LaunchedEffect
        when (scene) {
            CelebrationScene.COMPLETE -> {
                rain++
                hskPlayCue(context, HskCue.LESSON_DONE)
            }
            CelebrationScene.STREAK -> {
                delay(350)
                hskPlayCue(context, HskCue.STREAK)
            }
            CelebrationScene.RANK_UP -> {
                delay(RANK_SLIDE_DELAY_MS)
                rain++
                hskPlayCue(context, HskCue.RANK_UP)
            }
        }
    }

    HskCelebrationStage(
        raysVisible = revealed,
        rainKey = rain.takeIf { it > 0 },
    ) {
        AnimatedContent(
            targetState = sceneIndex to revealed,
            transitionSpec = { fadeIn(tween(300)) togetherWith fadeOut(tween(300)) },
            modifier = Modifier.fillMaxSize(),
            label = "lesson-celebration-scene",
        ) { (index, shown) ->
            val active = scenes[index.coerceIn(0, scenes.lastIndex)]
            if (!shown) {
                HskCinematicEntrance(
                    entrance = active.entrance,
                    character = if (active == CelebrationScene.COMPLETE && isCheckpoint) {
                        LessonCharacter.Dragon
                    } else {
                        LessonCharacter.Panda
                    },
                    cape = active == CelebrationScene.STREAK,
                    onReveal = { if (sceneIndex == index) revealedIndex = index },
                )
            } else {
                RevealedScene(
                    scene = active,
                    outcome = outcome,
                    isCheckpoint = isCheckpoint,
                    rankUp = verifiedRankUp,
                    rankBoard = rankBoard,
                    isLast = index >= scenes.lastIndex,
                    onNext = {
                        if (sceneIndex < scenes.lastIndex) sceneIndex++ else onExit()
                    },
                )
            }
        }
    }
}

private enum class CelebrationScene(val entrance: HskEntrance) {
    COMPLETE(HskEntrance.LAND),
    STREAK(HskEntrance.FLY),
    RANK_UP(HskEntrance.ZOOM),
}

/** `showRankUp()`: the rows swap and the confetti falls 420 ms after the scene opens. */
private const val RANK_SLIDE_DELAY_MS = 420L

/**
 * A scene after its entrance. The character that just landed waits in the
 * corner (`.lu-panda`); on the streak screen it sits by the flame instead.
 */
@Composable
private fun RevealedScene(
    scene: CelebrationScene,
    outcome: LessonOutcome.Completed,
    isCheckpoint: Boolean,
    rankUp: LessonRankUp?,
    rankBoard: LessonRankBoard?,
    isLast: Boolean,
    onNext: () -> Unit,
) {
    Box(modifier = Modifier.fillMaxSize()) {
        val corner = when (scene) {
            CelebrationScene.COMPLETE ->
                if (isCheckpoint) LessonCharacter.Dragon else LessonCharacter.Panda
            CelebrationScene.RANK_UP -> LessonCharacter.Panda
            CelebrationScene.STREAK -> null
        }
        if (corner != null) {
            LessonCharacterStage(
                character = corner,
                mood = LessonCharacterMood.Celebrate,
                reaction = LessonCharacterReaction.Pop,
                reactionKey = scene,
                modifier = Modifier
                    .align(Alignment.TopEnd)
                    .statusBarsPadding()
                    .padding(top = 24.dp, end = 24.dp)
                    .size(84.dp),
            )
        }
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
                        when (scene) {
                            CelebrationScene.COMPLETE -> CompletionScene(outcome, isCheckpoint)
                            CelebrationScene.STREAK -> HskStreakCelebration(outcome.gamification)
                            CelebrationScene.RANK_UP -> rankUp?.let { RankUpScene(it, rankBoard) }
                        }
                    }
                }
            }

            HskFadeIn(durationMillis = 400) {
                PrimaryAction(
                    text = if (isLast) {
                        stringResource(R.string.lesson_back_to_course)
                    } else {
                        stringResource(R.string.lesson_next)
                    },
                    onClick = onNext,
                )
            }
            Spacer(Modifier.height(20.dp))
        }
    }
}

@Composable
private fun CompletionScene(
    outcome: LessonOutcome.Completed,
    isCheckpoint: Boolean,
) {
    val gamification = outcome.gamification
    val graded = outcome.graded
    val accuracy = if (graded > 0) outcome.correct * 100 / graded else -1
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        // `.lu-emb`: 毕 "done" for a lesson, 胜 "won" for a checkpoint. The
        // glyph is the Mini App's own and reads the same in every language.
        HskReveal(delayMillis = 0) {
            HskCelebrationEmblem(glyph = if (isCheckpoint) "胜" else "毕")
        }
        HskReveal(delayMillis = 90) {
            Text(
                text = completionTitle(accuracy, outcome.seed()),
                style = MaterialTheme.typography.headlineMedium,
                color = HskStageInkOn,
                textAlign = TextAlign.Center,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(top = 14.dp),
            )
        }
        completionSubtitle(accuracy)?.let { subtitle ->
            HskReveal(delayMillis = 170) {
                Text(
                    text = subtitle,
                    style = MaterialTheme.typography.bodyMedium,
                    color = HskStageInkMuted,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.padding(top = 8.dp),
                )
            }
        }
        HskReveal(delayMillis = 250) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 18.dp),
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
        }
        if (gamification.league.isNotBlank()) {
            HskReveal(delayMillis = 320) {
                Text(
                    text = "${gamification.league} · ${gamification.weeklyXp} XP",
                    style = MaterialTheme.typography.bodyMedium,
                    color = HskStageInkMuted,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.padding(top = 12.dp),
                )
            }
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
 *
 * When the board is there, you and the learner you passed start in each
 * other's places and swap (`.ru-row` with `data-from`), so the overtaking is
 * seen rather than only read.
 */
@Composable
private fun RankUpScene(rankUp: LessonRankUp, board: LessonRankBoard?) {
    HskReveal(delayMillis = 0) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
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
                val slide = remember { Animatable(0f) }
                LaunchedEffect(Unit) {
                    delay(RANK_SLIDE_DELAY_MS)
                    slide.animateTo(1f, tween(durationMillis = 700, easing = RankSlideEase))
                }
                val meIndex = board.rows.indexOfFirst { it.isMe }
                board.rows.forEachIndexed { index, row ->
                    // You come up from the passed learner's row; they drop
                    // from yours.
                    val from = when {
                        row.isMe -> 1f
                        meIndex >= 0 && index == meIndex + 1 -> -1f
                        else -> 0f
                    }
                    RankRow(
                        row = row,
                        modifier = Modifier
                            .zIndex(if (row.isMe) 1f else 0f)
                            .graphicsLayer {
                                translationY = from * (1f - slide.value) * RANK_ROW_PITCH.toPx()
                            },
                    )
                }
            }
        }
    }
}

/** `transition: transform .7s cubic-bezier(.3,.85,.3,1)` on `.ru-row`. */
private val RankSlideEase = CubicBezierEasing(.3f, .85f, .3f, 1f)

/** One row plus the gap under it — how far a swap moves a row. */
private val RANK_ROW_PITCH = 60.dp

@Composable
private fun RankRow(row: LessonRankRow, modifier: Modifier = Modifier) {
    Surface(
        shape = RoundedCornerShape(12.dp),
        color = if (row.isMe) PompColors.LightCinnabar else HskStageTile,
        modifier = modifier
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
