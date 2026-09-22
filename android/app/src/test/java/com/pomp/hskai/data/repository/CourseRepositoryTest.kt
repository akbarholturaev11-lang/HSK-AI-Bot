package com.pomp.hskai.data.repository

import androidx.compose.ui.geometry.Offset
import com.pomp.hskai.core.audio.TtsCache
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.AndroidCourseApi
import com.pomp.hskai.data.api.AndroidFoundationApi
import com.pomp.hskai.data.api.FoundationCompleteRequest
import com.pomp.hskai.data.api.FoundationCompleteResponse
import com.pomp.hskai.data.api.FoundationPayloadDto
import com.pomp.hskai.data.api.FoundationResponseDto
import com.pomp.hskai.data.api.CourseFoundationDto
import com.pomp.hskai.data.api.CourseCompleteRequest
import com.pomp.hskai.data.api.CourseCompleteResponse
import com.pomp.hskai.data.api.CourseLessonDto
import com.pomp.hskai.data.api.CourseLessonResponse
import com.pomp.hskai.data.api.CourseMapDto
import com.pomp.hskai.data.api.StrokeDataDto
import com.pomp.hskai.data.api.DictionaryResponse
import com.pomp.hskai.data.api.CourseUnitDto
import com.pomp.hskai.data.api.CourseUserDto
import com.pomp.hskai.data.api.LanguageRequest
import com.pomp.hskai.data.api.NotificationsRequest
import com.pomp.hskai.data.api.LocalizedText
import com.pomp.hskai.data.api.OkResponse
import com.pomp.hskai.data.api.RewardChestOpenResponse
import com.pomp.hskai.data.api.LessonUnlockRequest
import com.pomp.hskai.data.api.LessonUnlockResponse
import com.pomp.hskai.data.local.CourseMapCacheEntity
import com.pomp.hskai.data.local.CourseMapDao
import com.pomp.hskai.data.local.LessonCacheDao
import com.pomp.hskai.data.local.LessonCacheEntity
import com.pomp.hskai.domain.model.LessonAccess
import java.io.IOException
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import okhttp3.ResponseBody
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import retrofit2.Response

private class FakeCourseMapDao : CourseMapDao {
    val rows = mutableMapOf<String, CourseMapCacheEntity>()
    var clearCalls = 0

    override suspend fun find(level: String) = rows[level]

    override suspend fun findMostRecent() = rows.values.maxByOrNull { it.fetchedAtMillis }

    override suspend fun upsert(entity: CourseMapCacheEntity) {
        rows[entity.level] = entity
    }

    override suspend fun clear() {
        clearCalls++
        rows.clear()
    }
}

private class FakeLessonCacheDao : LessonCacheDao {
    val rows = mutableMapOf<Pair<String, Int>, LessonCacheEntity>()
    var clearCalls = 0

    override suspend fun find(level: String, lessonOrder: Int) = rows[level to lessonOrder]

    override suspend fun upsert(entity: LessonCacheEntity) {
        rows[entity.level to entity.lessonOrder] = entity
    }

    override suspend fun clear() {
        clearCalls++
        rows.clear()
    }
}

private class FakeTtsCache : TtsCache {
    val entries = mutableMapOf<String, ByteArray>()
    var cleared = 0

    override suspend fun read(key: String): ByteArray? = entries[key]

    override suspend fun write(key: String, audio: ByteArray) {
        entries[key] = audio
    }

    override suspend fun clear() {
        cleared++
        entries.clear()
    }
}

private val lessonPayload = Json.parseToJsonElement(
    """{"source_lesson":1,"part_no":1,"part_count":1,"checkpoint":false,"title":{"uz":"1-dars"},"subtitle":{"uz":"1-qism"},"sections":[{"section_no":1,"cards":[{"type":"pronunciation","phrase":"你好","pinyin":"nǐ hǎo","translation":{"uz":"salom"}},{"type":"tone_drill_v2"}]}]}"""
).jsonObject

private open class FakeCourseApi : AndroidCourseApi {
    var lastAuthorization: String? = null
    var lastTimezoneOffset: Int? = null

    /** Counted so a cache read can be proven to touch nothing. */
    var mapCalls = 0

    override suspend fun courseMap(
        authorization: String,
        timezoneOffsetMinutes: Int,
    ): Response<CourseMapDto> {
        mapCalls++
        lastAuthorization = authorization
        lastTimezoneOffset = timezoneOffsetMinutes
        return Response.success(sampleMap())
    }

    override suspend fun lesson(
        authorization: String,
        lessonOrder: Int,
        accessRef: String,
    ): Response<CourseLessonResponse> = throw NotImplementedError()

    override suspend fun stroke(
        authorization: String,
        char: String,
    ): Response<StrokeDataDto> = Response.success(
        StrokeDataDto(
            strokes = listOf("M 0 0 L 100 0 L 100 20 L 0 20 Z"),
            medians = listOf(listOf(listOf(0f, 10f), listOf(100f, 10f))),
        )
    )

    override suspend fun unlockLesson(
        authorization: String,
        body: LessonUnlockRequest,
    ): Response<LessonUnlockResponse> = throw NotImplementedError()


    var ttsCalls = 0

    override suspend fun tts(
        authorization: String,
        text: String,
        rate: String,
    ): Response<ResponseBody> {
        ttsCalls++
        return Response.success("audio".toResponseBody())
    }

    override suspend fun complete(
        authorization: String,
        body: CourseCompleteRequest,
    ): Response<CourseCompleteResponse> = throw NotImplementedError()

    override suspend fun openRewardChest(
        authorization: String,
    ): Response<RewardChestOpenResponse> = Response.success(
        RewardChestOpenResponse(ok = true, rewardType = "xp", rewardValue = 10)
    )

    override suspend fun setLanguage(
        authorization: String,
        body: LanguageRequest,
    ): Response<OkResponse> = Response.success(OkResponse(ok = true))

    override suspend fun setNotifications(
        authorization: String,
        body: NotificationsRequest,
    ): Response<OkResponse> = Response.success(OkResponse(ok = true))

    override suspend fun dictionary(
        authorization: String,
        ifNoneMatch: String?,
    ): Response<DictionaryResponse> = Response.success(DictionaryResponse(ok = true))
}

private open class FakeFoundationApi(
    private val completion: FoundationCompleteResponse = FoundationCompleteResponse(
        ok = true,
        foundation = CourseFoundationDto(required = true, completed = true, status = "completed"),
    ),
    private val statusCompleted: Boolean = true,
) : AndroidFoundationApi {
    var foundationCalls = 0
    var completionCalls = 0

    override suspend fun foundation(
        authorization: String,
    ): Response<FoundationResponseDto> {
        foundationCalls++
        return Response.success(
            FoundationResponseDto(
                ok = true,
                foundation = FoundationPayloadDto(
                    requiredObjectives = listOf("meaning", "build", "listen"),
                    cards = listOf(lessonPayload),
                ),
                status = CourseFoundationDto(
                    required = true,
                    completed = statusCompleted,
                    status = if (statusCompleted) "completed" else "required",
                ),
            )
        )
    }

    override suspend fun completeFoundation(
        authorization: String,
        body: FoundationCompleteRequest,
    ): Response<FoundationCompleteResponse> {
        completionCalls++
        return Response.success(completion)
    }
}

private fun sampleMap(completed: Int = 2) = CourseMapDto(
    ok = true,
    level = "hsk1",
    units = listOf(
        CourseUnitDto(
            number = 1,
            title = LocalizedText(uz = "1-dars", ru = "Урок 1", tj = "Дарси 1"),
            lessons = listOf(
                CourseLessonDto(order = 1, status = "done", completionAllowed = true),
                CourseLessonDto(order = 2, status = "done", completionAllowed = true),
                CourseLessonDto(order = 3, status = "current", previewHalf = true),
                CourseLessonDto(order = 4, status = "locked", lockedPremium = true),
            ),
        )
    ),
    progress = com.pomp.hskai.data.api.CourseProgressDto(completed = completed, xp = 120),
    user = CourseUserDto(name = "Akbar", language = "uz"),
)

class CourseRepositoryTest {

    private val json = Json { ignoreUnknownKeys = true }

    /**
     * The cache used to be reachable only after a request had failed, so every
     * open waited out a full round trip with a copy of the same screen already
     * on disk. These two pin the read that makes the app draw first.
     */
    @Test
    fun `the map on disk is returned without asking the network`() = runTest {
        val dao = FakeCourseMapDao()
        val api = FakeCourseApi()
        val repo = repository(api, dao)

        // Fill the cache the only way anything ever does: one good response.
        repo.courseMap()
        val callsAfterWarmUp = api.mapCalls

        val cached = repo.cachedCourseMap()

        assertEquals(callsAfterWarmUp, api.mapCalls)
        assertEquals(false, cached == null)
        // Not stale: a refresh has not failed, it has not been attempted.
        assertFalse(cached!!.isStale)
        assertNull(cached.refreshError)
    }

    @Test
    fun `an empty cache asks for nothing and promises nothing`() = runTest {
        val dao = FakeCourseMapDao()
        val api = FakeCourseApi()

        val cached = repository(api, dao).cachedCourseMap()

        assertNull(cached)
        assertEquals(0, api.mapCalls)
    }

    /**
     * The medians are what make the animation a stroke being written rather
     * than an outline being traced, and they were being dropped here: the DTO
     * read `strokes` and nothing else, so the screen had no centre line to
     * sweep the brush along.
     */
    @Test
    fun `stroke data carries the centre line of every stroke`() = runTest {
        val repository = repository(api = FakeCourseApi(), dao = FakeCourseMapDao())

        val result = repository.strokes("人")

        val strokes = (result as ApiResult.Success).value
        assertEquals(1, strokes.size)
        assertEquals(
            listOf(Offset(0f, 10f), Offset(100f, 10f)),
            strokes.medians.single(),
        )
    }

    private fun repository(
        api: AndroidCourseApi,
        dao: CourseMapDao,
        token: suspend () -> ApiResult<String> = { ApiResult.Success("access-1") },
        offsetMinutes: Int = 300,
        onSessionExpired: suspend () -> Unit = {},
        ttsCache: TtsCache? = null,
        lessonDao: LessonCacheDao? = null,
        foundationApi: AndroidFoundationApi? = null,
    ) = CourseRepository(
        api = api,
        accessToken = token,
        dao = dao,
        lessonDao = lessonDao,
        json = json,
        foundationApi = foundationApi,
        onSessionExpired = onSessionExpired,
        ttsCache = ttsCache,
        now = { 1_700_000_000_000L },
        timezoneOffsetMinutes = { offsetMinutes },
    )

    private fun lessonApi(
        previewHalf: Boolean = false,
        previewCardLimit: Int = 2,
        completionAllowed: Boolean = true,
        failure: Boolean = false,
    ) = object : FakeCourseApi() {
        var lessonCalls = 0

        override suspend fun lesson(
            authorization: String,
            lessonOrder: Int,
            accessRef: String,
        ): Response<CourseLessonResponse> {
            lessonCalls++
            if (failure) throw IOException("offline")
            return Response.success(
                CourseLessonResponse(
                    ok = true,
                    level = "hsk1",
                    lessonOrder = lessonOrder,
                    previewHalf = previewHalf,
                    previewCardLimit = previewCardLimit,
                    totalCards = 2,
                    completionAllowed = completionAllowed,
                    lesson = lessonPayload,
                )
            )
        }
    }

    private suspend fun CourseRepository.openLesson(order: Int = 1) = lesson(
        level = "hsk1",
        lessonOrder = order,
        language = com.pomp.hskai.core.i18n.AppLanguage.UZBEK,
    )

    @Test
    fun `a confirmed foundation completion does not make a second request`() = runTest {
        val foundation = FakeFoundationApi()
        val repository = repository(
            api = FakeCourseApi(),
            dao = FakeCourseMapDao(),
            foundationApi = foundation,
        )

        val result = repository.completeFoundation(
            speakingBonus = false,
            eventId = "android:foundation:" + "a".repeat(32),
        )

        assertTrue(result is ApiResult.Success)
        assertTrue((result as ApiResult.Success).value.foundation.completed)
        assertEquals(1, foundation.completionCalls)
        assertEquals(0, foundation.foundationCalls)
    }

    @Test
    fun `an incomplete post response is reconciled with server status`() = runTest {
        val foundation = FakeFoundationApi(
            completion = FoundationCompleteResponse(
                ok = true,
                foundation = CourseFoundationDto(
                    required = true,
                    completed = false,
                    status = "required",
                ),
            ),
            statusCompleted = true,
        )
        val repository = repository(
            api = FakeCourseApi(),
            dao = FakeCourseMapDao(),
            foundationApi = foundation,
        )

        val result = repository.completeFoundation(
            speakingBonus = false,
            eventId = "android:foundation:" + "b".repeat(32),
        )

        assertTrue(result is ApiResult.Success)
        assertTrue((result as ApiResult.Success).value.foundation.completed)
        assertEquals(1, foundation.completionCalls)
        assertEquals(1, foundation.foundationCalls)
    }

    @Test
    fun `a lesson opened online reopens from disk when the network is gone`() = runTest {
        val cache = FakeLessonCacheDao()
        repository(lessonApi(), FakeCourseMapDao(), lessonDao = cache).openLesson()
        assertEquals(1, cache.rows.size)

        val offline = repository(
            api = lessonApi(failure = true),
            dao = FakeCourseMapDao(),
            lessonDao = cache,
        )

        val snapshot = (offline.openLesson() as ApiResult.Success).value
        assertTrue(snapshot.isStale)
        assertEquals(2, snapshot.lesson.cards.size)
    }

    /**
     * The cached copy is a snapshot, never a second source of truth: a lesson
     * the server last served as a one-card preview must reopen as a one-card
     * preview, not as the whole deck.
     */
    @Test
    fun `a cached preview stays a preview offline`() = runTest {
        val cache = FakeLessonCacheDao()
        repository(
            api = lessonApi(previewHalf = true, previewCardLimit = 1, completionAllowed = false),
            dao = FakeCourseMapDao(),
            lessonDao = cache,
        ).openLesson()

        val snapshot = (
            repository(lessonApi(failure = true), FakeCourseMapDao(), lessonDao = cache)
                .openLesson() as ApiResult.Success
            ).value

        assertTrue(snapshot.isHalfPreview)
        assertEquals(1, snapshot.previewCardLimit)
        assertFalse(snapshot.completionAllowed)
    }

    /**
     * Only a request that never got an answer may be answered from disk. A
     * spent allowance is the server deciding, and the cache must not overrule
     * it — otherwise yesterday's download becomes a way around today's limit.
     */
    @Test
    fun `a refused lesson is never served from the cache`() = runTest {
        val cache = FakeLessonCacheDao()
        repository(lessonApi(), FakeCourseMapDao(), lessonDao = cache).openLesson()

        val refusing = object : FakeCourseApi() {
            override suspend fun lesson(
                authorization: String,
                lessonOrder: Int,
                accessRef: String,
            ): Response<CourseLessonResponse> = Response.error(
                403,
                """{"error":"free_feature_limit_reached"}""".toResponseBody(),
            )
        }

        val result = repository(refusing, FakeCourseMapDao(), lessonDao = cache).openLesson()

        assertTrue(result is ApiResult.Failure)
        assertFalse((result as ApiResult.Failure).error is ApiError.Offline)
    }

    @Test
    fun `an expired session never opens a cached lesson`() = runTest {
        val cache = FakeLessonCacheDao()
        repository(lessonApi(), FakeCourseMapDao(), lessonDao = cache).openLesson()

        val result = repository(
            api = lessonApi(failure = true),
            dao = FakeCourseMapDao(),
            token = { ApiResult.Failure(ApiError.SessionExpired) },
            lessonDao = cache,
        ).openLesson()

        assertEquals(ApiError.SessionExpired, (result as ApiResult.Failure).error)
    }

    /**
     * Fetching a lesson spends the learner's daily slot on the server, so a
     * lesson that was never opened must never be on disk to open offline.
     */
    @Test
    fun `nothing reaches the cache without an opened lesson`() = runTest {
        val cache = FakeLessonCacheDao()
        val offline = repository(lessonApi(failure = true), FakeCourseMapDao(), lessonDao = cache)

        val result = offline.openLesson(order = 7)

        assertTrue(result is ApiResult.Failure)
        assertTrue(cache.rows.isEmpty())
    }

    @Test
    fun `a lesson cached under one number does not answer for another`() = runTest {
        val cache = FakeLessonCacheDao()
        repository(lessonApi(), FakeCourseMapDao(), lessonDao = cache).openLesson(order = 1)

        val result = repository(lessonApi(failure = true), FakeCourseMapDao(), lessonDao = cache)
            .openLesson(order = 2)

        assertTrue(result is ApiResult.Failure)
    }

    @Test
    fun `logging out drops cached lessons with everything else`() = runTest {
        val cache = FakeLessonCacheDao()
        val repository = repository(lessonApi(), FakeCourseMapDao(), lessonDao = cache)
        repository.openLesson()

        repository.clearCache()

        assertEquals(1, cache.clearCalls)
        assertTrue(cache.rows.isEmpty())
    }

    @Test
    fun `the same phrase is fetched once and replayed from the cache`() = runTest {
        val api = FakeCourseApi()
        val cache = FakeTtsCache()
        val repository = repository(api, FakeCourseMapDao(), ttsCache = cache)

        val first = repository.ttsAudio("\u4f60\u597d")
        val second = repository.ttsAudio("\u4f60\u597d")

        assertEquals("audio", String((first as ApiResult.Success).value))
        assertEquals("audio", String((second as ApiResult.Success).value))
        assertEquals(1, api.ttsCalls)
        assertEquals(1, cache.entries.size)
    }

    @Test
    fun `cached audio plays even when the session can no longer be renewed`() = runTest {
        val api = FakeCourseApi()
        val cache = FakeTtsCache()
        repository(api, FakeCourseMapDao(), ttsCache = cache).ttsAudio("\u4f60\u597d")

        val offline = repository(
            api = api,
            dao = FakeCourseMapDao(),
            token = { ApiResult.Failure(ApiError.SessionExpired) },
            ttsCache = cache,
        )

        assertEquals("audio", String((offline.ttsAudio("\u4f60\u597d") as ApiResult.Success).value))
        assertEquals(1, api.ttsCalls)
    }

    @Test
    fun `a phrase with no chinese is never fetched or cached`() = runTest {
        val api = FakeCourseApi()
        val cache = FakeTtsCache()

        val result = repository(api, FakeCourseMapDao(), ttsCache = cache).ttsAudio("salom")

        assertTrue(result is ApiResult.Failure)
        assertEquals(0, api.ttsCalls)
        assertTrue(cache.entries.isEmpty())
    }

    @Test
    fun `clearing the cache drops downloaded audio too`() = runTest {
        val cache = FakeTtsCache()
        val repository = repository(FakeCourseApi(), FakeCourseMapDao(), ttsCache = cache)
        repository.ttsAudio("\u4f60\u597d")

        repository.clearCache()

        assertEquals(1, cache.cleared)
        assertTrue(cache.entries.isEmpty())
    }

    @Test
    fun `a successful fetch is fresh and gets cached`() = runTest {
        val dao = FakeCourseMapDao()
        val api = FakeCourseApi()

        val result = repository(api, dao).courseMap()

        val snapshot = (result as ApiResult.Success).value
        assertFalse(snapshot.isStale)
        assertNull(snapshot.refreshError)
        assertEquals(4, snapshot.map.totalLessons)
        assertEquals("Bearer access-1", api.lastAuthorization)
        assertEquals(1, dao.rows.size)
        assertEquals(1_700_000_000_000L, dao.rows.getValue("hsk1").fetchedAtMillis)
    }

    @Test
    fun `utc plus zero is sent as a real offset`() = runTest {
        val api = FakeCourseApi()
        repository(api, FakeCourseMapDao(), offsetMinutes = 0).courseMap()
        assertEquals(0, api.lastTimezoneOffset)
    }

    @Test
    fun `an offline refresh falls back to the cache and marks it stale`() = runTest {
        val dao = FakeCourseMapDao()
        val online = FakeCourseApi()
        repository(online, dao).courseMap()

        val offline = object : FakeCourseApi() {
            override suspend fun courseMap(
                authorization: String,
                timezoneOffsetMinutes: Int,
            ): Response<CourseMapDto> = throw IOException("offline")
        }

        val result = repository(offline, dao).courseMap()

        val snapshot = (result as ApiResult.Success).value
        assertTrue(snapshot.isStale)
        assertEquals(ApiError.Offline, snapshot.refreshError)
        assertEquals(LessonAccess.HalfPreview, snapshot.map.lessons[2].access)
        assertEquals(LessonAccess.PremiumLocked, snapshot.map.lessons[3].access)
    }

    @Test
    fun `an offline refresh with an empty cache reports the failure`() = runTest {
        val offline = object : FakeCourseApi() {
            override suspend fun courseMap(
                authorization: String,
                timezoneOffsetMinutes: Int,
            ): Response<CourseMapDto> = throw IOException("offline")
        }

        val result = repository(offline, FakeCourseMapDao()).courseMap()

        assertEquals(ApiError.Offline, (result as ApiResult.Failure).error)
    }

    @Test
    fun `an expired session does not silently serve an empty map`() = runTest {
        val result = repository(
            FakeCourseApi(),
            FakeCourseMapDao(),
            token = { ApiResult.Failure(ApiError.SessionExpired) },
        ).courseMap()

        assertEquals(ApiError.SessionExpired, (result as ApiResult.Failure).error)
    }

    @Test
    fun `an expired session never uses cached entitlement as authentication`() = runTest {
        val dao = FakeCourseMapDao()
        repository(FakeCourseApi(), dao).courseMap()

        val result = repository(
            FakeCourseApi(),
            dao,
            token = { ApiResult.Failure(ApiError.SessionExpired) },
        ).courseMap()

        assertEquals(ApiError.SessionExpired, (result as ApiResult.Failure).error)
    }

    @Test
    fun `a runtime server revocation invalidates auth and never serves cached access`() = runTest {
        val dao = FakeCourseMapDao()
        repository(FakeCourseApi(), dao).courseMap()
        var invalidations = 0
        val revoked = object : FakeCourseApi() {
            override suspend fun courseMap(
                authorization: String,
                timezoneOffsetMinutes: Int,
            ): Response<CourseMapDto> = Response.error(
                401,
                """{"ok":false,"error":"desktop_session_revoked"}""".toResponseBody(),
            )
        }

        val result = repository(
            api = revoked,
            dao = dao,
            onSessionExpired = { invalidations++ },
        ).courseMap()

        assertEquals(ApiError.SessionExpired, (result as ApiResult.Failure).error)
        assertEquals(1, invalidations)
        assertEquals(1, dao.rows.size)
    }

    @Test
    fun `lesson obeys the server preview limit instead of deriving half locally`() = runTest {
        val api = object : FakeCourseApi() {
            override suspend fun lesson(
                authorization: String,
                lessonOrder: Int,
                accessRef: String,
            ): Response<CourseLessonResponse> = Response.success(
                CourseLessonResponse(
                    ok = true,
                    level = "hsk1",
                    lessonOrder = lessonOrder,
                    previewHalf = true,
                    previewCardLimit = 1,
                    totalCards = 2,
                    completionAllowed = false,
                    completionError = "free_preview_completed",
                    lesson = lessonPayload,
                )
            )
        }

        val result = repository(api, FakeCourseMapDao()).lesson(
            level = "hsk1",
            lessonOrder = 1,
            language = com.pomp.hskai.core.i18n.AppLanguage.UZBEK,
        )

        val snapshot = (result as ApiResult.Success).value
        assertEquals(1, snapshot.previewCardLimit)
        assertFalse(snapshot.completionAllowed)
        assertEquals("free_preview_completed", snapshot.completionError)
    }

    @Test
    fun `lesson rejects a mismatched server access envelope`() = runTest {
        val api = object : FakeCourseApi() {
            override suspend fun lesson(
                authorization: String,
                lessonOrder: Int,
                accessRef: String,
            ): Response<CourseLessonResponse> = Response.success(
                CourseLessonResponse(
                    ok = true,
                    level = "hsk4",
                    lessonOrder = lessonOrder,
                    previewHalf = false,
                    previewCardLimit = 2,
                    totalCards = 2,
                    completionAllowed = true,
                    lesson = lessonPayload,
                )
            )
        }

        val result = repository(api, FakeCourseMapDao()).lesson(
            level = "hsk1",
            lessonOrder = 1,
            language = com.pomp.hskai.core.i18n.AppLanguage.UZBEK,
        )

        assertEquals(ApiError.Unknown, (result as ApiResult.Failure).error)
    }

    @Test
    fun `a malformed payload is not cached`() = runTest {
        val dao = FakeCourseMapDao()
        val broken = object : FakeCourseApi() {
            override suspend fun courseMap(
                authorization: String,
                timezoneOffsetMinutes: Int,
            ): Response<CourseMapDto> = Response.success(
                CourseMapDto(ok = true, level = "hsk1", units = emptyList())
            )
        }

        val result = repository(broken, dao).courseMap()

        assertEquals(ApiError.Unknown, (result as ApiResult.Failure).error)
        assertTrue(dao.rows.isEmpty())
    }

    @Test
    fun `completion event ids use the android namespace and are unique`() {
        val first = CourseRepository.newEventId()
        val second = CourseRepository.newEventId()

        assertTrue(first.startsWith("android:"))
        assertTrue(first.length in 16..80)
        assertTrue(first != second)
        assertFalse(first.contains("desktop"))
    }

    @Test
    fun `completion sends the supplied event id unchanged so retries dedupe`() = runTest {
        val sent = mutableListOf<CourseCompleteRequest>()
        val api = object : FakeCourseApi() {
            override suspend fun complete(
                authorization: String,
                body: CourseCompleteRequest,
            ): Response<CourseCompleteResponse> {
                sent += body
                return Response.success(
                    CourseCompleteResponse(
                        ok = true,
                        completedLesson = body.lessonOrder,
                        completedLessonsCount = body.lessonOrder,
                        duplicate = sent.size > 1,
                    )
                )
            }
        }
        val repository = repository(api, FakeCourseMapDao())
        val eventId = "android:0d1f2e3a4b5c6d7e8f90a1b2c3d4e5f6"

        repository.completeLesson(lessonOrder = 1, eventId = eventId)
        val retry = repository.completeLesson(lessonOrder = 1, eventId = eventId)

        assertEquals(2, sent.size)
        assertEquals(listOf(eventId, eventId), sent.map { it.eventId })
        assertTrue((retry as ApiResult.Success).value.duplicate)
    }

    @Test
    fun `reward chest uses bearer transport and returns server reward`() = runTest {
        var sentAuthorization: String? = null
        val api = object : FakeCourseApi() {
            override suspend fun openRewardChest(
                authorization: String,
            ): Response<RewardChestOpenResponse> {
                sentAuthorization = authorization
                return Response.success(
                    RewardChestOpenResponse(ok = true, rewardType = "xp", rewardValue = 20)
                )
            }
        }

        val result = repository(api, FakeCourseMapDao()).openRewardChest()

        assertEquals("Bearer access-1", sentAuthorization)
        assertEquals(20, (result as ApiResult.Success).value.rewardValue)
    }

    @Test
    fun `clearing the cache wipes cached progress`() = runTest {
        val dao = FakeCourseMapDao()
        repository(FakeCourseApi(), dao).courseMap()
        assertEquals(1, dao.rows.size)

        repository(FakeCourseApi(), dao).clearCache()

        assertEquals(1, dao.clearCalls)
        assertTrue(dao.rows.isEmpty())
    }
}
