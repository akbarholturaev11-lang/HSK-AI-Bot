package com.pomp.hskai.feature.dictionary

import android.graphics.Bitmap
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.hasScrollAction
import androidx.compose.ui.test.hasSetTextAction
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollToNode
import androidx.compose.ui.test.performTextInput
import androidx.compose.ui.test.performTouchInput
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.core.hanzi.CharacterStrokes
import com.pomp.hskai.core.hanzi.HanziGrid
import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.core.settings.AppSettings
import com.pomp.hskai.core.settings.AppThemeMode
import com.pomp.hskai.data.local.BundledDictionaryInsights
import com.pomp.hskai.data.local.BundledStrokes
import com.pomp.hskai.data.repository.DictionaryWord
import java.io.File
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * The dictionary entry drawn from the material inside the APK, and a
 * character written on it by touch.
 *
 * The handwriting test goes through the real pointer pipeline: a stroke is
 * swiped along the character's own centre line in screen pixels and has to
 * come out the other end, through [HanziGrid.toGrid] and the matcher, as the
 * right stroke. If drawing and touch disagreed on where the character is,
 * nothing would pass.
 */
@RunWith(AndroidJUnit4::class)
class DictionaryEntryTest {

    @get:Rule
    val compose = createComposeRule()

    private val context = InstrumentationRegistry.getInstrumentation().targetContext
    private val strokes = BundledStrokes(context)
    private val insights = BundledDictionaryInsights(context)

    private fun entry(word: DictionaryWord, neighbours: List<DictionaryWord> = emptyList()): DictionaryUiState =
        runBlocking {
            val characters = word.hanzi.filter { it in '\u4E00'..'\u9FFF' }.map { it.toString() }
            val first = requireNotNull(strokes.find(characters.first()))
            DictionaryUiState(
                isLoading = false,
                words = neighbours.ifEmpty { listOf(word) },
                total = 1247,
                selectedWord = word,
                characters = characters,
                strokes = first,
                visibleStrokeCount = first.size,
                examples = insights.examples(word.hanzi, AppLanguage.UZBEK),
                breakdowns = characters.distinct().mapNotNull { insights.breakdown(it, AppLanguage.UZBEK) },
            )
        }

    private val noActions = DictionaryActions(
        onQueryChange = {}, onRetry = {}, onOpenWord = {}, onOpenRecent = {}, onCloseWord = {},
        onPreviousCharacter = {}, onNextCharacter = {}, onPlayStrokeOrder = {},
        onToggleStrokePlayback = {}, onPauseStrokePlayback = {}, onPreviousStroke = {}, onNextStroke = {},
        onStrokeComplete = {}, onStrokeAnimationFinished = {}, onPlayAudio = {},
        onPreviousWord = {}, onNextWord = {}, onStartWriting = {}, onCloseWriting = {},
        onWritingDemoAgain = {}, onBeginWriting = {}, onWritingStroke = {}, onWritingHint = {},
        onRestartWritingRound = {}, onWriteAgain = {}, onWriteNextCharacter = {}, onBack = {},
    )

    @Test
    fun entryShowsTheWordItsPartsAndRealExamples() {
        val hao = DictionaryWord("好", "hǎo", "yaxshi, ajoyib", "HSK1")
        val neighbours = listOf(
            DictionaryWord("你", "nǐ", "sen", "HSK1"),
            hao,
            DictionaryWord("您", "nín", "siz", "HSK1"),
        )
        val state = entry(hao, neighbours)
        assertTrue(state.examples.isNotEmpty())
        compose.setContent { PompHskAiTheme { DictionaryScreen(state, noActions) } }

        compose.onNodeWithText("hǎo").assertExists()
        compose.onNodeWithText(context.getString(R.string.dictionary_action_write)).assertExists()
        compose.onNodeWithText("你").assertExists()
        compose.onNodeWithText("您").assertExists()
        save("entry_hao_top")

        compose.onNode(hasScrollAction()).performScrollToNode(hasText(context.getString(R.string.dictionary_parts_title)))
        compose.onNodeWithText("女").assertExists()
        compose.onNodeWithText("子").assertExists()
        save("entry_hao_parts")

        compose.onNode(hasScrollAction()).performScrollToNode(hasText(state.examples.last().translation))
        save("entry_hao_examples")
    }

    @Test
    fun singleCharacterEntryShowsItsHanziInTheHeading() {
        val mei = DictionaryWord("每", "měi", "har bir", "HSK2")
        val state = DictionaryUiState(
            isLoading = false,
            words = listOf(mei),
            total = 1,
            selectedWord = mei,
            characters = listOf("每"),
        )

        compose.setContent { PompHskAiTheme { DictionaryScreen(state, noActions) } }

        compose.onNodeWithText("每").assertExists()
        compose.onNodeWithText("měi").assertExists()
        compose.onNodeWithText("har bir").assertExists()
        save("entry_mei_single_character")
    }

    @Test
    fun theHistoryShowsOnlyWhileTheSearchBoxIsFocused() {
        val hao = DictionaryWord("好", "hǎo", "yaxshi, ajoyib", "HSK1")
        val xuexi = DictionaryWord("学习", "xuéxí", "o'qimoq, o'rganmoq", "HSK1")
        val list = listOf(
            DictionaryWord("你", "nǐ", "sen", "HSK1"),
            hao,
            DictionaryWord("您", "nín", "siz", "HSK1"),
            xuexi,
        )
        var screen by mutableStateOf(
            DictionaryUiState(isLoading = false, words = list, total = list.size, history = listOf(xuexi, hao)),
        )
        val actions = noActions.copy(onQueryChange = { screen = screen.copy(query = it) })
        compose.setContent { PompHskAiTheme { DictionaryScreen(screen, actions) } }
        val recent = context.getString(R.string.dictionary_recent_title)
        val search = hasSetTextAction()

        // Opening the dictionary: the list, and no history.
        compose.onNodeWithText(recent).assertDoesNotExist()
        save("history_closed")

        // Tapping search: the history first, then the list.
        compose.onNode(search).performClick()
        compose.onNodeWithText(recent).assertExists()
        compose.onNodeWithText(context.getString(R.string.dictionary_filter_all_versions)).assertExists()
        compose.onNodeWithText(context.getString(R.string.dictionary_filter_all_levels)).assertExists()
        compose.onNodeWithText(context.getString(R.string.dictionary_all_words)).assertExists()
        save("history_open")

        // Typing: the history gives way to the results.
        compose.onNode(search).performTextInput("ni")
        compose.onNodeWithText(recent).assertDoesNotExist()
    }

    @Test
    fun aPhraseIsWrittenOneCharacterAtATime() {
        val state = entry(DictionaryWord("休息", "xiūxi", "dam olmoq", "HSK2"))
        compose.setContent { PompHskAiTheme { DictionaryScreen(state, noActions) } }

        compose.onNodeWithContentDescription(context.getString(R.string.dictionary_action_order)).performClick()
        compose.onNodeWithText(context.getString(R.string.dictionary_character_position, 1, 2)).assertExists()
        compose.onNodeWithContentDescription(context.getString(R.string.action_close)).performClick()
        compose.onNodeWithText("休息").assertExists()
        save("entry_xiuxi_top")
        compose.onNode(hasScrollAction()).performScrollToNode(hasText(state.breakdowns.last().hint))
        assertEquals(listOf("休", "息"), state.breakdowns.map { it.character })
        save("entry_xiuxi_parts")
        compose.onNode(hasScrollAction()).performScrollToNode(hasText(state.examples.first().translation))
        save("entry_xiuxi_examples")
    }

    @Test
    fun aFrameEntryMarksBothHalvesOfItsExamples() {
        val state = entry(DictionaryWord("不但……而且……", "bùdàn... érqiě...", "nafaqat..., balki...", "HSK3"))
        assertTrue(state.examples.isNotEmpty())
        compose.setContent { PompHskAiTheme { DictionaryScreen(state, noActions) } }

        compose.onNode(hasScrollAction()).performScrollToNode(hasText(state.examples.last().translation))
        save("entry_frame_examples")
    }

    @Test
    fun aCharacterIsWrittenByTouchThroughAllThreeRounds() {
        val hao = requireNotNull(strokes.find("好"))
        var writing by mutableStateOf(HanziWriting.start("好", hao))
        compose.setContent {
            PompHskAiTheme {
                HanziWritingScreen(
                    writing = writing,
                    hasNextCharacter = false,
                    onClose = {},
                    onDemoAgain = { writing = HanziWriting.playDemoAgain(writing) },
                    onBegin = { writing = HanziWriting.beginWriting(writing) },
                    onStroke = { points ->
                        writing = HanziWriting.submitStroke(writing, points)
                        if (writing.isRoundComplete) writing = HanziWriting.nextRound(writing)
                    },
                    onHint = { writing = HanziWriting.hint(writing) },
                    onRestart = { writing = HanziWriting.restartRound(writing) },
                    onWriteAgain = { writing = HanziWriting.again(writing) },
                    onNextCharacter = {},
                )
            }
        }
        compose.mainClock.advanceTimeBy(4_000)
        save("writing_demo")
        // HskDepthButton sets its label in capitals.
        compose.onNodeWithText(context.getString(R.string.writing_start).uppercase()).performClick()
        assertEquals(WritingStage.TRACE, writing.stage)

        // A stroke in the wrong place is refused and said so.
        swipe(hao, strokeIndex = hao.size - 1)
        assertEquals(WritingMiss.WRONG, writing.lastMiss)
        assertEquals(0, writing.strokeIndex)
        compose.onNodeWithText(context.getString(R.string.writing_miss_wrong)).assertExists()

        repeat(3) { swipe(hao, strokeIndex = it) }
        assertEquals(3, writing.strokeIndex)
        save("writing_trace_midway")

        for (index in 3 until hao.size) swipe(hao, index)
        assertEquals(WritingStage.HINT, writing.stage)
        swipe(hao, 0)
        save("writing_hint_round")
        for (index in 1 until hao.size) swipe(hao, index)
        assertEquals(WritingStage.MEMORY, writing.stage)
        for (index in 0 until hao.size) swipe(hao, index)

        assertEquals(WritingStage.DONE, writing.stage)
        assertEquals(1, writing.totalMistakes)
        compose.onNodeWithText(context.getString(R.string.writing_done_mistakes, 1)).assertExists()
        save("writing_done")
    }

    @Test
    fun theEntryAndThePracticeReadInDarkMode() {
        val settings = AppSettings(context)
        val previous = runBlocking { settings.themeMode.first() }
        runBlocking { settings.setThemeMode(AppThemeMode.DARK) }
        try {
            val hao = DictionaryWord("好", "hǎo", "yaxshi, ajoyib", "HSK1")
            var screen by mutableStateOf(entry(hao))
            val actions = noActions.copy(
                onWritingStroke = { points ->
                    screen = screen.copy(writing = screen.writing?.let { HanziWriting.submitStroke(it, points) })
                },
            )
            compose.setContent { PompHskAiTheme { DictionaryScreen(screen, actions) } }
            compose.waitForIdle()
            save("dark_entry_hao")
            compose.onNode(hasScrollAction()).performScrollToNode(hasText(screen.examples.last().translation))
            save("dark_entry_examples")

            val strokes = screen.strokes
            screen = screen.copy(writing = HanziWriting.beginWriting(HanziWriting.start("好", strokes)))
            compose.waitForIdle()
            swipe(strokes, 0)
            swipe(strokes, 1)
            assertEquals(2, screen.writing?.strokeIndex)
            save("dark_writing_trace")
        } finally {
            runBlocking { settings.setThemeMode(previous) }
        }
    }

    /** Swipes stroke [strokeIndex] of [strokes] along its centre line, in pixels. */
    private fun swipe(strokes: CharacterStrokes, strokeIndex: Int) {
        val median = strokes.medians[strokeIndex]
        compose.onNodeWithTag(WRITING_CANVAS_TAG).performTouchInput {
            val side = minOf(width, height).toFloat()
            val points = resample(median).map { HanziGrid.toCanvas(it, side) }
            down(points.first())
            points.drop(1).forEach { moveTo(it) }
            up()
        }
        compose.waitForIdle()
    }

    private fun resample(median: List<Offset>, samples: Int = 16): List<Offset> {
        val lengths = median.zipWithNext { a, b -> (b - a).getDistance() }
        val total = lengths.sum()
        return (0 until samples).map { i ->
            var target = total * i / (samples - 1)
            var segment = 0
            while (segment < lengths.lastIndex && target > lengths[segment]) {
                target -= lengths[segment]
                segment++
            }
            val t = if (lengths[segment] == 0f) 0f else (target / lengths[segment]).coerceIn(0f, 1f)
            median[segment] + (median[segment + 1] - median[segment]) * t
        }
    }

    /** Kept on the device for `adb pull`: files/dictionary-screens/<name>.png */
    private fun save(name: String) {
        compose.waitForIdle()
        val bitmap = compose.onRoot().captureToImage().asAndroidBitmap()
        val dir = File(context.filesDir, "dictionary-screens").apply { mkdirs() }
        File(dir, "$name.png").outputStream().use { bitmap.compress(Bitmap.CompressFormat.PNG, 100, it) }
    }
}
