package com.pomp.hskai.feature.course

import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.AndroidCourseApi
import com.pomp.hskai.data.api.CourseCompleteRequest
import com.pomp.hskai.data.api.CourseCompleteResponse
import com.pomp.hskai.data.api.CourseLessonResponse
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
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
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
        val model = viewModel()

        model.start(4)
        advanceUntilIdle()

        assertEquals(SkipTestViewModel.QUESTION_COUNT, model.state.value.questions.size)
        assertFalse(model.state.value.isLoading)
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

private class FakeSkipApi(private val withQuestions: Boolean = true) : AndroidCourseApi {
    val unlocks = mutableListOf<Pair<Int, Int>>()

    private val cardCount = if (withQuestions) SKIP_CARD_COUNT else 1

    override suspend fun unlockLesson(
        authorization: String,
        body: LessonUnlockRequest,
    ): Response<LessonUnlockResponse> {
        unlocks += body.lessonOrder to body.score
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
    ): Response<CourseLessonResponse> = Response.success(
        CourseLessonResponse(
            ok = true,
            level = "hsk1",
            lessonOrder = lessonOrder,
            // The repository refuses an envelope whose counts do not match the
            // payload it carries, so a fake that leaves them at zero is
            // refused exactly as a malformed server answer would be.
            previewCardLimit = cardCount,
            totalCards = cardCount,
            completionAllowed = true,
            lesson = Json.parseToJsonElement(skipLessonBody(withQuestions))
                .jsonObject
                .getValue("lesson")
                .jsonObject,
        )
    )

    override suspend fun courseMap(
        authorization: String,
        timezoneOffsetMinutes: Int,
    ): Response<CourseMapDto> = throw NotImplementedError()

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
