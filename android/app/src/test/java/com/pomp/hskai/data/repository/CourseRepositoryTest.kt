package com.pomp.hskai.data.repository

import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.AndroidCourseApi
import com.pomp.hskai.data.api.CourseCompleteRequest
import com.pomp.hskai.data.api.CourseCompleteResponse
import com.pomp.hskai.data.api.CourseLessonDto
import com.pomp.hskai.data.api.CourseLessonResponse
import com.pomp.hskai.data.api.CourseMapDto
import com.pomp.hskai.data.api.CourseUnitDto
import com.pomp.hskai.data.api.CourseUserDto
import com.pomp.hskai.data.api.LanguageRequest
import com.pomp.hskai.data.api.LocalizedText
import com.pomp.hskai.data.api.OkResponse
import com.pomp.hskai.data.local.CourseMapCacheEntity
import com.pomp.hskai.data.local.CourseMapDao
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

private val lessonPayload = Json.parseToJsonElement(
    """{"source_lesson":1,"part_no":1,"part_count":1,"checkpoint":false,"title":{"uz":"1-dars"},"subtitle":{"uz":"1-qism"},"sections":[{"section_no":1,"cards":[{"type":"pronunciation","phrase":"你好","pinyin":"nǐ hǎo","translation":{"uz":"salom"}},{"type":"tone_drill_v2"}]}]}"""
).jsonObject

private open class FakeCourseApi : AndroidCourseApi {
    var lastAuthorization: String? = null
    var lastTimezoneOffset: Int? = null

    override suspend fun courseMap(
        authorization: String,
        timezoneOffsetMinutes: Int,
    ): Response<CourseMapDto> {
        lastAuthorization = authorization
        lastTimezoneOffset = timezoneOffsetMinutes
        return Response.success(sampleMap())
    }

    override suspend fun lesson(
        authorization: String,
        lessonOrder: Int,
    ): Response<CourseLessonResponse> = throw NotImplementedError()

    override suspend fun tts(
        authorization: String,
        text: String,
        rate: String,
    ): Response<ResponseBody> = Response.success("audio".toResponseBody())

    override suspend fun complete(
        authorization: String,
        body: CourseCompleteRequest,
    ): Response<CourseCompleteResponse> = throw NotImplementedError()

    override suspend fun setLanguage(
        authorization: String,
        body: LanguageRequest,
    ): Response<OkResponse> = Response.success(OkResponse(ok = true))
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

    private fun repository(
        api: AndroidCourseApi,
        dao: CourseMapDao,
        token: suspend () -> ApiResult<String> = { ApiResult.Success("access-1") },
        offsetMinutes: Int = 300,
        onSessionExpired: suspend () -> Unit = {},
    ) = CourseRepository(
        api = api,
        accessToken = token,
        dao = dao,
        json = json,
        onSessionExpired = onSessionExpired,
        now = { 1_700_000_000_000L },
        timezoneOffsetMinutes = { offsetMinutes },
    )

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
        // A falsy check would have dropped this and silently shifted the
        // learner's streak day boundary.
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
        // The cache repeats the last server decision; it cannot widen access.
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
    fun `an expired session never uses cached entitlement as authentication`() =
        runTest {
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
        // The backend bounds event_id to 16..80 characters.
        assertTrue(first.length in 16..80)
        assertTrue(first != second)
        // Must not look like a desktop completion.
        assertFalse(first.contains("desktop"))
    }

    @Test
    fun `completion sends the supplied event id unchanged so retries dedupe`() =
        runTest {
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
    fun `clearing the cache wipes cached progress`() = runTest {
        val dao = FakeCourseMapDao()
        repository(FakeCourseApi(), dao).courseMap()
        assertEquals(1, dao.rows.size)

        repository(FakeCourseApi(), dao).clearCache()

        assertEquals(1, dao.clearCalls)
        assertTrue(dao.rows.isEmpty())
    }
}
