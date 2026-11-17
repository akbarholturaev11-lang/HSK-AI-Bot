package com.pomp.hskai.feature.lesson

import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.AdaptiveAnswerRequestDto
import com.pomp.hskai.data.api.AdaptiveAnswerResponseDto
import com.pomp.hskai.data.api.AdaptiveItemDto
import com.pomp.hskai.data.api.AdaptivePlanDto
import com.pomp.hskai.data.api.AdaptivePlanRequestDto
import com.pomp.hskai.data.api.AdaptivePlanResponseDto
import com.pomp.hskai.data.api.AndroidAdaptiveApi
import com.pomp.hskai.data.api.AndroidCourseApi
import com.pomp.hskai.data.api.MistakeReviewQuestionDto
import com.pomp.hskai.data.repository.AdaptiveLessonRepository
import com.pomp.hskai.data.repository.CourseRepository
import com.pomp.hskai.data.repository.MISTAKE_REVIEW_FORMATS
import com.pomp.hskai.domain.model.ChoiceCard
import com.pomp.hskai.domain.model.ChoiceKind
import com.pomp.hskai.domain.model.Lesson
import com.pomp.hskai.domain.model.LessonSection
import com.pomp.hskai.domain.model.MatchPairsCard
import com.pomp.hskai.domain.model.SentenceBuilderCard
import com.pomp.hskai.domain.model.UnsupportedCard
import java.io.IOException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import kotlinx.serialization.json.Json
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import retrofit2.Response

private fun adaptivePlan(count: Int, lessonOrder: Int = 1) = AdaptivePlanResponseDto(
    ok = true,
    enabled = true,
    plan = AdaptivePlanDto(
        id = 41,
        version = 1,
        level = "hsk1",
        lessonOrder = lessonOrder,
        items = (1..count).map { slot ->
            AdaptiveItemDto(
                id = "a$slot:${10 + slot}:meaning_choice",
                slot = slot,
                kind = "review",
                skill = "meaning",
                question = MistakeReviewQuestionDto(
                    id = "q$slot", prompt = "Choose", options = listOf("你", "好", "我"), format = "meaning_choice",
                ),
            )
        },
    ),
)

private class FakeAdaptiveApi(
    var onPlan: () -> Response<AdaptivePlanResponseDto> = { Response.success(adaptivePlan(3)) },
    var onAnswer: (AdaptiveAnswerRequestDto) -> Response<AdaptiveAnswerResponseDto> = { body ->
        Response.success(
            AdaptiveAnswerResponseDto(
                ok = true, itemId = body.itemId, correct = false, correctIndex = 0,
                selectedIndex = body.selectedIndex, correctAnswer = "你",
            )
        )
    },
) : AndroidAdaptiveApi {
    val plans = mutableListOf<AdaptivePlanRequestDto>()
    val answers = mutableListOf<AdaptiveAnswerRequestDto>()

    override suspend fun plan(authorization: String, body: AdaptivePlanRequestDto): Response<AdaptivePlanResponseDto> {
        plans += body
        return onPlan()
    }

    override suspend fun answer(authorization: String, body: AdaptiveAnswerRequestDto): Response<AdaptiveAnswerResponseDto> {
        answers += body
        return onAnswer(body)
    }
}

private fun <T> status(code: Int): Response<T> = Response.error(code, """{"ok":false}""".toResponseBody())

/** The official numbers a lesson reports; a personal review may change none of them. */
private data class Official(
    val correct: Int,
    val graded: Int,
    val hearts: Int,
    val streak: Int,
)

private fun LessonUiState.official() = Official(correctCount, gradedAnswered, hearts, answerStreak)

@OptIn(ExperimentalCoroutinesApi::class)
class LessonAdaptiveReviewTest {

    private val dispatcher = StandardTestDispatcher()
    private var clock = 0L

    @Before
    fun setUp() = Dispatchers.setMain(dispatcher)

    @After
    fun tearDown() = Dispatchers.resetMain()

    private fun adaptiveRepository(api: AndroidAdaptiveApi) =
        AdaptiveLessonRepository(api, { ApiResult.Success("access-1") }, now = { clock })

    private fun viewModel(
        api: AndroidCourseApi = FakeLessonApi(),
        adaptive: AdaptiveLessonRepository? = null,
    ) = LessonViewModel(
        repository = CourseRepository(
            api = api,
            accessToken = { ApiResult.Success("access-1") },
            dao = NoopDao(),
            json = Json { ignoreUnknownKeys = true },
            ioDispatcher = dispatcher,
        ),
        audioPlayer = FakeLessonAudioPlayer(),
        level = "hsk1",
        lessonOrder = 1,
        language = AppLanguage.UZBEK,
        adaptiveRepository = adaptive,
        eventIdFactory = { "android:0d1f2e3a4b5c6d7e8f90a1b2c3d4e5f6" },
    ).also { it.beginAttempt("attempt-1") }

    /**
     * Plays the base deck with the same answers every time: the choice wrong,
     * the builder and the pairs right. [onReview] answers a personal review.
     */
    private fun TestScope.playDeck(
        model: LessonViewModel,
        onReview: (AdaptiveReviewState) -> Unit = {},
    ) {
        var guard = 0
        while (model.state.value.outcome is LessonOutcome.InProgress && guard++ < 40) {
            val review = model.state.value.adaptive
            if (review != null) {
                onReview(review)
                advanceUntilIdle()
                continue
            }
            when (val card = model.state.value.currentCard) {
                is ChoiceCard -> model.answerChoice(card, 1)
                is SentenceBuilderCard -> model.answerBuilder(card, card.answerTokens)
                is MatchPairsCard -> model.answerMatchPairs(card)
                null -> break
                else -> Unit
            }
            model.advance()
            advanceUntilIdle()
        }
    }

    @Test
    fun `the same base answers give the same official result with reviews on or off`() = runTest(dispatcher) {
        val offApi = FakeLessonApi()
        val off = viewModel(offApi)
        advanceUntilIdle()
        playDeck(off)

        val onApi = FakeLessonApi()
        val adaptiveApi = FakeAdaptiveApi()
        val on = viewModel(onApi, adaptiveRepository(adaptiveApi))
        advanceUntilIdle()
        val shownAt = mutableListOf<Int>()
        playDeck(on) { review ->
            shownAt += on.state.value.cardIndex
            val before = on.state.value.official()
            on.answerAdaptive(selectedIndex = 1)
            advanceUntilIdle()
            val checked = on.state.value.adaptive
            assertNotNull(checked?.feedback)
            assertFalse(checked!!.feedback!!.correct)
            assertEquals("a wrong review costs no heart and no streak", before, on.state.value.official())
            on.continueAdaptive()
            assertNull(on.state.value.adaptive)
            assertEquals(review.item.id, adaptiveApi.answers.last().itemId)
        }

        assertEquals("reviews stand only after graded cards", listOf(2, 3, 4), shownAt)
        assertEquals(offApi.completions.single(), onApi.completions.single())
        assertEquals(off.state.value.official(), on.state.value.official())
        val offOutcome = off.state.value.outcome as LessonOutcome.Completed
        val onOutcome = on.state.value.outcome as LessonOutcome.Completed
        assertEquals(offOutcome.correct to offOutcome.graded, onOutcome.correct to onOutcome.graded)

        val request = adaptiveApi.plans.single()
        assertEquals(AdaptivePlanRequestDto("hsk1", 1, MISTAKE_REVIEW_FORMATS, "uz"), request)
        assertEquals(listOf(41L, 41L, 41L), adaptiveApi.answers.map { it.planId })
        assertTrue(adaptiveApi.answers.all { it.selectedIndex == 1 && it.selectedTokens == null })
    }

    @Test
    fun `nothing advances behind a review and a second answer is ignored`() = runTest(dispatcher) {
        val adaptiveApi = FakeAdaptiveApi(onPlan = { Response.success(adaptivePlan(1)) })
        val model = viewModel(adaptive = adaptiveRepository(adaptiveApi))
        advanceUntilIdle()
        playDeck(model) { review ->
            val index = model.state.value.cardIndex
            model.advance()
            assertEquals(index, model.state.value.cardIndex)
            model.answerAdaptive(selectedIndex = 0)
            model.answerAdaptive(selectedIndex = 2)
            model.answerAdaptive(selectedIndex = 1, selectedTokens = listOf("你"))
            advanceUntilIdle()
            assertEquals(listOf(0), adaptiveApi.answers.map { it.selectedIndex })
            assertEquals(review.item.id, model.state.value.adaptive?.item?.id)
            model.continueAdaptive()
            assertEquals(index, model.state.value.cardIndex)
        }
        assertEquals(1, adaptiveApi.answers.size)
        assertTrue(model.state.value.outcome is LessonOutcome.Completed)
    }

    @Test
    fun `a failed plan or a free preview leaves the deck as it was`() = runTest(dispatcher) {
        val failing = FakeAdaptiveApi(onPlan = { throw IOException("offline") })
        val api = FakeLessonApi()
        val model = viewModel(api, adaptiveRepository(failing))
        advanceUntilIdle()
        playDeck(model) { error("no review may appear without a plan") }
        assertEquals(1, api.completions.size)

        val disabled = FakeAdaptiveApi(onPlan = { Response.success(AdaptivePlanResponseDto(ok = true, enabled = false)) })
        val second = viewModel(FakeLessonApi(), adaptiveRepository(disabled))
        advanceUntilIdle()
        playDeck(second) { error("a disabled plan shows nothing") }

        val preview = FakeAdaptiveApi()
        viewModel(FakeLessonApi(previewHalf = true), adaptiveRepository(preview))
        advanceUntilIdle()
        assertTrue("a free preview never asks for a plan", preview.plans.isEmpty())

        val otherLesson = FakeAdaptiveApi(onPlan = { Response.success(adaptivePlan(3, lessonOrder = 2)) })
        val third = viewModel(FakeLessonApi(), adaptiveRepository(otherLesson))
        advanceUntilIdle()
        playDeck(third) { error("another lesson's plan is not this deck's") }
    }

    @Test
    fun `a refused answer goes straight back to the lesson`() = runTest(dispatcher) {
        val adaptiveApi = FakeAdaptiveApi(onPlan = { Response.success(adaptivePlan(1)) }, onAnswer = { status(409) })
        val repository = adaptiveRepository(adaptiveApi)
        val model = viewModel(adaptive = repository)
        advanceUntilIdle()
        var shown = 0
        playDeck(model) {
            shown++
            model.answerAdaptive(selectedIndex = 0)
            advanceUntilIdle()
            assertNull(model.state.value.adaptive)
        }
        assertEquals(1, shown)
        assertEquals(0, repository.pendingCount())
    }

    @Test
    fun `an offline answer waits on the phone and is sent before the next plan`() = runTest(dispatcher) {
        val adaptiveApi = FakeAdaptiveApi(
            onPlan = { Response.success(adaptivePlan(1)) },
            onAnswer = { throw IOException("offline") },
        )
        val repository = adaptiveRepository(adaptiveApi)
        val model = viewModel(adaptive = repository)
        advanceUntilIdle()
        playDeck(model) {
            model.answerAdaptive(selectedIndex = 2)
            advanceUntilIdle()
            assertTrue(model.state.value.adaptive!!.savedOffline)
            model.continueAdaptive()
        }
        assertTrue(model.state.value.outcome is LessonOutcome.Completed)
        assertEquals(1, repository.pendingCount())

        // A 5xx keeps it; a real verdict (even a duplicate) clears it.
        adaptiveApi.onAnswer = { status(503) }
        repository.plan("hsk1", 2, "uz")
        assertEquals(1, repository.pendingCount())
        adaptiveApi.onAnswer = { Response.success(AdaptiveAnswerResponseDto(ok = true, itemId = it.itemId, duplicate = true)) }
        repository.plan("hsk1", 2, "uz")
        assertEquals(0, repository.pendingCount())
        assertEquals(List(3) { "a1:11:meaning_choice" }, adaptiveApi.answers.map { it.itemId })
        assertTrue(adaptiveApi.answers.all { it.selectedIndex == 2 })
    }

    @Test
    fun `the outbox keeps one answer per item, at most ten, for 36 hours`() = runTest(dispatcher) {
        val adaptiveApi = FakeAdaptiveApi(onAnswer = { throw IOException("offline") })
        val repository = adaptiveRepository(adaptiveApi)
        repository.answer(41, "a1:11:meaning_choice", selectedIndex = 0)
        repository.answer(41, "a1:11:meaning_choice", selectedIndex = 1)
        assertEquals(1, repository.pendingCount())
        repeat(12) { repository.answer(50L + it, "a1:1:meaning_choice", selectedIndex = 0) }
        assertEquals(AdaptiveLessonRepository.OUTBOX_MAX, repository.pendingCount())

        clock += AdaptiveLessonRepository.OUTBOX_TTL_MILLIS
        val sent = adaptiveApi.answers.size
        repository.plan("hsk1", 1, "uz")
        assertEquals("expired answers are dropped unsent", sent, adaptiveApi.answers.size)
        assertEquals(0, repository.pendingCount())
    }

    @Test
    fun `placement mirrors the server and stops before the exit check`() {
        val cases = listOf(
            Triple(listOf(2, 3, 4, 5, 6, 7, 8, 9), 3, listOf(4, 6, 8)),
            Triple(listOf(2, 3), 3, listOf(2, 3)),
            Triple(listOf(5), 1, listOf(5)),
            Triple(listOf(2, 3, 4, 5, 6), 2, listOf(3, 5)),
            Triple((2..19).toList(), 3, listOf(6, 11, 15)),
            Triple(emptyList(), 2, emptyList()),
        )
        for ((eligible, count, expected) in cases) assertEquals(expected, adaptiveSlots(eligible, count))

        fun choice(n: Int) = ChoiceCard("ref:$n", ChoiceKind.HANZI, "", "?", listOf("a", "b"), 0, "")
        val lesson = Lesson(
            level = "hsk1", order = 1, sourceLesson = 1, part = 1, partCount = 1, isCheckpoint = false,
            title = "", subtitle = "",
            sections = listOf(
                LessonSection(1, "", "practice", listOf(UnsupportedCard("ref:0", "intro"), choice(1), choice(2), choice(3))),
                LessonSection(2, "", "learning_exit_check", listOf(choice(4), choice(5))),
            ),
        )
        assertEquals(listOf(2, 3), adaptiveBoundaries(lesson, 0))
        assertEquals("a resumed lesson only uses boundaries ahead", listOf(3), adaptiveBoundaries(lesson, 2))
    }
}
