package com.pomp.hskai.feature.course

import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.AndroidCourseApi
import com.pomp.hskai.data.api.CourseCompleteRequest
import com.pomp.hskai.data.api.CourseCompleteResponse
import com.pomp.hskai.data.api.CourseLessonResponse
import com.pomp.hskai.data.api.CourseSkipTestResponse
import com.pomp.hskai.data.api.CourseSkipQuestionDto
import com.pomp.hskai.data.api.CourseMapDto
import com.pomp.hskai.data.api.DictionaryResponse
import com.pomp.hskai.data.api.LanguageRequest
import com.pomp.hskai.data.api.LessonUnlockRequest
import com.pomp.hskai.data.api.LessonUnlockResponse
import com.pomp.hskai.data.api.NotificationsRequest
import com.pomp.hskai.data.api.OkResponse
import com.pomp.hskai.data.api.RewardChestOpenResponse
import com.pomp.hskai.data.api.StrokeDataDto
import com.pomp.hskai.data.local.CourseMapCacheEntity
import com.pomp.hskai.data.local.CourseMapDao
import com.pomp.hskai.data.repository.CourseRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.setMain
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonArray
import okhttp3.ResponseBody
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import retrofit2.Response

/**
 * The skip-ahead test, which is the only way a locked lesson opens.
 *
 * What is worth pinning is the arithmetic and who decides: the score is the
 * learner's own answers, the pass mark matches the Mini App's, and a weak
 * score still reaches the server — refusing on the device would only be a
 * second, quieter rule for the same thing.
 */
@OptIn(ExperimentalCoroutinesApi::class)
class SkipTestViewModelTest {

    private val dispatcher = StandardTestDispatcher()

    @Before
    fun setUp() = Dispatchers.setMain(dispatcher)

    @After
    fun tearDown() = Dispatchers.resetMain()

    @Test
    fun `a locked lesson is drawn as six questions`() = runTest(dispatcher) {
        val api = FakeSkipApi()
        val model = viewModel(api)

        model.start(4)
        advanceUntilIdle()

        assertEquals(SkipTestViewModel.QUESTION_COUNT, model.state.value.questions.size)
        assertFalse(model.state.value.isLoading)
        assertEquals(listOf(4), api.quizReads)
        assertEquals(0, api.lessonReads)
        assertTrue(api.unlocks.isEmpty())
    }

    @Test
    fun `the same locked lesson asks the same questions`() = runTest(dispatcher) {
        val first = viewModel()
        first.start(4)
        advanceUntilIdle()
        val second = viewModel()
        second.start(4)
        advanceUntilIdle()

        // Re-opening must not reroll: otherwise a learner could close and
        // reopen until an easy draw appeared.
        assertEquals(
            first.state.value.questions.map { it.materialRef },
            second.state.value.questions.map { it.materialRef },
        )
    }

    @Test
    fun `answering everything correctly passes and unlocks`() = runTest(dispatcher) {
        val api = FakeSkipApi()
        val model = viewModel(api)
        model.start(4)
        advanceUntilIdle()

        answerAll(model, correct = true)

        assertEquals(100, model.state.value.finishedScore)
        assertTrue(model.state.value.passed)
        model.unlock()
        advanceUntilIdle()
        assertTrue(model.state.value.unlocked)
        assertEquals(listOf(4 to 100), api.unlocks)
        assertEquals(listOf("hsk1"), api.unlockLevels)
    }

    @Test
    fun `answering everything wrongly fails but still reaches the server`() =
        runTest(dispatcher) {
            val api = FakeSkipApi()
            val model = viewModel(api)
            model.start(4)
            advanceUntilIdle()

            answerAll(model, correct = false)

            assertEquals(0, model.state.value.finishedScore)
            assertFalse(model.state.value.passed)
            // The confirmation is the screen's to ask; once it is answered the
            // score goes up as it is, and the lesson opens.
            model.unlock()
            advanceUntilIdle()
            assertTrue(model.state.value.unlocked)
            assertEquals(listOf(4 to 0), api.unlocks)
        }

    @Test
    fun `a lesson with nothing to ask simply opens`() = runTest(dispatcher) {
        val api = FakeSkipApi(withQuestions = false)
        val model = viewModel(api)

        model.start(4)
        advanceUntilIdle()

        assertTrue(model.state.value.unlocked)
        assertEquals(listOf(4 to 100), api.unlocks)
    }

    @Test
    fun `a second tap cannot unlock twice`() = runTest(dispatcher) {
        val api = FakeSkipApi()
        val model = viewModel(api)
        model.start(4)
        advanceUntilIdle()
        answerAll(model, correct = true)

        model.unlock()
        model.unlock()
        advanceUntilIdle()

        assertEquals(1, api.unlocks.size)
    }

    @Test
    fun `reopened retained viewmodel starts a fresh locked attempt`() = runTest(dispatcher) {
        val api = FakeSkipApi()
        val model = viewModel(api)
        model.start(4)
        advanceUntilIdle()
        answerAll(model, correct = true)
        model.unlock()
        advanceUntilIdle()
        assertTrue(model.state.value.unlocked)

        model.endAttempt()
        model.beginAttempt()
        model.start(4)
        advanceUntilIdle()

        assertFalse(model.state.value.unlocked)
        assertEquals(null, model.state.value.finishedScore)
        assertEquals(0, model.state.value.correctCount)
        assertEquals(listOf(4, 4), api.quizReads)
        assertEquals(1, api.unlocks.size)
    }

    @Test
    fun `closed quiz response cannot auto unlock an empty old lesson`() = runTest(dispatcher) {
        val pending = CompletableDeferred<Response<CourseSkipTestResponse>>()
        val api = object : FakeSkipApi() {
            override suspend fun skipTestQuestions(authorization: String, lessonOrder: Int) = pending.await()
        }
        val model = viewModel(api)
        model.start(4)
        runCurrent()
        model.endAttempt()
        pending.complete(Response.success(CourseSkipTestResponse(
            ok = true, level = "hsk1", lessonOrder = 4, questions = emptyList(),
        )))
        advanceUntilIdle()
        assertEquals(SkipTestUiState(), model.state.value)
        assertTrue(api.unlocks.isEmpty())
    }

    @Test
    fun `late unlock cannot mark a reopened quiz as unlocked`() = runTest(dispatcher) {
        val pending = CompletableDeferred<Response<LessonUnlockResponse>>()
        val api = object : FakeSkipApi() {
            override suspend fun unlockLesson(authorization: String, body: LessonUnlockRequest) = pending.await()
        }
        val model = viewModel(api)
        model.start(4)
        advanceUntilIdle()
        answerAll(model, correct = true)
        model.unlock()
        runCurrent()
        model.endAttempt()
        model.beginAttempt()
        model.start(4)
        runCurrent()
        pending.complete(Response.success(LessonUnlockResponse(
            ok = true, lessonOrder = 4, completedLessonsCount = 3,
        )))
        advanceUntilIdle()
        assertFalse(model.state.value.unlocked)
        assertFalse(model.state.value.isUnlocking)
        assertEquals(null, model.state.value.finishedScore)
    }

    @Test
    fun `queued unlock is not sent after closing the attempt`() = runTest(dispatcher) {
        val api = FakeSkipApi()
        val model = viewModel(api)
        model.start(4)
        advanceUntilIdle()
        answerAll(model, correct = true)
        model.unlock()
        model.endAttempt()
        advanceUntilIdle()
        assertTrue(api.unlocks.isEmpty())
        assertEquals(SkipTestUiState(), model.state.value)
    }

    private fun answerAll(model: SkipTestViewModel, correct: Boolean) {
        repeat(SkipTestViewModel.QUESTION_COUNT) {
            val question = model.state.value.currentQuestion ?: return
            val wrong = (0 until question.options.size)
                .firstOrNull { index -> index != question.correctIndex } ?: 0
            model.select(if (correct) question.correctIndex else wrong)
            model.advance()
        }
    }

    private fun viewModel(api: AndroidCourseApi = FakeSkipApi()) = SkipTestViewModel(
        repository = CourseRepository(
            api = api,
            accessToken = { ApiResult.Success("access-1") },
            dao = NoopSkipDao(),
            json = Json { ignoreUnknownKeys = true },
            ioDispatcher = dispatcher,
        ),
        level = "hsk1",
        language = AppLanguage.UZBEK,
    )
}

private class NoopSkipDao : CourseMapDao {
    override suspend fun find(level: String): CourseMapCacheEntity? = null
    override suspend fun findMostRecent(): CourseMapCacheEntity? = null
    override suspend fun upsert(entity: CourseMapCacheEntity) = Unit
    override suspend fun clear() = Unit
}

/** Eight graded cards, so a draw of six is a real choice rather than the lot. */
private const val SKIP_CARD_COUNT = 8

private fun skipLessonBody(withQuestions: Boolean): String {
    val cards = if (!withQuestions) {
        """{"type":"pronunciation","phrase":"你好","pinyin":"nǐ hǎo","translation":{"uz":"salom"}}"""
    } else {
        (1..SKIP_CARD_COUNT).joinToString(",") { index ->
            """{"type":"meaning_guess","prompt":"词 $index","options":["a","b","c"],"correct_index":1,"explanation":""}"""
        }
    }
    return """{"lesson":{"source_lesson":1,"part_no":1,"part_count":1,"checkpoint":false,
        "title":{"uz":"1-dars"},"subtitle":{"uz":"1-qism"},
        "sections":[{"section_no":1,"section_purpose":"practice","cards":[$cards]}]}}"""
}

private open class FakeSkipApi(private val withQuestions: Boolean = true) : AndroidCourseApi {
    val unlocks = mutableListOf<Pair<Int, Int>>()
    val unlockLevels = mutableListOf<String>()
    val quizReads = mutableListOf<Int>()
    var lessonReads = 0

    override suspend fun unlockLesson(
        authorization: String,
        body: LessonUnlockRequest,
    ): Response<LessonUnlockResponse> {
        unlocks += body.lessonOrder to body.score
        unlockLevels += body.expectedLevel
        return Response.success(
            LessonUnlockResponse(
                ok = true,
                lessonOrder = body.lessonOrder,
                completedLessonsCount = body.lessonOrder - 1,
            )
        )
    }

    override suspend fun lesson(
        authorization: String,
        lessonOrder: Int,
        accessRef: String,
    ): Response<CourseLessonResponse> {
        lessonReads++
        // The actual locked lesson is forbidden. A successful skip quiz must
        // use the question endpoint, not this playable-lesson endpoint.
        return Response.error(403, ResponseBody.create(null,
            """{"error":"course_lesson_not_unlocked"}"""))
    }

    override suspend fun skipTestQuestions(
        authorization: String,
        lessonOrder: Int,
    ): Response<CourseSkipTestResponse> {
        quizReads += lessonOrder
        val cards = if (!withQuestions) emptyList() else Json.parseToJsonElement(
            skipLessonBody(true)
        ).jsonObject.getValue("lesson").jsonObject.getValue("sections")
            .jsonArray.first().jsonObject.getValue("cards").jsonArray
        return Response.success(CourseSkipTestResponse(
            ok = true,
            level = "hsk1",
            lessonOrder = lessonOrder,
            questions = cards.mapIndexed { index, card -> CourseSkipQuestionDto(
                materialRef = "lesson:hsk1:$lessonOrder:section:1:card:${index + 1}",
                card = card.jsonObject,
            ) },
        ))
    }

    override suspend fun courseMap(
        authorization: String,
        timezoneOffsetMinutes: Int,
    ): Response<CourseMapDto> = throw NotImplementedError()

    override suspend fun switchCourseTrack(
        authorization: String,
        body: com.pomp.hskai.data.api.CourseTrackSwitchRequest,
    ): Response<com.pomp.hskai.data.api.OkResponse> = throw NotImplementedError()

    override suspend fun markHsk30PromoShown(
        authorization: String,
    ): Response<com.pomp.hskai.data.api.Hsk30PromoMarkResponse> = throw NotImplementedError()

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

    override suspend fun dictionary(
        authorization: String,
        ifNoneMatch: String?,
    ): Response<DictionaryResponse> = throw NotImplementedError()

    override suspend fun stroke(
        authorization: String,
        char: String,
    ): Response<StrokeDataDto> = throw NotImplementedError()

    override suspend fun tts(
        authorization: String,
        text: String,
        rate: String,
    ): Response<ResponseBody> = throw NotImplementedError()
}
