package com.pomp.hskai.feature.practice

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompTextStyles
import com.pomp.hskai.feature.limit.LimitGate
import com.pomp.hskai.feature.limit.SectionLimitBlock

/**
 * The Mini App's adaptive drill screen.
 *
 * Recognition asks the learner to find the character behind a pinyin and a
 * meaning; pronunciation shows the character and listens. Both draw their
 * words from the same adviser, so the review schedule sees every answer.
 */
@Composable
fun WordDrillScreen(
    state: WordDrillUiState,
    limit: LimitGate,
    onChoose: (String) -> Unit,
    onSpeak: () -> Unit,
    onSkipSpoken: () -> Unit,
    onAdvance: () -> Unit,
    onRetry: () -> Unit,
    onClose: () -> Unit,
) {
    Surface(modifier = Modifier.fillMaxSize(), color = PompColors.Paper) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .statusBarsPadding(),
        ) {
            DrillTopBar(progress = state.progress, onClose = onClose)

            when {
                state.isLoading -> Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center,
                ) { CircularProgressIndicator(color = PompColors.Cinnabar) }

                // A spent allowance is not a dead end: this is the one
                // place that says what reopens the section.
                state.limitReached -> Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(horizontal = 18.dp),
                ) {
                    SectionLimitBlock(
                        sectionTitle = stringResource(
                            if (state.mode == DrillMode.RECOGNITION) {
                                R.string.practice_characters_title
                            } else {
                                R.string.practice_pronunciation_row_title
                            }
                        ),
                        limit = limit,
                        reason = stringResource(R.string.limit_practice_reason),
                        resetAt = state.resetAt,
                    )
                }

                state.finished -> DrillSummary(
                    correct = state.correctCount,
                    total = state.total,
                    onDone = onClose,
                )

                state.current == null -> DrillEmpty(onRetry = onRetry, onClose = onClose)

                else -> DrillQuestionBody(
                    state = state,
                    question = state.current!!,
                    onChoose = onChoose,
                    onSpeak = onSpeak,
                    onSkipSpoken = onSkipSpoken,
                    onAdvance = onAdvance,
                )
            }
        }
    }
}

@Composable
private fun DrillTopBar(progress: Float, onClose: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(start = 16.dp, end = 16.dp, top = 14.dp, bottom = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(11.dp),
    ) {
        Surface(
            onClick = onClose,
            shape = CircleShape,
            color = PompColors.PaperRaised,
            border = BorderStroke(1.dp, PompColors.Divider),
            modifier = Modifier.size(30.dp),
        ) {
            Box(contentAlignment = Alignment.Center) {
                Icon(
                    imageVector = Icons.Filled.Close,
                    contentDescription = stringResource(R.string.action_close),
                    tint = PompColors.InkSecondary,
                    modifier = Modifier.size(17.dp),
                )
            }
        }
        Box(
            modifier = Modifier
                .weight(1f)
                .height(9.dp)
                .clip(RoundedCornerShape(6.dp))
                .background(PompColors.Divider),
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth(progress.coerceIn(0f, 1f))
                    .height(9.dp)
                    .clip(RoundedCornerShape(6.dp))
                    .background(PompColors.Cinnabar),
            )
        }
    }
}

@Composable
private fun DrillQuestionBody(
    state: WordDrillUiState,
    question: DrillQuestion,
    onChoose: (String) -> Unit,
    onSpeak: () -> Unit,
    onSkipSpoken: () -> Unit,
    onAdvance: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 18.dp),
    ) {
        Spacer(Modifier.height(10.dp))
        Text(
            text = stringResource(
                if (state.mode == DrillMode.RECOGNITION) {
                    R.string.drill_recognition_prompt
                } else {
                    R.string.drill_pronunciation_prompt
                }
            ),
            style = MaterialTheme.typography.bodyMedium.copy(fontSize = 14.sp),
            fontWeight = FontWeight.Medium,
            color = PompColors.InkSecondary,
        )
        Spacer(Modifier.height(12.dp))

        Surface(
            color = PompColors.PaperRaised,
            shape = RoundedCornerShape(18.dp),
            border = BorderStroke(1.dp, PompColors.Divider),
            modifier = Modifier.fillMaxWidth(),
        ) {
            Column(
                modifier = Modifier.padding(vertical = 24.dp, horizontal = 18.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                if (state.mode == DrillMode.PRONUNCIATION) {
                    Text(
                        text = question.hanzi,
                        style = PompTextStyles.hanziLarge,
                        color = PompColors.Ink,
                    )
                }
                Text(
                    text = question.pinyin,
                    style = PompTextStyles.pinyin.copy(fontSize = 17.sp),
                    fontWeight = FontWeight.Medium,
                    color = PompColors.CinnabarDark,
                    textAlign = TextAlign.Center,
                )
                Spacer(Modifier.height(6.dp))
                Text(
                    text = question.meaning,
                    style = MaterialTheme.typography.titleMedium.copy(fontSize = 16.sp),
                    color = PompColors.Ink,
                    textAlign = TextAlign.Center,
                )
            }
        }

        Spacer(Modifier.height(18.dp))

        if (state.mode == DrillMode.RECOGNITION) {
            RecognitionOptions(state = state, question = question, onChoose = onChoose)
        } else {
            PronunciationControls(
                state = state,
                onSpeak = onSpeak,
                onSkipSpoken = onSkipSpoken,
            )
        }

        Spacer(Modifier.weight(1f))

        if (state.isAnswered) {
            DrillFeedback(state = state, question = question, onAdvance = onAdvance)
        }
        Spacer(Modifier.height(16.dp))
    }
}

@Composable
private fun RecognitionOptions(
    state: WordDrillUiState,
    question: DrillQuestion,
    onChoose: (String) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
        question.options.chunked(2).forEach { row ->
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                row.forEach { option ->
                    val isRight = state.isAnswered && option == question.hanzi
                    val isWrongPick = state.isAnswered &&
                        option == state.selected &&
                        option != question.hanzi
                    Surface(
                        onClick = { onChoose(option) },
                        enabled = !state.isAnswered,
                        shape = RoundedCornerShape(13.dp),
                        color = when {
                            isRight -> PompColors.JadeSoft
                            isWrongPick -> PompColors.CinnabarSoft
                            else -> PompColors.PaperRaised
                        },
                        border = BorderStroke(
                            2.dp,
                            when {
                                isRight -> PompColors.Jade
                                isWrongPick -> PompColors.Cinnabar
                                else -> PompColors.Divider
                            },
                        ),
                        modifier = Modifier
                            .weight(1f)
                            .padding(bottom = 10.dp),
                    ) {
                        Box(
                            modifier = Modifier.heightIn(min = 76.dp),
                            contentAlignment = Alignment.Center,
                        ) {
                            Text(
                                text = option,
                                style = PompTextStyles.hanziMedium,
                                color = when {
                                    isRight -> PompColors.Jade
                                    isWrongPick -> PompColors.CinnabarDark
                                    else -> PompColors.Ink
                                },
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun PronunciationControls(
    state: WordDrillUiState,
    onSpeak: () -> Unit,
    onSkipSpoken: () -> Unit,
) {
    val context = LocalContext.current
    val permission = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { granted -> if (granted) onSpeak() }

    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Surface(
            onClick = {
                val granted = ContextCompat.checkSelfPermission(
                    context,
                    Manifest.permission.RECORD_AUDIO,
                ) == PackageManager.PERMISSION_GRANTED
                if (granted) onSpeak() else permission.launch(Manifest.permission.RECORD_AUDIO)
            },
            enabled = !state.isRecording && !state.isScoring && !state.isAnswered,
            shape = CircleShape,
            color = if (state.isRecording) PompColors.CinnabarDark else PompColors.Cinnabar,
            border = BorderStroke(3.dp, PompColors.PaperRaised),
            modifier = Modifier.size(78.dp),
        ) {
            Box(contentAlignment = Alignment.Center) {
                Icon(
                    imageVector = Icons.Filled.Mic,
                    contentDescription = stringResource(R.string.voice_a11y_mic),
                    tint = PompColors.Paper,
                    modifier = Modifier.size(31.dp),
                )
            }
        }
        Spacer(Modifier.height(9.dp))
        Text(
            text = when {
                state.isRecording -> stringResource(R.string.foundation_speak_listening)
                state.isScoring -> stringResource(R.string.foundation_speak_checking)
                else -> stringResource(R.string.foundation_speak_check)
            },
            style = MaterialTheme.typography.bodySmall.copy(fontSize = 12.sp),
            color = PompColors.InkDisabled,
        )
        if (!state.isAnswered) {
            Spacer(Modifier.height(10.dp))
            Text(
                text = stringResource(R.string.foundation_speak_skip),
                style = MaterialTheme.typography.labelLarge.copy(fontSize = 13.sp),
                fontWeight = FontWeight.Bold,
                color = PompColors.InkDisabled,
                textAlign = TextAlign.Center,
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable(enabled = !state.isRecording && !state.isScoring) {
                        onSkipSpoken()
                    }
                    .padding(vertical = 6.dp),
            )
        }
    }
}

@Composable
private fun DrillFeedback(
    state: WordDrillUiState,
    question: DrillQuestion,
    onAdvance: () -> Unit,
) {
    Surface(
        color = if (state.wasCorrect) PompColors.JadeSoft else PompColors.CinnabarSoft,
        shape = RoundedCornerShape(14.dp),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Text(
                text = buildString {
                    append(
                        stringResource(
                            if (state.wasCorrect) R.string.lesson_correct else R.string.lesson_wrong
                        )
                    )
                    state.spokenScore?.let { append(" $it%") }
                },
                style = MaterialTheme.typography.titleMedium.copy(fontSize = 15.sp),
                fontWeight = FontWeight.Medium,
                color = if (state.wasCorrect) PompColors.Jade else PompColors.CinnabarDark,
            )
            if (!state.wasCorrect) {
                Text(
                    text = "${question.hanzi} · ${question.pinyin}",
                    style = MaterialTheme.typography.bodyMedium.copy(fontSize = 13.sp),
                    color = PompColors.InkSecondary,
                )
            }
            Spacer(Modifier.height(10.dp))
            Surface(
                onClick = onAdvance,
                color = if (state.wasCorrect) PompColors.Jade else PompColors.Cinnabar,
                shape = RoundedCornerShape(13.dp),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(
                    text = stringResource(R.string.lesson_next),
                    style = MaterialTheme.typography.titleMedium.copy(fontSize = 16.sp),
                    fontWeight = FontWeight.Medium,
                    color = PompColors.Paper,
                    textAlign = TextAlign.Center,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 14.dp),
                )
            }
        }
    }
}

@Composable
private fun DrillSummary(correct: Int, total: Int, onDone: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .navigationBarsPadding()
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text = stringResource(R.string.practice_result_title),
            style = MaterialTheme.typography.headlineMedium,
            color = PompColors.Ink,
        )
        Spacer(Modifier.height(10.dp))
        Text(
            text = "$correct / $total",
            style = MaterialTheme.typography.headlineMedium,
            color = PompColors.Jade,
        )
        Spacer(Modifier.height(24.dp))
        Surface(
            onClick = onDone,
            color = PompColors.Cinnabar,
            shape = RoundedCornerShape(14.dp),
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(
                text = stringResource(R.string.action_close),
                style = MaterialTheme.typography.titleMedium,
                color = PompColors.Paper,
                textAlign = TextAlign.Center,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 15.dp),
            )
        }
    }
}

@Composable
private fun DrillEmpty(onRetry: () -> Unit, onClose: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text = stringResource(R.string.error_unknown),
            style = MaterialTheme.typography.bodyLarge,
            color = PompColors.InkSecondary,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(16.dp))
        Surface(
            onClick = onRetry,
            color = PompColors.Cinnabar,
            shape = RoundedCornerShape(14.dp),
        ) {
            Text(
                text = stringResource(R.string.action_retry),
                style = MaterialTheme.typography.titleMedium,
                color = PompColors.Paper,
                modifier = Modifier.padding(horizontal = 22.dp, vertical = 13.dp),
            )
        }
        Spacer(Modifier.height(10.dp))
        Text(
            text = stringResource(R.string.action_close),
            style = MaterialTheme.typography.labelLarge,
            color = PompColors.InkDisabled,
            modifier = Modifier
                .clickable(onClick = onClose)
                .padding(8.dp),
        )
    }
}
