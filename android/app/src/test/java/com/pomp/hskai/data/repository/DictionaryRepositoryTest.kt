package com.pomp.hskai.data.repository

import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.AndroidCourseApi
import com.pomp.hskai.data.api.CourseCompleteRequest
import com.pomp.hskai.data.api.CourseCompleteResponse
import com.pomp.hskai.data.api.CourseLessonResponse
import com.pomp.hskai.data.api.CourseMapDto
import com.pomp.hskai.data.api.DictionaryResponse
import com.pomp.hskai.data.api.DictionaryWordDto
import com.pomp.hskai.data.api.LanguageRequest
import com.pomp.hskai.data.api.NotificationsRequest
import com.pomp.hskai.data.api.OkResponse
import com.pomp.hskai.data.api.RewardChestOpenResponse
import com.pomp.hskai.data.api.StrokeDataDto
import com.pomp.hskai.data.api.LessonUnlockRequest
import com.pomp.hskai.data.api.LessonUnlockResponse
import com.pomp.hskai.data.local.DictionaryDao
import com.pomp.hskai.data.local.DictionaryMetaEntity
import com.pomp.hskai.data.local.DictionaryWordEntity
import kotlinx.coroutines.test.runTest
import okhttp3.ResponseBody
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import retrofit2.Response

private class FakeDictionaryDao : DictionaryDao {
    val rows = mutableMapOf<String, DictionaryWordEntity>()
    var meta: DictionaryMetaEntity? = null

    override suspend fun meta(): DictionaryMetaEntity? = meta

    override suspend fun count(): Int = rows.size

    override suspend fun all(limit: Int): List<DictionaryWordEntity> =
        rows.values.sortedBy { it.position }.take(limit)

    override suspend fun search(
        query: String,
        plain: String,
        limit: Int,
    ): List<DictionaryWordEntity> {
        val q = query.lowercase()
        val p = plain.lowercase()
        return rows.values
            .asSequence()
            .filter {
                it.hanzi.lowercase().contains(q) ||
                    it.pinyinPlain.lowercase().contains(p) ||
                    it.meaning.lowercase().contains(q)
            }
            .sortedBy { it.position }
            .take(limit)
            .toList()
    }

    override suspend fun insertAll(words: List<DictionaryWordEntity>) {
        words.forEach { rows[it.hanzi] = it }
    }

    override suspend fun setMeta(meta: DictionaryMetaEntity) {
        this.meta = meta
    }

    override suspend fun clearWords() {
        rows.clear()
    }

    override suspend fun clearMeta() {
        meta = null
    }
}

private class FakeBundledDictionarySource(
    private val words: List<DictionaryWordEntity>,
) : BundledDictionarySource {
    override suspend fun load(language: AppLanguage): BundledDictionary =
        BundledDictionary(
            version = "asset-v1",
            language = language.backendCode,
            words = words,
        )
}

private class DictionaryApi(
    private val notModified: Boolean = false,
) : AndroidCourseApi {
    var calls = 0

    override suspend fun unlockLesson(
        authorization: String,
        body: LessonUnlockRequest,
    ): Response<LessonUnlockResponse> = throw NotImplementedError()

    override suspend fun dictionary(
        authorization: String,
        ifNoneMatch: String?,
    ): Response<DictionaryResponse> {
        calls++
        if (notModified) {
            return Response.error(304, ByteArray(0).toResponseBody(null))
        }
        return Response.success(
            DictionaryResponse(
                ok = true,
                version = "server-v2",
                language = "uz",
                words = listOf(
                    DictionaryWordDto(
                        hanzi = "新",
                        pinyin = "xīn",
                        meaning = "yangi",
                        level = "HSK1",
                    )
                ),
            )
        )
    }

    override suspend fun courseMap(
        authorization: String,
        timezoneOffsetMinutes: Int,
    ): Response<CourseMapDto> = throw NotImplementedError()

    override suspend fun lesson(
        authorization: String,
        lessonOrder: Int,
        accessRef: String,
    ): Response<CourseLessonResponse> = throw NotImplementedError()

    override suspend fun stroke(
        authorization: String,
        char: String,
    ): Response<StrokeDataDto> = throw NotImplementedError()

    override suspend fun tts(
        authorization: String,
        text: String,
        rate: String,
    ): Response<ResponseBody> = throw NotImplementedError()

    override suspend fun complete(
        authorization: String,
        body: CourseCompleteRequest,
    ): Response<CourseCompleteResponse> = throw NotImplementedError()

    override suspend fun openRewardChest(
        authorization: String,
    ): Response<RewardChestOpenResponse> = throw NotImplementedError()

    override suspend fun setLanguage(
        authorization: String,
        body: LanguageRequest,
    ): Response<OkResponse> = throw NotImplementedError()

    override suspend fun setNotifications(
        authorization: String,
        body: NotificationsRequest,
    ): Response<OkResponse> = throw NotImplementedError()
}

class DictionaryRepositoryTest {
    @Test
    fun `bundled dictionary seeds offline cache before network is available`() = runTest {
        val dao = FakeDictionaryDao()
        val repository = DictionaryRepository(
            api = DictionaryApi(),
            accessToken = { ApiResult.Failure(ApiError.Offline) },
            dao = dao,
            bundledSource = FakeBundledDictionarySource(sampleWords(251)),
        )

        val result = repository.sync(AppLanguage.UZBEK)
        val words = repository.search("")

        assertTrue(result is ApiResult.Success)
        assertEquals(251, (result as ApiResult.Success).value)
        assertEquals(251, words.size)
        assertEquals("HSK4", words.last().level)
        assertEquals("离线词250", words.last().hanzi)
    }

    @Test
    fun `etag check is skipped inside ttl and repeated at expiry`() = runTest {
        val dao = FakeDictionaryDao()
        dao.insertAll(sampleWords(3))
        dao.setMeta(DictionaryMetaEntity(version = "asset-v1", language = "uz"))
        val api = DictionaryApi(notModified = true)
        var now = 100_000L
        var checkedAt: Long? = null
        var checkedClient: Int? = null
        val repository = DictionaryRepository(
            api = api,
            accessToken = { ApiResult.Success("token") },
            dao = dao,
            clientVersionCode = 7,
            readLastCheckedAtMillis = { checkedAt },
            readLastCheckedClientVersion = { checkedClient },
            writeLastChecked = { _, at, version ->
                checkedAt = at
                checkedClient = version
            },
            now = { now },
        )

        repository.sync(AppLanguage.UZBEK)
        assertEquals(1, api.calls)
        assertEquals(now, checkedAt)
        assertEquals(7, checkedClient)

        now += DICTIONARY_CHECK_TTL_MILLIS - 1
        repository.sync(AppLanguage.UZBEK)
        assertEquals(1, api.calls)

        now += 1
        repository.sync(AppLanguage.UZBEK)
        assertEquals(2, api.calls)
    }

    @Test
    fun `new android version invalidates a fresh dictionary check`() = runTest {
        val dao = FakeDictionaryDao()
        dao.insertAll(sampleWords(3))
        dao.setMeta(DictionaryMetaEntity(version = "asset-v1", language = "uz"))
        val api = DictionaryApi(notModified = true)
        val now = 500_000L
        val repository = DictionaryRepository(
            api = api,
            accessToken = { ApiResult.Success("token") },
            dao = dao,
            clientVersionCode = 8,
            readLastCheckedAtMillis = { now - 1_000L },
            readLastCheckedClientVersion = { 7 },
            writeLastChecked = { _, _, _ -> },
            now = { now },
        )

        repository.sync(AppLanguage.UZBEK)

        assertEquals(1, api.calls)
    }

    @Test
    fun `default dictionary list is not capped at hsk2 sized first page`() = runTest {
        val dao = FakeDictionaryDao()
        dao.insertAll(sampleWords(251))
        dao.setMeta(DictionaryMetaEntity(version = "asset-v1", language = "uz"))
        val repository = DictionaryRepository(
            api = DictionaryApi(),
            accessToken = { ApiResult.Success("token") },
            dao = dao,
        )

        val words = repository.search("")

        assertEquals(251, words.size)
        assertEquals("离线词250", words.last().hanzi)
        assertEquals("HSK4", words.last().level)
    }

    private fun sampleWords(count: Int): List<DictionaryWordEntity> =
        (0 until count).map { index ->
            DictionaryWordEntity(
                hanzi = "离线词$index",
                pinyin = "lixian ci $index",
                pinyinPlain = "lixian ci $index",
                meaning = "offline word $index",
                level = if (index < 200) "HSK2" else "HSK4",
                position = index,
            )
        }
}
