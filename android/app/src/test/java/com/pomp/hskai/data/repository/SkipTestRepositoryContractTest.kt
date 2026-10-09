package com.pomp.hskai.data.repository

import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.AndroidCourseApi
import com.pomp.hskai.data.local.CourseMapCacheEntity
import com.pomp.hskai.data.local.CourseMapDao
import com.pomp.hskai.data.local.LessonCacheDao
import com.pomp.hskai.data.local.LessonCacheEntity
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import java.util.concurrent.TimeUnit

/** Real Retrofit and repository validation: a lesson fake used to hide the locked-order 403. */
class SkipTestRepositoryContractTest {
    private val server = MockWebServer()
    private val cache = SkipLessonCache()
    private var sessionExpired = 0
    private val json = Json { ignoreUnknownKeys = true; explicitNulls = false }
    private lateinit var repository: CourseRepository

    @Before
    fun setUp() {
        server.start()
        val api = Retrofit.Builder()
            .baseUrl(server.url("/"))
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()
            .create(AndroidCourseApi::class.java)
        repository = CourseRepository(
            api = api,
            accessToken = { ApiResult.Success("skip-token") },
            dao = SkipMapDao(),
            lessonDao = cache,
            json = json,
            onSessionExpired = { sessionExpired++ },
        )
    }

    @After
    fun tearDown() = server.shutdown()

    @Test
    fun `locked quiz uses read only question route and retains source grading`() = runTest {
        respond(quizBody())

        val result = repository.skipTestQuestions("hsk1", 4, AppLanguage.UZBEK)

        val request = requireNotNull(server.takeRequest(1, TimeUnit.SECONDS))
        assertEquals("GET", request.method)
        assertEquals("/api/v3/android/course/skip-test/4", request.path)
        assertEquals("Bearer skip-token", request.getHeader("Authorization"))
        assertEquals(0L, request.body.size)
        assertTrue(result is ApiResult.Success)
        val question = (result as ApiResult.Success).value.single()
        assertEquals("lesson:hsk1:4:section:2:card:3", question.materialRef)
        assertEquals(listOf("salom", "rahmat"), question.options)
        assertTrue(question.isCorrect(0))
        assertFalse(question.isCorrect(1))
        assertEquals(0, cache.reads)
        assertEquals(0, cache.writes)
    }

    @Test
    fun `only explicit empty quiz succeeds without populating playable lesson cache`() = runTest {
        respond("""{"ok":true,"level":"hsk1","lesson_order":4,"questions":[]}""")
        val result = repository.skipTestQuestions("hsk1", 4, AppLanguage.UZBEK)
        assertTrue(result is ApiResult.Success)
        assertTrue((result as ApiResult.Success).value.isEmpty())
        assertEquals(0, cache.reads)
        assertEquals(0, cache.writes)
    }

    @Test
    fun `missing questions cannot become a free empty test unlock`() = runTest {
        respond("""{"ok":true,"level":"hsk1","lesson_order":4}""")
        val result = repository.skipTestQuestions("hsk1", 4, AppLanguage.UZBEK)
        assertEquals(ApiResult.Failure(ApiError.Unknown), result)
    }

    @Test
    fun `wrong course order source or malformed grading cannot become quiz success`() = runTest {
        for (body in listOf(
            quizBody(level = "nhsk1"),
            quizBody(order = 5),
            quizBody(ref = "lesson:nhsk1:4:section:2:card:3"),
            quizBody(card = """{"type":"pronunciation","phrase":"你好"}"""),
            quizBody(card = """{"type":"meaning_guess","options":["a","b"],"correct_index":4}"""),
        )) {
            respond(body)
            assertEquals(ApiResult.Failure(ApiError.Unknown),
                repository.skipTestQuestions("hsk1", 4, AppLanguage.UZBEK))
        }
    }

    @Test
    fun `course access denial never reads a playable lesson fallback`() = runTest {
        respond("""{"ok":false,"error":"hsk30_unlock_required"}""", status = 403)
        val result = repository.skipTestQuestions("nhsk1", 4, AppLanguage.UZBEK)
        assertTrue(result is ApiResult.Failure)
        assertEquals(ApiError.fromCode("hsk30_unlock_required"), (result as ApiResult.Failure).error)
        assertEquals(0, cache.reads)
        assertEquals(0, cache.writes)
    }

    @Test
    fun `invalid session keeps shared credential expiry handling`() = runTest {
        respond("""{"ok":false,"error":"desktop_access_invalid"}""", status = 401)
        assertEquals(ApiResult.Failure(ApiError.SessionExpired),
            repository.skipTestQuestions("hsk1", 4, AppLanguage.UZBEK))
        assertEquals(1, sessionExpired)
    }

    @Test
    fun `unlock posts the actual score and requires confirmed server progress`() = runTest {
        respond("""{"ok":true,"lesson_order":4,"completed_lessons_count":3}""")
        assertTrue(repository.unlockLesson(4, 0, expectedLevel = "hsk1") is ApiResult.Success)
        val request = requireNotNull(server.takeRequest(1, TimeUnit.SECONDS))
        assertEquals("POST", request.method)
        assertEquals("/api/v3/android/lesson/unlock", request.path)
        val body = json.parseToJsonElement(request.body.readUtf8()).jsonObject
        assertEquals("4", body["lesson_order"]?.jsonPrimitive?.content)
        assertEquals("0", body["score"]?.jsonPrimitive?.content)
        assertEquals("hsk1", body["expected_level"]?.jsonPrimitive?.content)
    }

    @Test
    fun `refused wrong order and incomplete unlock never become confirmed success`() = runTest {
        for (body in listOf(
            """{"ok":false,"lesson_order":4,"completed_lessons_count":3}""",
            """{"ok":true,"lesson_order":5,"completed_lessons_count":4}""",
            """{"ok":true,"lesson_order":4,"completed_lessons_count":0}""",
        )) {
            respond(body)
            assertEquals(ApiResult.Failure(ApiError.Unknown), repository.unlockLesson(4, 100, expectedLevel = "hsk1"))
        }
    }

    @Test
    fun `course change precondition refusal remains a mapped unlock failure`() = runTest {
        respond("""{"ok":false,"error":"course_context_changed"}""", status = 409)
        assertEquals(ApiResult.Failure(ApiError.fromCode("course_context_changed")),
            repository.unlockLesson(4, 100, expectedLevel = "hsk1"))
        val request = requireNotNull(server.takeRequest(1, TimeUnit.SECONDS))
        val body = json.parseToJsonElement(request.body.readUtf8()).jsonObject
        assertEquals("hsk1", body["expected_level"]?.jsonPrimitive?.content)
    }

    private fun respond(body: String, status: Int = 200) {
        server.enqueue(MockResponse().setResponseCode(status)
            .setHeader("Content-Type", "application/json").setBody(body))
    }

    private fun quizBody(
        level: String = "hsk1",
        order: Int = 4,
        ref: String = "lesson:hsk1:4:section:2:card:3",
        card: String = """{"type":"meaning_guess","prompt":"你好","options":[{"uz":"salom","ru":"привет"},{"uz":"rahmat","ru":"спасибо"}],"correct_index":0}""",
    ) = """{"ok":true,"level":"$level","lesson_order":$order,"questions":[{"material_ref":"$ref","card":$card}]}"""
}

private class SkipLessonCache : LessonCacheDao {
    var reads = 0
    var writes = 0
    override suspend fun find(level: String, lessonOrder: Int): LessonCacheEntity? {
        reads++
        return null
    }
    override suspend fun upsert(entity: LessonCacheEntity) { writes++ }
    override suspend fun clear() = Unit
}

private class SkipMapDao : CourseMapDao {
    override suspend fun find(level: String): CourseMapCacheEntity? = null
    override suspend fun findMostRecent(): CourseMapCacheEntity? = null
    override suspend fun upsert(entity: CourseMapCacheEntity) = Unit
    override suspend fun clear() = Unit
}
