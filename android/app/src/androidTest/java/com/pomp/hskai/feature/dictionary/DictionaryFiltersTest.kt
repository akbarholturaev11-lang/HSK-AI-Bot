package com.pomp.hskai.feature.dictionary

import android.graphics.Bitmap
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performTextReplacement
import androidx.compose.ui.test.hasSetTextAction
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.isRoot
import androidx.compose.ui.test.onLast
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.ViewModelStore
import androidx.room.Room
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.pomp.hskai.R
import com.pomp.hskai.core.audio.LessonAudioPlayer
import com.pomp.hskai.core.design.PompHskAiTheme
import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.AndroidCourseApi
import com.pomp.hskai.data.local.HskAiDatabase
import com.pomp.hskai.data.repository.AssetBundledDictionarySource
import com.pomp.hskai.data.repository.CourseRepository
import com.pomp.hskai.data.repository.DictionaryRepository
import java.lang.reflect.Proxy
import java.io.File
import kotlinx.coroutines.runBlocking
import kotlinx.serialization.json.Json
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** Real bundled words, Room queries, ViewModel filtering and the rendered filter sheet. */
@RunWith(AndroidJUnit4::class)
class DictionaryFiltersTest {
    @get:Rule val compose = createComposeRule()
    private val context = InstrumentationRegistry.getInstrumentation().targetContext
    private val database = Room.inMemoryDatabaseBuilder(context, HskAiDatabase::class.java).build()
    private val store = ViewModelStore()
    private lateinit var vm: DictionaryViewModel
    private val source = AssetBundledDictionarySource(context, Json { ignoreUnknownKeys = true })

    private fun save(name: String) {
        compose.waitForIdle()
        val bitmap = compose.onAllNodes(isRoot()).onLast().captureToImage().asAndroidBitmap()
        val directory = File(context.filesDir, "dictionary-filters").apply { mkdirs() }
        File(directory, "$name.png").outputStream().use { bitmap.compress(Bitmap.CompressFormat.PNG, 100, it) }
    }

    @After fun close() {
        InstrumentationRegistry.getInstrumentation().runOnMainSync { store.clear() }
        database.close()
    }

    private fun openDictionary() {
        val api = Proxy.newProxyInstance(
            AndroidCourseApi::class.java.classLoader, arrayOf(AndroidCourseApi::class.java),
        ) { _, method, _ -> error("Unexpected request: ${method.name}") } as AndroidCourseApi
        val offline: suspend () -> ApiResult<String> = { ApiResult.Failure(ApiError.Offline) }
        val factory = DictionaryViewModel.Factory(
            DictionaryRepository(api, offline, database.dictionaryDao(), bundledSource = source),
            CourseRepository(api, offline, database.courseMapDao(), json = Json),
            object : LessonAudioPlayer {
                override suspend fun play(mp3: ByteArray, speed: Float) = Unit
                override fun release() = Unit
            }, AppLanguage.UZBEK,
        )
        InstrumentationRegistry.getInstrumentation().runOnMainSync {
            vm = ViewModelProvider(store, factory)[DictionaryViewModel::class.java]
        }
        val actions = DictionaryActions(
            onQueryChange = vm::onQueryChange, onVersionFilter = vm::selectVersionFilter,
            onLevelFilter = vm::selectLevelFilter, onRetry = vm::load,
            onOpenWord = vm::openWord, onOpenRecent = vm::openRecent, onCloseWord = vm::closeWord,
            onPreviousCharacter = {}, onNextCharacter = {}, onPlayStrokeOrder = {},
            onToggleStrokePlayback = {}, onPauseStrokePlayback = {}, onPreviousStroke = {}, onNextStroke = {},
            onStrokeComplete = {}, onStrokeAnimationFinished = {}, onPlayAudio = {},
            onPreviousWord = {}, onNextWord = {}, onStartWriting = {}, onCloseWriting = {},
            onWritingDemoAgain = {}, onBeginWriting = {}, onWritingStroke = {}, onWritingHint = {},
            onRestartWritingRound = {}, onWriteAgain = {}, onWriteNextCharacter = {}, onBack = {},
        )
        compose.setContent {
            val state by vm.state.collectAsState()
            PompHskAiTheme { DictionaryScreen(state, actions) }
        }
        compose.waitUntil(10_000) { !vm.state.value.isLoading && vm.state.value.total > 1_000 }
    }

    @Test fun everyRealLevelMatchesItsSourceMembershipAndLegacyBadgesHaveNo30() = runBlocking {
        val words = requireNotNull(source.load(AppLanguage.UZBEK)).words.map {
            com.pomp.hskai.data.repository.DictionaryWord(it.hanzi, it.pinyin, it.meaning, it.level)
        }
        assertTrue(words.size > 1_500)
        for ((version, prefix, levelPrefix, max) in listOf(
            arrayOf("hsk20", "HSK", "hsk", "4"), arrayOf("hsk30", "N", "nhsk", "3"),
        )) {
            for (band in 1..max.toInt()) {
                val expected = words.filter { word -> word.level.split('|').any { it.substringBefore(' ') == "$prefix$band" } }.map { it.hanzi }.toSet()
                val filtered = words.filter { dictionaryWordMatches(it, version, "$levelPrefix$band") }
                assertTrue(expected.isNotEmpty())
                assertEquals(expected, filtered.map { it.hanzi }.toSet())
                if (version == "hsk20") assertTrue(filtered.none { "3.0" in dictionaryLevelLabel(it.level, version) })
            }
        }
        val yao = words.single { it.hanzi == "要" }
        assertEquals("HSK2", dictionaryLevelLabel(yao.level, "hsk20", "hsk2"))
        assertTrue(dictionaryLevelLabel(yao.level, "hsk30", "nhsk1").contains("3.0"))
    }

    @Test fun filtersOpenFromTheIconAndBothVersionsWorkWithRoomSearch() {
        openDictionary()
        val allVersions = context.getString(R.string.dictionary_filter_all_versions)
        val allLevels = context.getString(R.string.dictionary_filter_all_levels)
        compose.onNodeWithText(allVersions).assertDoesNotExist()
        compose.onNodeWithText(allLevels).assertDoesNotExist()
        compose.onNodeWithContentDescription(context.getString(R.string.dictionary_filters)).performClick()
        save("filter-sheet")
        compose.onNodeWithText("HSK 2.0").performClick()
        compose.onNodeWithText("HSK 2").performScrollTo().performClick()
        compose.waitUntil(5_000) { vm.state.value.words.isNotEmpty() && vm.state.value.words.all { "HSK2" in it.level.split('|') } }
        val oldCount = vm.state.value.words.size
        compose.onNodeWithText(context.getString(R.string.dictionary_filter_results, oldCount)).performClick()
        compose.onNodeWithText(oldCount.toString()).assertExists()
        compose.onNodeWithText(allVersions).assertDoesNotExist()
        compose.onNode(hasSetTextAction()).performTextReplacement("要")
        compose.waitUntil(5_000) { vm.state.value.query == "要" && vm.state.value.words.size == 1 }
        compose.onNodeWithText("HSK2").assertExists()
        compose.onNodeWithText("N1 (3.0)").assertDoesNotExist()
        compose.onNodeWithText("1").assertExists()
        save("legacy-result")

        compose.onNodeWithContentDescription(context.getString(R.string.dictionary_filters)).performClick()
        compose.onNodeWithText("HSK 3.0").performClick()
        compose.onNodeWithText("N1").performClick()
        compose.waitUntil(5_000) {
            vm.state.value.versionFilter == "hsk30" && vm.state.value.levelFilter == "nhsk1" &&
                vm.state.value.words.map { it.hanzi }.toSet() == setOf("要", "不要")
        }
        compose.onNodeWithText(context.getString(R.string.dictionary_filter_results, 2)).performClick()
        compose.onNodeWithText("不要").assertExists()
        compose.onNodeWithText("HSK2").assertDoesNotExist()
        save("new-version-result")
        // The detail must use the same version projection as the list.
        compose.onNode(hasText("要") and !hasSetTextAction()).performClick()
        compose.onNodeWithText("N1 (3.0)").assertExists()
        compose.onNodeWithText("HSK2").assertDoesNotExist()
    }
}
