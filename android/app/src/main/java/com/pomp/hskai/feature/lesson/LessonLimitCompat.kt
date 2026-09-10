package com.pomp.hskai.feature.lesson

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import com.pomp.hskai.R
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.settings.PinyinVisibility
import com.pomp.hskai.domain.model.ChoiceCard
import com.pomp.hskai.domain.model.LessonCard
import com.pomp.hskai.domain.model.MatchPairsCard
import com.pomp.hskai.feature.limit.LimitGate
import com.pomp.hskai.feature.limit.SectionLimitOverlay

/**
 * Adds the latest native limit overlay around the richer lesson surface without
 * replacing the dark-mode lesson implementation restored on codex/cloud-ai.
 */
@Composable
fun LessonScreen(
    state: LessonUiState,
    limit: LimitGate,
    pinyin: PinyinVisibility,
    onAnswerChoice: (ChoiceCard, Int) -> Unit,
    onAnswerBuilder: (LessonCard, List<String>) -> Unit,
    onAnswerPairs: (MatchPairsCard, List<Pair<Int, Int>>) -> Unit,
    onAcknowledge: () -> Unit,
    onAdvance: () -> Unit,
    onPlayAudio: (String) -> Unit,
    onRetryCompletion: () -> Unit,
    onOpenPinyinSettings: () -> Unit,
    onOpenWriter: (WriterTarget) -> Unit,
    onCloseWriter: () -> Unit,
    onExit: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Box(modifier = modifier.fillMaxSize()) {
        LessonScreen(
            state = state,
            pinyin = pinyin,
            onAnswerChoice = onAnswerChoice,
            onAnswerBuilder = onAnswerBuilder,
            onAnswerPairs = onAnswerPairs,
            onAcknowledge = onAcknowledge,
            onAdvance = onAdvance,
            onPlayAudio = onPlayAudio,
            onRetryCompletion = onRetryCompletion,
            onOpenPinyinSettings = onOpenPinyinSettings,
            onOpenWriter = onOpenWriter,
            onCloseWriter = onCloseWriter,
            onExit = onExit,
            modifier = Modifier.fillMaxSize(),
        )

        val spent = state.error as? ApiError.LimitReached
        if (spent != null) {
            SectionLimitOverlay(
                sectionTitle = stringResource(R.string.nav_course),
                limit = limit,
                reason = spent.limitText ?: stringResource(R.string.limit_lesson_reason),
                resetAt = spent.resetAt,
                onClose = onExit,
            )
        }
    }
}
