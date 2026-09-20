package com.pomp.hskai.feature.course

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.design.components.HskBrandLoader
import com.pomp.hskai.core.design.components.HskGlassButton
import com.pomp.hskai.core.design.components.HskPrimaryButton
import com.pomp.hskai.core.settings.PinyinVisibility
import com.pomp.hskai.feature.lesson.ChoiceCardView

/**
 * The Mini App's skip-ahead test, on Android.
 *
 * A locked lesson used to answer nothing at all here. Now it answers the way
 * the Mini App answers: a short test drawn from that lesson's own cards, and
 * the lesson opens on the other side of it — generously, because refusing a
 * weak score would only teach the learner to retake the test.
 */
@Composable
internal fun SkipTestScreen(
    state: SkipTestUiState,
    pinyin: PinyinVisibility,
    onStart: () -> Unit,
    onSelect: (Int) -> Unit,
    onAdvance: () -> Unit,
    onUnlock: () -> Unit,
    onOpenLesson: () -> Unit,
    onClose: () -> Unit,
) {
    BackHandler(onBack = onClose)

    Surface(modifier = Modifier.fillMaxSize(), color = PompColors.Paper) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .systemBarsPadding()
                .padding(horizontal = 20.dp),
        ) {
            // Bound once so the branches below read a value, not a nullable
            // property they each have to re-prove.
            val finished = state.finishedScore
            when {
                state.isLoading || state.isUnlocking -> Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center,
                ) { HskBrandLoader() }

                state.error != null -> SkipTestMessage(
                    title = stringResource(R.string.skip_test_not_ready),
                    body = stringResource(R.string.skip_test_save_error),
                    primaryLabel = stringResource(R.string.action_close),
                    onPrimary = onClose,
                )

                // The lesson is open on the server. The result is shown after
                // that, exactly as `completeSkipUnlock` orders it, and its
                // button walks straight into the lesson.
                state.unlocked -> SkipTestMessage(
                    title = stringResource(
                        if (state.passed) R.string.skip_test_pass_title
                        else R.string.skip_test_fail_title,
                    ),
                    body = stringResource(
                        if (state.passed) R.string.skip_test_pass_body
                        else R.string.skip_test_fail_body,
                        finished ?: state.score,
                    ),
                    primaryLabel = stringResource(R.string.skip_test_start_lesson),
                    onPrimary = onOpenLesson,
                )

                // A pass needs no permission; a weak score is asked about once
                // and opens the lesson anyway if the learner says so.
                finished != null && state.passed -> {
                    LaunchedEffect(finished) { onUnlock() }
                    Box(
                        modifier = Modifier.fillMaxSize(),
                        contentAlignment = Alignment.Center,
                    ) { HskBrandLoader() }
                }

                finished != null -> SkipTestMessage(
                    title = stringResource(R.string.skip_test_confirm_title),
                    body = stringResource(
                        R.string.skip_test_confirm_body,
                        finished,
                    ),
                    primaryLabel = stringResource(R.string.skip_test_confirm_yes),
                    onPrimary = onUnlock,
                    secondaryLabel = stringResource(R.string.skip_test_confirm_no),
                    onSecondary = onClose,
                )

                state.questions.isEmpty() -> SkipTestOffer(onStart = onStart, onClose = onClose)

                else -> SkipTestQuestion(
                    state = state,
                    pinyin = pinyin,
                    onSelect = onSelect,
                    onAdvance = onAdvance,
                )
            }
        }
    }
}

/** The sheet the Mini App opens on a locked node, before anything is loaded. */
@Composable
private fun SkipTestOffer(onStart: () -> Unit, onClose: () -> Unit) {
    Column(
        modifier = Modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        CoursePandaMascot(mood = PandaMood.Talk, modifier = Modifier.height(120.dp))
        Spacer(Modifier.height(14.dp))
        Text(
            text = stringResource(R.string.skip_test_tag),
            style = MaterialTheme.typography.labelLarge,
            color = PompColors.CinnabarDark,
            fontWeight = FontWeight.SemiBold,
        )
        Spacer(Modifier.height(8.dp))
        Text(
            text = stringResource(R.string.skip_test_offer),
            style = MaterialTheme.typography.bodyLarge,
            color = PompColors.InkSecondary,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(22.dp))
        HskPrimaryButton(
            text = stringResource(R.string.skip_test_start),
            onClick = onStart,
            modifier = Modifier.fillMaxWidth(),
        )
        Spacer(Modifier.height(10.dp))
        HskGlassButton(
            text = stringResource(R.string.action_close),
            onClick = onClose,
            modifier = Modifier.fillMaxWidth(),
        )
    }
}

@Composable
private fun SkipTestQuestion(
    state: SkipTestUiState,
    pinyin: PinyinVisibility,
    onSelect: (Int) -> Unit,
    onAdvance: () -> Unit,
) {
    val question = state.currentQuestion ?: return
    Column(modifier = Modifier.fillMaxSize()) {
        Column(modifier = Modifier.padding(top = 6.dp, bottom = 12.dp)) {
            Text(
                text = stringResource(
                    R.string.skip_test_progress,
                    state.index + 1,
                    state.questions.size,
                ),
                style = MaterialTheme.typography.labelMedium,
                color = PompColors.InkSecondary,
            )
            Spacer(Modifier.height(6.dp))
            LinearProgressIndicator(
                progress = { (state.index + 1f) / state.questions.size },
                color = PompColors.Cinnabar,
                trackColor = PompColors.Divider,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(6.dp)
                    .clip(RoundedCornerShape(999.dp)),
            )
        }
        Column(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .verticalScroll(rememberScrollState()),
        ) {
            ChoiceCardView(
                card = question,
                pinyin = pinyin,
                selectedIndex = state.selectedIndex,
                isAnswered = state.isAnswered,
                isAudioLoading = false,
                // The skip test is a check, not a lesson: nothing is spoken
                // for the learner here, so no audio is requested either.
                onPlayAudio = {},
                onSelect = onSelect,
            )
        }
        HskPrimaryButton(
            text = if (state.isLastQuestion) {
                stringResource(R.string.practice_finish)
            } else {
                stringResource(R.string.lesson_next)
            },
            onClick = onAdvance,
            enabled = state.isAnswered,
            modifier = Modifier.fillMaxWidth(),
        )
        Spacer(Modifier.height(18.dp))
    }
}

@Composable
private fun SkipTestMessage(
    title: String,
    body: String,
    primaryLabel: String,
    onPrimary: () -> Unit,
    secondaryLabel: String? = null,
    onSecondary: () -> Unit = {},
) {
    Column(
        modifier = Modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text(
            text = title,
            style = MaterialTheme.typography.headlineSmall,
            color = PompColors.Ink,
            fontWeight = FontWeight.Bold,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(10.dp))
        Text(
            text = body,
            style = MaterialTheme.typography.bodyLarge,
            color = PompColors.InkSecondary,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(22.dp))
        HskPrimaryButton(
            text = primaryLabel,
            onClick = onPrimary,
            modifier = Modifier.fillMaxWidth(),
        )
        if (secondaryLabel != null) {
            Spacer(Modifier.height(10.dp))
            HskGlassButton(
                text = secondaryLabel,
                onClick = onSecondary,
                modifier = Modifier.fillMaxWidth(),
            )
        }
    }
}
