package com.pomp.hskai.feature.lesson

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.pomp.hskai.core.settings.PinyinVisibility
import com.pomp.hskai.domain.model.ChoiceCard
import com.pomp.hskai.domain.model.LessonCard
import com.pomp.hskai.domain.model.MatchPairsCard
import com.pomp.hskai.feature.limit.LimitGate

/**
 * Keeps the richer lesson surface source-compatible with the latest native
 * limit host while the overlay behavior is integrated without replacing the
 * dark-mode lesson implementation.
 */
@Suppress("UNUSED_PARAMETER")
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
        modifier = modifier,
    )
}
