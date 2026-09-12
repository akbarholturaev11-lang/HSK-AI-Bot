package com.pomp.hskai.feature.dictionary

import androidx.compose.runtime.Composable

/**
 * Source-compatible entry used by MainActivity.
 *
 * The original Android dictionary call site only knew list/search callbacks.
 * Detail actions now belong to the same DictionaryViewModel and are exposed by
 * the state controller, so opening a row really enters the native Mini App
 * parity detail instead of falling into the old no-op default callbacks.
 */
@Composable
fun DictionaryScreen(
    state: DictionaryUiState,
    onQueryChange: (String) -> Unit,
    onRetry: () -> Unit,
    onBack: () -> Unit,
) {
    val controller = state.controller
    DictionaryScreen(
        state = state,
        onQueryChange = onQueryChange,
        onRetry = onRetry,
        onBack = onBack,
        onOpenWord = { word -> controller?.openWord(word) },
        onCloseWord = { controller?.closeWord() },
        onPreviousCharacter = { controller?.previousCharacter() },
        onNextCharacter = { controller?.nextCharacter() },
        onPreviousStroke = { controller?.previousStroke() },
        onNextStroke = { controller?.nextStroke() },
        onPlayStrokeOrder = { controller?.playStrokeOrder() },
        onPauseStrokeOrder = { controller?.pauseStrokeOrder() },
        onNextWord = { controller?.nextWord() },
    )
}
