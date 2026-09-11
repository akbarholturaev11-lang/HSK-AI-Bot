package com.pomp.hskai.feature.rating

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
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
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.PompTextStyles

/**
 * The duel itself: the same questions the opponent gets, in the same order.
 *
 * There is no per-answer feedback on purpose — the server keeps the answer key
 * and compares the two scores at the end, which is what makes it a duel rather
 * than a drill.
 */
@Composable
fun ChallengeRunScreen(
    state: ChallengeRunUiState,
    opponentName: String,
    onSelect: (Int) -> Unit,
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
                            .fillMaxWidth(state.progress.coerceIn(0f, 1f))
                            .height(9.dp)
                            .clip(RoundedCornerShape(6.dp))
                            .background(PompColors.Cinnabar),
                    )
                }
            }

            when {
                state.isLoading -> Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center,
                ) { CircularProgressIndicator(color = PompColors.Cinnabar) }

                state.finished -> ChallengeSubmitted(
                    opponentName = opponentName,
                    onDone = onClose,
                )

                state.current == null -> ChallengeFailed(onRetry = onRetry, onClose = onClose)

                else -> ChallengeQuestion(
                    state = state,
                    opponentName = opponentName,
                    onSelect = onSelect,
                    onAdvance = onAdvance,
                )
            }
        }
    }
}

@Composable
private fun ColumnQuestionSpacing() = Spacer(Modifier.height(14.dp))

@Composable
private fun ChallengeQuestion(
    state: ChallengeRunUiState,
    opponentName: String,
    onSelect: (Int) -> Unit,
    onAdvance: () -> Unit,
) {
    val question = state.current ?: return
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 18.dp),
    ) {
        Text(
            text = stringResource(R.string.challenge_versus, opponentName),
            style = MaterialTheme.typography.labelLarge.copy(fontSize = 12.sp),
            fontWeight = FontWeight.SemiBold,
            color = PompColors.CinnabarDark,
        )
        ColumnQuestionSpacing()
        if (question.sentence.isNotBlank() || question.audioText.isNotBlank()) {
            Surface(
                color = PompColors.PaperRaised,
                shape = RoundedCornerShape(18.dp),
                border = BorderStroke(1.dp, PompColors.Divider),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(
                    text = question.sentence.ifBlank { question.audioText },
                    style = PompTextStyles.hanziSmall.copy(fontSize = 22.sp),
                    color = PompColors.Ink,
                    textAlign = TextAlign.Center,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 22.dp, horizontal = 16.dp),
                )
            }
            ColumnQuestionSpacing()
        }
        Text(
            text = question.prompt,
            style = MaterialTheme.typography.titleMedium.copy(fontSize = 15.sp),
            color = PompColors.InkSecondary,
        )
        Spacer(Modifier.height(12.dp))

        question.options.forEachIndexed { index, option ->
            val chosen = state.selected == index
            Surface(
                onClick = { onSelect(index) },
                enabled = !state.isSubmitting,
                shape = RoundedCornerShape(13.dp),
                color = if (chosen) PompColors.CinnabarSoft else PompColors.PaperRaised,
                border = BorderStroke(
                    2.dp,
                    if (chosen) PompColors.Cinnabar else PompColors.Divider,
                ),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 10.dp)
                    .heightIn(min = 54.dp),
            ) {
                Text(
                    text = option,
                    style = MaterialTheme.typography.titleMedium.copy(fontSize = 15.sp),
                    color = if (chosen) PompColors.CinnabarDark else PompColors.Ink,
                    modifier = Modifier.padding(horizontal = 15.dp, vertical = 14.dp),
                )
            }
        }

        Spacer(Modifier.weight(1f))
        Surface(
            onClick = onAdvance,
            enabled = state.selected != null && !state.isSubmitting,
            color = if (state.selected != null) PompColors.Cinnabar else PompColors.Divider,
            shape = RoundedCornerShape(14.dp),
            modifier = Modifier
                .fillMaxWidth()
                .padding(bottom = 20.dp),
        ) {
            Text(
                text = stringResource(
                    if (state.index + 1 >= state.total) {
                        R.string.challenge_finish
                    } else {
                        R.string.lesson_next
                    }
                ),
                style = MaterialTheme.typography.titleMedium.copy(fontSize = 16.sp),
                fontWeight = FontWeight.Medium,
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
private fun ChallengeSubmitted(opponentName: String, onDone: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text = "战",
            style = PompTextStyles.hanziLarge,
            color = PompColors.Cinnabar,
        )
        Spacer(Modifier.height(12.dp))
        Text(
            text = stringResource(R.string.challenge_sent, opponentName),
            style = MaterialTheme.typography.titleMedium,
            color = PompColors.Ink,
            textAlign = TextAlign.Center,
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
private fun ChallengeFailed(onRetry: () -> Unit, onClose: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Surface(
            color = PompColors.FlameSoft,
            shape = RoundedCornerShape(16.dp),
            border = BorderStroke(1.dp, PompColors.Flame.copy(alpha = 0.35f)),
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(
                text = stringResource(R.string.error_unknown),
                style = MaterialTheme.typography.bodyLarge,
                color = PompColors.Flame,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(horizontal = 18.dp, vertical = 16.dp),
            )
        }
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
        Spacer(Modifier.height(12.dp))
        Surface(
            onClick = onClose,
            color = PompColors.PaperRaised,
            shape = RoundedCornerShape(12.dp),
            border = BorderStroke(1.dp, PompColors.Divider),
        ) {
            Text(
                text = stringResource(R.string.action_close),
                style = MaterialTheme.typography.labelLarge,
                color = PompColors.InkSecondary,
                modifier = Modifier.padding(horizontal = 18.dp, vertical = 10.dp),
            )
        }
    }
}
