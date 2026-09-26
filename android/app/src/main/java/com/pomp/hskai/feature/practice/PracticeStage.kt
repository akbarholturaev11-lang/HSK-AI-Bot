package com.pomp.hskai.feature.practice

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Cancel
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.components.HskCinematicEntrance
import com.pomp.hskai.core.design.components.HskConfettiRain
import com.pomp.hskai.core.design.components.HskCue
import com.pomp.hskai.core.design.components.HskDepthButton
import com.pomp.hskai.core.design.components.HskEntrance
import com.pomp.hskai.core.design.components.HskGlassIconButton
import com.pomp.hskai.core.design.components.HskSceneBackground
import com.pomp.hskai.core.design.components.HskStageProgress
import com.pomp.hskai.core.design.components.hskPlayCue

/*
 * The practice screens in the lesson's stage layout: the same top bar, the
 * same Tekshirish, the same verdict panel. The verdict carries the right
 * answer and its explanation and nothing else — practice asks no AI on its
 * own, and offers no chat questions after a wrong answer.
 */

/** Close and progress: the lesson's top bar without the hearts practice does not have. */
@Composable
internal fun PracticeStageTopBar(progress: Float, onClose: () -> Unit, modifier: Modifier = Modifier) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .padding(start = 8.dp, end = 16.dp, top = 8.dp, bottom = 2.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        HskGlassIconButton(
            icon = Icons.Filled.Close,
            contentDescription = stringResource(R.string.action_close),
            onClick = onClose,
            size = 40.dp,
            iconSize = 24.dp,
            tint = PompColors.InkSecondary,
        )
        HskStageProgress(progress = progress, modifier = Modifier.weight(1f))
    }
}

/**
 * The footer before a check: a tap on an answer only picks it, this checks
 * it. [bottomInset] keeps it above the floating tab bar.
 */
@Composable
internal fun PracticeCheckFooter(
    enabled: Boolean,
    onCheck: () -> Unit,
    bottomInset: Dp,
    loading: Boolean = false,
) {
    Box(modifier = Modifier.padding(start = 16.dp, end = 16.dp, top = 8.dp, bottom = 16.dp + bottomInset)) {
        HskDepthButton(
            text = stringResource(R.string.lesson_check),
            color = PompColors.Cinnabar,
            onClick = onCheck,
            enabled = enabled,
            loading = loading,
        )
    }
}

/**
 * The verdict after a check, the lesson's panel: right or wrong, then — on a
 * wrong answer — the right one and why, as plain text. [verdictSuffix] is
 * the pronunciation score, when there is one.
 */
@Composable
internal fun PracticeFeedbackPanel(
    isCorrect: Boolean,
    lines: List<String>,
    continueText: String,
    loading: Boolean,
    onContinue: () -> Unit,
    bottomInset: Dp,
    verdictSuffix: String = "",
) {
    val accent = if (isCorrect) PompColors.Jade else PompColors.Flame
    Surface(
        color = if (isCorrect) PompColors.JadeSoft else PompColors.FlameSoft,
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(modifier = Modifier.padding(start = 16.dp, end = 16.dp, top = 16.dp, bottom = 16.dp + bottomInset)) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                Icon(
                    imageVector = if (isCorrect) Icons.Filled.CheckCircle else Icons.Filled.Cancel,
                    contentDescription = null,
                    tint = accent,
                    modifier = Modifier.size(30.dp),
                )
                Text(
                    text = stringResource(if (isCorrect) R.string.lesson_correct else R.string.lesson_wrong) + verdictSuffix,
                    fontSize = 22.sp,
                    lineHeight = 28.sp,
                    fontWeight = FontWeight.Bold,
                    color = accent,
                )
            }
            lines.filter { it.isNotBlank() }.forEach { line ->
                Text(
                    text = line,
                    fontSize = 14.sp,
                    lineHeight = 20.sp,
                    color = PompColors.InkSecondary,
                    modifier = Modifier.padding(top = 6.dp),
                )
            }
            Spacer(Modifier.height(14.dp))
            HskDepthButton(
                text = continueText,
                color = accent,
                onClick = onContinue,
                enabled = !loading,
                loading = loading,
            )
        }
    }
}

/** A request that failed under a question, in the flame colour. */
@Composable
internal fun PracticeErrorPill(text: String, modifier: Modifier = Modifier) {
    Surface(color = PompColors.FlameSoft, shape = RoundedCornerShape(12.dp), modifier = modifier.fillMaxWidth()) {
        Text(
            text = text,
            style = MaterialTheme.typography.bodyMedium,
            color = PompColors.Flame,
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
        )
    }
}

/**
 * The lesson's closing clip before a practice result: the closing character
 * drops onto the page and lands in a puff of dust, then the result comes in.
 * A good round also gets the confetti and the lesson's closing tones; a round
 * that went badly lands quietly — a fanfare over a failed exam would mock it.
 *
 * The clip plays once per result: turning the phone does not replay it.
 */
@Composable
internal fun PracticeCompletionClip(
    outcome: PracticeCompletionOutcome,
    content: @Composable () -> Unit,
) {
    var revealed by rememberSaveable(outcome.kind, outcome.score, outcome.total) { mutableStateOf(false) }
    var cheered by rememberSaveable(outcome.kind, outcome.score, outcome.total) { mutableStateOf(false) }
    var rain by rememberSaveable(outcome.kind, outcome.score, outcome.total) { mutableStateOf(0) }
    val context = LocalContext.current
    LaunchedEffect(revealed) {
        if (!revealed || cheered) return@LaunchedEffect
        cheered = true
        if (outcome.showConfetti) {
            rain++
            hskPlayCue(context, HskCue.LESSON_DONE)
        }
    }
    Box(modifier = Modifier.fillMaxSize()) {
        AnimatedContent(
            targetState = revealed,
            transitionSpec = { fadeIn(tween(300)) togetherWith fadeOut(tween(300)) },
            modifier = Modifier.fillMaxSize(),
            label = "practice-completion-clip",
        ) { shown ->
            if (shown) {
                content()
            } else {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(PompColors.Paper),
                ) {
                    HskSceneBackground(Modifier.fillMaxSize())
                    HskCinematicEntrance(
                        entrance = HskEntrance.LAND,
                        character = completionCharacterFor(outcome.reaction),
                        mood = completionMoodFor(outcome.reaction),
                        onReveal = { revealed = true },
                    )
                }
            }
        }
        HskConfettiRain(key = rain.takeIf { it > 0 }, modifier = Modifier.fillMaxSize())
    }
}
