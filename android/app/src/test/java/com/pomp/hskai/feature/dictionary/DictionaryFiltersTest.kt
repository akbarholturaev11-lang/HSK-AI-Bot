package com.pomp.hskai.feature.dictionary

import com.pomp.hskai.core.audio.LessonAudioPlayer
import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.AndroidCourseApi
import com.pomp.hskai.data.local.CourseMapDao
import com.pomp.hskai.data.local.DictionaryDao
import com.pomp.hskai.data.local.DictionaryMetaEntity
import com.pomp.hskai.data.local.DictionaryWordEntity
import com.pomp.hskai.data.repository.CourseRepository
import com.pomp.hskai.data.repository.DictionaryRepository
import com.pomp.hskai.data.repository.DictionaryWord
import java.lang.reflect.Proxy
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import kotlinx.serialization.json.Json
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class DictionaryFiltersTest {
    private val dispatcher = StandardTestDispatcher()
    @Before fun setUp() { Dispatchers.setMain(dispatcher) }
    @After fun tearDown() { Dispatchers.resetMain() }

    private val shared = DictionaryWord("要", "yào", "kerak", "HSK2|N1")
    private val oldOnly = DictionaryWord("阿姨", "āyí", "xola", "HSK3")
    private val newOnly = DictionaryWord("外卖", "wàimài", "yetkazib berish", "N2")

    @Test fun versionAndLevelMembershipRemainIndependentForSharedWords() {
        assertTrue(dictionaryWordMatches(shared, "hsk20", "hsk2"))
        assertTrue(dictionaryWordMatches(shared, "hsk30", "nhsk1"))
        assertFalse(dictionaryWordMatches(shared, "hsk20", "hsk1"))
        assertFalse(dictionaryWordMatches(shared, "hsk30", "nhsk2"))
        assertFalse(dictionaryWordMatches(shared, "hsk20", "nhsk1"))
        assertFalse(dictionaryWordMatches(shared, "hsk30", "hsk2"))
        assertFalse(dictionaryWordMatches(oldOnly, "hsk30", "all"))
        assertFalse(dictionaryWordMatches(newOnly, "hsk20", "all"))
        assertTrue(dictionaryWordMatches(newOnly, "all", "nhsk2"))
    }

    @Test fun legacySelectionNeverShowsTheNewVersionBadge() {
        assertEquals("HSK2", dictionaryLevelLabel(shared.level, "hsk20", "all"))
        assertEquals("HSK2", dictionaryLevelLabel(shared.level, "all", "hsk2"))
        assertEquals("N1 (3.0)", dictionaryLevelLabel(shared.level, "hsk30", "all"))
        assertEquals("N1 (3.0)", dictionaryLevelLabel(shared.level, "all", "nhsk1"))
        assertEquals("HSK2 · N1 (3.0)", dictionaryLevelLabel(shared.level))
        assertEquals("", dictionaryLevelLabel(newOnly.level, "hsk20"))
    }

    @Test fun bothAuthoredPartsOfHsk4BelongToTheHsk4Filter() {
        for (part in listOf("HSK4 (1-qism)", "HSK4 (2-qism)|N3")) {
            val word = shared.copy(level = part)
            assertTrue(dictionaryWordMatches(word, "hsk20", "hsk4"))
            assertFalse(dictionaryWordMatches(word, "hsk20", "hsk3"))
            assertEquals("HSK4", dictionaryLevelLabel(part, "hsk20", "hsk4"))
        }
    }

    private class Dao : DictionaryDao {
        val rows = listOf(
            DictionaryWordEntity("要", "yào", "yao", "kerak", "HSK2|N1", 0),
            DictionaryWordEntity("外卖", "wàimài", "waimai", "yetkazib berish", "N2", 1),
        )
        var nextRead: CompletableDeferred<List<DictionaryWordEntity>>? = null
        override suspend fun meta() = DictionaryMetaEntity(version = "test", language = "uz")
        override suspend fun count() = rows.size
        override suspend fun all(limit: Int): List<DictionaryWordEntity> {
            val pending = nextRead
            nextRead = null
            return pending?.await() ?: rows.take(limit)
        }
        override suspend fun search(query: String, plain: String, limit: Int) = rows.filter { query in it.hanzi }.take(limit)
        override suspend fun insertAll(words: List<DictionaryWordEntity>) = error("Unexpected cache mutation")
        override suspend fun setMeta(meta: DictionaryMetaEntity) = error("Unexpected cache mutation")
        override suspend fun clearWords() = error("Unexpected cache mutation")
        override suspend fun clearMeta() = error("Unexpected cache mutation")
    }

    @Suppress("UNCHECKED_CAST")
    private inline fun <reified T> unused(): T = Proxy.newProxyInstance(
        T::class.java.classLoader, arrayOf(T::class.java),
    ) { _, method, _ -> error("Unexpected dependency: ${method.name}") } as T

    @Test fun anOlderQueryCannotOverwriteNewerVersionAndLevelFilters() = runTest(dispatcher) {
        val dao = Dao()
        val api = unused<AndroidCourseApi>()
        val offline: suspend () -> ApiResult<String> = { ApiResult.Failure(ApiError.Offline) }
        val repository = DictionaryRepository(api, offline, dao)
        val vm = DictionaryViewModel(
            repository, CourseRepository(api, offline, unused<CourseMapDao>(), json = Json),
            object : LessonAudioPlayer {
                override suspend fun play(mp3: ByteArray, speed: Float) = Unit
                override fun release() = Unit
            }, AppLanguage.UZBEK,
        )
        runCurrent()
        val delayed = CompletableDeferred<List<DictionaryWordEntity>>()
        dao.nextRead = delayed
        vm.selectVersionFilter("hsk20"); runCurrent()
        vm.selectVersionFilter("hsk30"); runCurrent()
        vm.selectLevelFilter("nhsk2"); runCurrent()
        assertEquals(listOf("外卖"), vm.state.value.words.map { it.hanzi })
        delayed.complete(dao.rows); runCurrent()
        assertEquals(listOf("外卖"), vm.state.value.words.map { it.hanzi })
        assertEquals("nhsk2", vm.state.value.levelFilter)
        vm.selectLevelFilter("hsk2"); runCurrent()
        assertEquals("nhsk2", vm.state.value.levelFilter)
        vm.selectVersionFilter("hsk20"); runCurrent()
        assertEquals("all", vm.state.value.levelFilter)
        assertEquals(listOf("要"), vm.state.value.words.map { it.hanzi })
    }
}
