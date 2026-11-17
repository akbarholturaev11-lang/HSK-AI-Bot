package com.pomp.hskai.feature.lesson

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.asPaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.History
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.components.HskAnswerOption
import com.pomp.hskai.core.design.components.HskDepthButton
import com.pomp.hskai.core.design.components.HskSceneBackground
import com.pomp.hskai.core.design.components.HskStageCoach
import com.pomp.hskai.core.design.components.HskStageHeading
import com.pomp.hskai.core.design.components.hskOptionState
import com.pomp.hskai.core.design.components.hskReactionFor
import com.pomp.hskai.feature.practice.PracticeCheckFooter
import com.pomp.hskai.feature.practice.PracticeFeedbackPanel
import com.pomp.hskai.feature.practice.ReviewMaterial
import com.pomp.hskai.feature.practice.ReviewTokenBuilder
import com.pomp.hskai.feature.practice.mistakeCharacterFor
import com.pomp.hskai.feature.practice.practiceMoodFor
import kotlinx.coroutines.delay

/**
 * A personal review question inside an ordinary lesson (UIUX-007).
 *
 * It is the Xatolarim question in the lesson's own frame: the same top bar
 * (progress and hearts stay exactly where the base deck left them), a small
 * «Shaxsiy takror» line so the learner knows why it is here, and the server's
 * verdict. Nothing it shows or answers moves the lesson's score.
 */
@Composable
internal fun LessonAdaptiveReview(
    state: LessonUiState,
    review: AdaptiveReviewState,
    onAnswer: (selectedIndex: Int?, selectedTokens: List<String>?) -> Unit,
    onContinue: () -> Unit,
    onPlayAudio: (String) -> Unit,
    onOpenPinyinSettings: () -> Unit,
    onExit: () -> Unit,
) {
    val question = review.item.question
    val feedback = review.feedback
    val locked = review.checking || feedback != null || review.savedOffline
    var picked by remember(review.item.id) { mutableStateOf<Int?>(null) }
    // Sentence building: indexes into question.tokens, in the order laid.
    var laid by remember(review.item.id) { mutableStateOf(listOf<Int>()) }
    val bottomInset = WindowInsets.navigationBars.asPaddingValues().calculateBottomPadding()

    val play by rememberUpdatedState(onPlayAudio)
    LaunchedEffect(review.item.id) {
        if (question.autoplay && question.audioText.isNotBlank()) {
            delay(AUTOPLAY_DELAY_MILLIS)
            play(question.audioText)
        }
    }
    val haptics = LocalHapticFeedback.current
    LaunchedEffect(feedback) {
        val verdict = feedback ?: return@LaunchedEffect
        haptics.performHapticFeedback(
            if (verdict.correct) HapticFeedbackType.LongPress else HapticFeedbackType.TextHandleMove
        )
    }

    Box(modifier = Modifier.fillMaxSize()) {
        HskSceneBackground(Modifier.fillMaxSize())
        Column(modifier = Modifier.fillMaxSize()) {
            LessonTopBar(
                progress = state.progress,
                hearts = state.hearts,
                onOpenPinyinSettings = onOpenPinyinSettings,
                onExit = onExit,
            )
            HskStageHeading(question.prompt)
            BoxWithConstraints(modifier = Modifier.weight(1f).fillMaxWidth()) {
                val viewport = maxHeight
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .verticalScroll(rememberScrollState())
                        .heightIn(min = viewport)
                        .padding(start = 16.dp, end = 16.dp, top = 14.dp, bottom = 20.dp),
                    verticalArrangement = Arrangement.SpaceBetween,
                ) {
                    HskStageCoach(
                        character = mistakeCharacterFor(question.category),
                        mood = practiceMoodFor(feedback?.correct),
                        reaction = feedback?.let { hskReactionFor(correct = it.correct) },
                        reactionKey = review.item.id to feedback?.correct,
                    ) {
                        AdaptiveLabel()
                        if (question.audioText.isNotBlank() || question.sentence.isNotBlank() || question.pinyin.isNotBlank()) {
                            Spacer(Modifier.height(6.dp))
                            ReviewMaterial(
                                question = question,
                                isAudioLoading = state.isAudioLoading,
                                audioError = state.audioError,
                                onSpeak = { onPlayAudio(question.audioText) },
                            )
                        }
                    }
                    Column(
                        modifier = Modifier.fillMaxWidth().padding(top = 20.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        if (question.isBuilder) {
                            ReviewTokenBuilder(
                                tokens = question.tokens,
                                laid = laid,
                                enabled = !locked,
                                onLay = { laid = laid + it },
                                onLift = { position -> laid = laid.filterIndexed { index, _ -> index != position } },
                            )
                        }
                        val correctIndex = feedback?.correctIndex
                        question.options.forEachIndexed { index, option ->
                            HskAnswerOption(
                                text = option,
                                state = if (correctIndex != null) {
                                    hskOptionState(index, correctIndex, review.selectedIndex, isAnswered = true)
                                } else {
                                    hskOptionState(index, -1, review.selectedIndex ?: picked, isAnswered = false)
                                },
                                enabled = !locked,
                                onClick = { picked = index },
                            )
                        }
                    }
                }
            }
            when {
                feedback != null -> PracticeFeedbackPanel(
                    isCorrect = feedback.correct,
                    lines = buildList {
                        if (!feedback.correct && feedback.correctAnswer.isNotBlank()) {
                            add("${stringResource(R.string.hsk_course_right_ans)} ${feedback.correctAnswer}")
                        }
                        if (feedback.explanation.isNotBlank() && feedback.explanation != feedback.correctAnswer) {
                            add(feedback.explanation)
                        }
                    },
                    continueText = stringResource(R.string.hsk_common_action_continue),
                    loading = false,
                    onContinue = onContinue,
                    bottomInset = bottomInset,
                )
                review.savedOffline -> AdaptiveSavedPanel(onContinue = onContinue, bottomInset = bottomInset)
                question.isBuilder -> PracticeCheckFooter(
                    enabled = laid.size == question.tokens.size,
                    loading = review.checking,
                    onCheck = { onAnswer(null, laid.map { question.tokens[it] }) },
                    bottomInset = bottomInset,
                )
                else -> PracticeCheckFooter(
                    enabled = picked != null,
                    loading = review.checking,
                    onCheck = { picked?.let { onAnswer(it, null) } },
                    bottomInset = bottomInset,
                )
            }
        }
    }
}

/** Why this question is here: one quiet line, not a badge. */
@Composable
private fun AdaptiveLabel() {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        Icon(
            imageVector = Icons.Filled.History,
            contentDescription = null,
            tint = PompColors.Cinnabar,
            modifier = Modifier.size(16.dp),
        )
        Text(
            text = stringResource(R.string.hsk_course_adaptive_label),
            style = MaterialTheme.typography.labelMedium,
            fontWeight = FontWeight.SemiBold,
            color = PompColors.Cinnabar,
        )
    }
    Text(
        text = stringResource(R.string.hsk_course_adaptive_hint),
        fontSize = 12.sp,
        lineHeight = 16.sp,
        color = PompColors.InkSecondary,
        modifier = Modifier.padding(top = 2.dp),
    )
}

/** No connection: the answer waits on the phone and the lesson goes on. */
@Composable
private fun AdaptiveSavedPanel(onContinue: () -> Unit, bottomInset: Dp) {
    Surface(color = PompColors.GoldSoft, modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(start = 16.dp, end = 16.dp, top = 16.dp, bottom = 16.dp + bottomInset)) {
            Text(
                text = stringResource(R.string.hsk_course_adaptive_saved_offline),
                fontSize = 15.sp,
                lineHeight = 21.sp,
                color = PompColors.Ink,
            )
            Spacer(Modifier.height(14.dp))
            HskDepthButton(
                text = stringResource(R.string.hsk_common_action_continue),
                color = PompColors.Cinnabar,
                onClick = onContinue,
            )
        }
    }
}

private const val AUTOPLAY_DELAY_MILLIS = 250L
