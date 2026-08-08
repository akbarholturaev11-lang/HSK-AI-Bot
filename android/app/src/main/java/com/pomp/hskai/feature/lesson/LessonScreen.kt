package com.pomp.hskai.feature.lesson

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.settings.PinyinVisibility
import com.pomp.hskai.domain.model.ChoiceCard
import com.pomp.hskai.domain.model.GrammarCard
import com.pomp.hskai.domain.model.LessonCard
import com.pomp.hskai.domain.model.MatchPairsCard
import com.pomp.hskai.domain.model.NewWordCard
import com.pomp.hskai.domain.model.PronunciationCard
import com.pomp.hskai.domain.model.ReverseBuilderCard
import com.pomp.hskai.domain.model.SentenceBuilderCard
import com.pomp.hskai.domain.model.UnsupportedCard

@Composable
internal fun PrimaryAction(
    // onClick is the second parameter, matching SecondaryAction, so a
    // positional call cannot land on `enabled` by accident.
    text: String,
    onClick: () -> Unit,
    enabled: Boolean = true,
) {
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 52.dp),
        shape = RoundedCornerShape(14.dp),
        colors = ButtonDefaults.buttonColors(
            containerColor = PompColors.Cinnabar,
            contentColor = PompColors.Paper,
        ),
    ) {
        Text(text = text, style = MaterialTheme.typography.labelLarge)
    }
}

@Composable
internal fun SecondaryAction(text: String, onClick: () -> Unit) {
    OutlinedButton(
        onClick = onClick,
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 48.dp),
        shape = RoundedCornerShape(14.dp),
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.labelLarge,
            color = PompColors.InkSecondary,
        )
    }
}

/**
 * One card per screen, a visible progress bar, and an unmistakable
 * correct/incorrect state. Nothing is graded silently.
 */
@Composable
fun LessonScreen(
    state: LessonUiState,
    pinyin: PinyinVisibility,
    onAnswerChoice: (ChoiceCard, Int) -> Unit,
    onAnswerBuilder: (LessonCard, List<String>) -> Unit,
    onAnswerPairs: (MatchPairsCard, List<Pair<Int, Int>>) -> Unit,
    onAcknowledge: () -> Unit,
    onAdvance: () -> Unit,
    onPlayAudio: (String) -> Unit,
    onRetryCompletion: () -> Unit,
    onExit: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val outcome = state.outcome
    Surface(modifier = modifier.fillMaxSize(), color = PompColors.Paper) {
        when {
            state.isLoading -> Centered { CircularProgressIndicator(color = PompColors.Cinnabar) }

            state.lesson == null -> Centered {
                Text(
                    text = stringResource(state.error?.messageRes ?: R.string.error_unknown),
                    style = MaterialTheme.typography.bodyLarge,
                    color = PompColors.InkSecondary,
                    textAlign = TextAlign.Center,
                )
                Spacer(Modifier.height(16.dp))
                SecondaryAction(stringResource(R.string.action_close), onExit)
            }

            outcome is LessonOutcome.PreviewExhausted -> PreviewEndBlock(onExit)

            outcome is LessonOutcome.Completed -> CompletedBlock(outcome, onExit)

            outcome is LessonOutcome.Failed ->
                FailedBlock(outcome, onRetryCompletion, onExit)

            else -> LessonBody(
                state = state,
                pinyin = pinyin,
                onAnswerChoice = onAnswerChoice,
                onAnswerBuilder = onAnswerBuilder,
                onAnswerPairs = onAnswerPairs,
                onAcknowledge = onAcknowledge,
                onAdvance = onAdvance,
                onPlayAudio = onPlayAudio,
                onExit = onExit,
            )
        }
    }
}

@Composable
private fun Centered(content: @Composable () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) { content() }
}

@Composable
private fun LessonBody(
    state: LessonUiState,
    pinyin: PinyinVisibility,
    onAnswerChoice: (ChoiceCard, Int) -> Unit,
    onAnswerBuilder: (LessonCard, List<String>) -> Unit,
    onAnswerPairs: (MatchPairsCard, List<Pair<Int, Int>>) -> Unit,
    onAcknowledge: () -> Unit,
    onAdvance: () -> Unit,
    onPlayAudio: (String) -> Unit,
    onExit: () -> Unit,
) {
    val haptics = LocalHapticFeedback.current
    val card = state.currentCard ?: return
    var selectedIndex by remember(state.cardIndex) { mutableStateOf<Int?>(null) }

    // Feedback is felt as well as seen; a wrong answer gets the heavier cue.
    LaunchedEffect(state.answer, state.cardIndex) {
        val answer = state.answer
        if (answer is AnswerState.Checked) {
            haptics.performHapticFeedback(
                if (answer.isCorrect) {
                    HapticFeedbackType.LongPress
                } else {
                    HapticFeedbackType.TextHandleMove
                }
            )
        }
    }

    Column(modifier = Modifier.fillMaxSize()) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            TextButton(onClick = onExit) {
                Text(
                    text = stringResource(R.string.action_close),
                    color = PompColors.InkSecondary,
                )
            }
            LinearProgressIndicator(
                progress = { state.progress },
                modifier = Modifier
                    .weight(1f)
                    .padding(horizontal = 8.dp),
                color = PompColors.Cinnabar,
                trackColor = PompColors.Divider,
            )
            Text(
                text = "${state.cardIndex + 1}/${state.totalCards}",
                style = MaterialTheme.typography.bodyMedium,
                color = PompColors.InkSecondary,
            )
        }

        Column(
            modifier = Modifier
                .weight(1f)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp, vertical = 12.dp),
        ) {
            when (card) {
                is NewWordCard -> NewWordCardView(card, pinyin)
                is GrammarCard -> GrammarCardView(card, pinyin)
                is PronunciationCard -> PronunciationCardView(
                    card = card,
                    pinyin = pinyin,
                    isAudioLoading = state.isAudioLoading,
                    onPlayAudio = onPlayAudio,
                    onSkip = onAcknowledge,
                )
                is ChoiceCard -> ChoiceCardView(
                    card = card,
                    pinyin = pinyin,
                    selectedIndex = selectedIndex,
                    isAnswered = state.isAnswered,
                    isAudioLoading = state.isAudioLoading,
                    onPlayAudio = onPlayAudio,
                    onSelect = { index ->
                        selectedIndex = index
                        onAnswerChoice(card, index)
                    },
                )

                is SentenceBuilderCard -> SentenceBuilderCardView(
                    card = card,
                    isAnswered = state.isAnswered,
                    onSubmit = { onAnswerBuilder(card, it) },
                )

                is ReverseBuilderCard -> ReverseBuilderCardView(
                    card = card,
                    pinyin = pinyin,
                    isAnswered = state.isAnswered,
                    onSubmit = { onAnswerBuilder(card, it) },
                )

                is MatchPairsCard -> MatchPairsCardView(
                    card = card,
                    isAnswered = state.isAnswered,
                    onFinished = { onAnswerPairs(card, it) },
                )

                is UnsupportedCard -> UnsupportedCardView(card, onAcknowledge)
            }
            state.audioError?.let { error ->
                Spacer(Modifier.height(12.dp))
                Text(
                    text = stringResource(error.messageRes),
                    style = MaterialTheme.typography.bodyMedium,
                    color = PompColors.CinnabarDark,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
            Spacer(Modifier.height(24.dp))
        }

        FooterBar(
            state = state,
            card = card,
            onAcknowledge = onAcknowledge,
            onAdvance = onAdvance,
        )
    }
}

@Composable
private fun FooterBar(
    state: LessonUiState,
    card: LessonCard,
    onAcknowledge: () -> Unit,
    onAdvance: () -> Unit,
) {
    val answer = state.answer
    if (answer is AnswerState.Checked) {
        Surface(
            color = if (answer.isCorrect) PompColors.JadeSoft else PompColors.CinnabarSoft,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Column(modifier = Modifier.padding(20.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = if (answer.isCorrect) "✓" else "✕",
                        style = MaterialTheme.typography.titleLarge,
                        color = if (answer.isCorrect) {
                            PompColors.Jade
                        } else {
                            PompColors.CinnabarDark
                        },
                    )
                    Spacer(Modifier.size(10.dp))
                    Text(
                        text = stringResource(
                            if (answer.isCorrect) {
                                R.string.lesson_correct
                            } else {
                                R.string.lesson_wrong
                            }
                        ),
                        style = MaterialTheme.typography.titleMedium,
                        color = PompColors.Ink,
                    )
                }
                if (answer.explanation.isNotBlank()) {
                    Spacer(Modifier.height(8.dp))
                    Text(
                        text = answer.explanation,
                        style = MaterialTheme.typography.bodyMedium,
                        color = PompColors.Ink,
                    )
                }
                Spacer(Modifier.height(16.dp))
                PrimaryAction(
                    text = stringResource(R.string.lesson_next),
                    onClick = onAdvance,
                )
            }
        }
        return
    }

    // Cards without a question advance on their own button.
    val needsAcknowledge = card is NewWordCard || card is GrammarCard
    if (needsAcknowledge) {
        Box(modifier = Modifier.padding(20.dp)) {
            PrimaryAction(
                text = stringResource(R.string.lesson_next),
                onClick = onAcknowledge,
            )
        }
    }
}

@Composable
private fun PreviewEndBlock(onExit: () -> Unit) {
    Centered {
        Text(
            text = stringResource(R.string.lesson_preview_over_title),
            style = MaterialTheme.typography.headlineMedium,
            color = PompColors.Ink,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(12.dp))
        Text(
            text = stringResource(R.string.lesson_preview_over_body),
            style = MaterialTheme.typography.bodyLarge,
            color = PompColors.InkSecondary,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(24.dp))
        // No subscribe CTA until Phase J wires real Play Billing.
        SecondaryAction(stringResource(R.string.action_close), onExit)
    }
}

@Composable
private fun CompletedBlock(outcome: LessonOutcome.Completed, onExit: () -> Unit) {
    Centered {
        Text(
            text = stringResource(R.string.lesson_done_title),
            style = MaterialTheme.typography.headlineMedium,
            color = PompColors.Jade,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(12.dp))
        if (outcome.graded > 0) {
            Text(
                text = stringResource(
                    R.string.lesson_done_accuracy,
                    outcome.correct,
                    outcome.graded,
                ),
                style = MaterialTheme.typography.titleMedium,
                color = PompColors.Ink,
            )
        }
        Spacer(Modifier.height(24.dp))
        PrimaryAction(stringResource(R.string.lesson_back_to_course), onClick = onExit)
    }
}

@Composable
private fun FailedBlock(
    outcome: LessonOutcome.Failed,
    onRetry: () -> Unit,
    onExit: () -> Unit,
) {
    Centered {
        Text(
            text = stringResource(R.string.lesson_save_failed),
            style = MaterialTheme.typography.titleMedium,
            color = PompColors.Ink,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(8.dp))
        Text(
            text = stringResource(outcome.error.messageRes),
            style = MaterialTheme.typography.bodyMedium,
            color = PompColors.InkSecondary,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(20.dp))
        // Retrying reuses the same event id, so the server dedupes it.
        PrimaryAction(stringResource(R.string.action_retry), onClick = onRetry)
        Spacer(Modifier.height(8.dp))
        SecondaryAction(stringResource(R.string.action_close), onExit)
    }
}
