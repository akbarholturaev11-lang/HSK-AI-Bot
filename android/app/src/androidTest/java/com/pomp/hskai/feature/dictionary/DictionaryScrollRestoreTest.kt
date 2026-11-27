package com.pomp.hskai.feature.dictionary

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasScrollToIndexAction
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performScrollToIndex
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.data.repository.DictionaryWord
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Opening an entry replaces the list in composition. Coming back must land on
 * the row the learner left, not jump to the top of a 5,000-word list.
 */
@RunWith(AndroidJUnit4::class)
class DictionaryScrollRestoreTest {

    @get:Rule
    val compose = createComposeRule()

    private val words = (0 until 300).map { DictionaryWord("字$it", "zi$it", "word $it", "HSK 1") }

    @Test
    fun closingAWordReturnsToTheSameListPosition() {
        var state by mutableStateOf(DictionaryUiState(isLoading = false, words = words, total = words.size))
        compose.setContent {
            PompHskAiTheme { DictionaryScreen(state = state, actions = noActions()) }
        }
        compose.onNode(hasScrollToIndexAction()).performScrollToIndex(120)
        compose.onNodeWithText("字120").assertIsDisplayed()

        compose.runOnIdle { state = state.copy(selectedWord = words[121]) }
        compose.onNodeWithText("字0").assertDoesNotExist()
        compose.runOnIdle { state = state.copy(selectedWord = null) }

        compose.onNodeWithText("字120").assertIsDisplayed()
        compose.onNodeWithText("字0").assertDoesNotExist()
    }

    private fun noActions() = DictionaryActions(
        onQueryChange = {},
        onRetry = {},
        onOpenWord = {},
        onOpenRecent = {},
        onCloseWord = {},
        onPreviousCharacter = {},
        onNextCharacter = {},
        onPlayStrokeOrder = {},
        onToggleStrokePlayback = {},
        onPauseStrokePlayback = {},
        onPreviousStroke = {},
        onNextStroke = {},
        onStrokeComplete = {},
        onStrokeAnimationFinished = {},
        onPlayAudio = {},
        onPreviousWord = {},
        onNextWord = {},
        onStartWriting = {},
        onCloseWriting = {},
        onWritingDemoAgain = {},
        onBeginWriting = {},
        onWritingStroke = {},
        onWritingHint = {},
        onRestartWritingRound = {},
        onWriteAgain = {},
        onWriteNextCharacter = {},
        onBack = {},
    )
}
