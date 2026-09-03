package com.pomp.hskai.feature.lesson

import com.pomp.hskai.core.audio.LessonAudioPlayer
import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.AndroidCourseApi
import com.pomp.hskai.data.api.CourseCompleteRequest
import com.pomp.hskai.data.api.CourseCompleteResponse
import com.pomp.hskai.data.api.CourseLessonResponse
import com.pomp.hskai.data.api.CourseMapDto
import com.pomp.hskai.data.api.DictionaryResponse
import com.pomp.hskai.data.api.LanguageRequest
import com.pomp.hskai.data.api.NotificationsRequest
import com.pomp.hskai.data.api.OkResponse
import com.pomp.hskai.data.local.CourseMapCacheEntity
import com.pomp.hskai.data.local.CourseMapDao
import com.pomp.hskai.data.repository.CourseRepository
import com.pomp.hskai.domain.model.ChoiceCard
import com.pomp.hskai.domain.model.MatchPairsCard
import com.pomp.hskai.domain.model.SentenceBuilderCard
import com.pomp.hskai.domain.model.UnsupportedCard
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import okhttp3.ResponseBody
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import retrofit2.Response

private const val LESSON_BODY = """
{"ok":true,"lesson":{
 "source_lesson":1,"part_no":1,"part_count":3,"checkpoint":false,
 "title":{"uz":"1-dars","ru":"Урок 1","tj":"Дарси 1"},
 "subtitle":{"uz":"1-qism","ru":"Часть 1","tj":"Қисми 1"},
 "sections":[{"section_no":1,"section_purpose":"practice","cards":[
   {"type":"active_word","word":{"no":1,"zh":"你","pinyin":"nǐ","pos":"pron.",
    "meaning":{"uz":"sen","ru":"ты","tj":"ту"}}},
   {"type":"hanzi_choice","prompt":{"uz":"?","ru":"?","tj":"?"},
    "title":{"uz":"Tanlang","ru":"?","tj":"?"},
    "options":["你","好"],"correct_index":0,
    "explanation":{"uz":"你 = sen","ru":"?","tj":"?"}},
   {"type":"sentence_builder","sentence":{"uz":"Salom!","ru":"?","tj":"?"},
    "tokens":["好","你"],"answer_tokens":["你","好"],
    "explanation":{"uz":"你好！","ru":"?","tj":"?"}},
   {"type":"match_pairs","pairs":[["你",{"uz":"sen","ru":"ты","tj":"ту"}],
    ["好",{"uz":"yaxshi","ru":"хорошо","tj":"хуб"}]],
    "explanation":{"uz":"Juftliklar","ru":"?","tj":"?"}},
   {"type":"tone_drill_v2"},
   {"type":"pronunciation","phrase":"你","pinyin":"nǐ",
    "translation":{"uz":"sen","ru":"ты","tj":"ту"}}
 ]}]}}
"""

private class NoopDao : CourseMapDao {
    override suspend fun find(level: String): CourseMapCacheEntity? = null
    override suspend fun findMostRecent(): CourseMapCacheEntity? = null
    override suspend fun upsert(entity: CourseMapCacheEntity) = Unit
    override suspend fun clear() = Unit
}

private fun lessonPayload() = Json.parseToJsonElement(LESSON_BODY)
    .jsonObject
    .getValue("lesson")
    .jsonObject

private open class FakeLessonApi(
    private val previewHalf: Boolean = false,
    private val previewCardLimit: Int = if (previewHalf) 3 else 6,
) : AndroidCourseApi {
    val completions = mutableListOf<CourseCompleteRequest>()
    var completeDuplicate = false
    var lastTtsAuthorization: String? = null
    var lastTtsText: String? = null

    override suspend fun courseMap(
        authorization: String,
        timezoneOffsetMinutes: Int,
    ): Response<CourseMapDto> = throw NotImplementedError()

    override suspend fun lesson(
        authorization: String,
        lessonOrder: Int,
    ): Response<CourseLessonResponse> = Response.success(
        CourseLessonResponse(
            ok = true,
            level = "hsk1",
            lessonOrder = lessonOrder,
            previewHalf = previewHalf,
            previewCardLimit = previewCardLimit,
            totalCards = 6,
            completionAllowed = !previewHalf,
            completionError = if (previewHalf) "free_preview_completed" else null,
            lesson = lessonPayload(),
        )
    )

    override suspend fun tts(
        authorization: String,
        text: String,
        rate: String,
    ): Response<ResponseBody> {
        lastTtsAuthorization = authorization
        lastTtsText = text
        return Response.success("audio:$text".toResponseBody())
    }

    override suspend fun complete(
        authorization: String,
        body: CourseCompleteRequest,
    ): Response<CourseCompleteResponse> {
        completions += body
        return Response.success(
            CourseCompleteResponse(
                ok = true,
                completedLesson = body.lessonOrder,
                completedLessonsCount = body.lessonOrder,
                duplicate = completeDuplicate,
            )
        )
    }

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

private class FakeLessonAudioPlayer : LessonAudioPlayer {
    val clips = mutableListOf<ByteArray>()
    var releaseCalls = 0

    override suspend fun play(mp3: ByteArray) {
        clips += mp3
    }

    override fun release() {
        releaseCalls++
    }
}

@OptIn(ExperimentalCoroutinesApi::class)
class LessonViewModelTest {

    private val dispatcher = StandardTestDispatcher()

    @Before
    fun setUp() = Dispatchers.setMain(dispatcher)

    @After
    fun tearDown() = Dispatchers.resetMain()

    private fun repository(api: AndroidCourseApi) = CourseRepository(
        api = api,
        accessToken = { ApiResult.Success("access-1") },
        dao = NoopDao(),
        json = Json { ignoreUnknownKeys = true },
        ioDispatcher = dispatcher,
    )

    private fun viewModel(
        api: AndroidCourseApi = FakeLessonApi(),
        audioPlayer: LessonAudioPlayer = FakeLessonAudioPlayer(),
        eventIdFactory: () -> String = {
            "android:0d1f2e3a4b5c6d7e8f90a1b2c3d4e5f6"
        },
    ) = LessonViewModel(
        repository = repository(api),
        audioPlayer = audioPlayer,
        level = "hsk1",
        lessonOrder = 1,
        language = AppLanguage.UZBEK,
        eventIdFactory = eventIdFactory,
    ).also { it.beginAttempt("attempt-1") }

    @Test
    fun `the whole deck is loaded, including the unknown card`() = runTest {
        val model = viewModel()
        advanceUntilIdle()

        val state = model.state.value
        assertFalse(state.isLoading)
        assertEquals(6, state.totalCards)
        // Unknown cards are kept and are not graded.
        assertTrue(state.cards[4] is UnsupportedCard)
        assertEquals(3, state.lesson?.gradedCards?.size)
    }

    @Test
    fun `a correct choice is counted and explained`() = runTest {
        val model = viewModel()
        advanceUntilIdle()
        model.acknowledge() // new word

        val card = model.state.value.currentCard as ChoiceCard
        model.answerChoice(card, 0)

        val answer = model.state.value.answer as AnswerState.Checked
        assertTrue(answer.isCorrect)
        assertEquals("你 = sen", answer.explanation)
        assertEquals(1, model.state.value.correctCount)
        assertEquals(1, model.state.value.gradedAnswered)
    }

    @Test
    fun `a wrong answer is reported with only the selection, never the answer`() =
        runTest {
            val api = FakeLessonApi()
            val model = viewModel(api)
            advanceUntilIdle()

            model.acknowledge()
            val choice = model.state.value.currentCard as ChoiceCard
            model.answerChoice(choice, 1)
            assertFalse((model.state.value.answer as AnswerState.Checked).isCorrect)
            model.advance()

            val builder = model.state.value.currentCard as SentenceBuilderCard
            model.answerBuilder(builder, listOf("好", "你"))
            model.advance()

            val pairs = model.state.value.currentCard as MatchPairsCard
            model.answerMatchPairs(pairs, listOf(0 to 1))
            model.advance()
            model.acknowledge() // unsupported
            model.acknowledge() // pronunciation
            advanceUntilIdle()

            val sent = api.completions.single()
            assertEquals(3, sent.mistakes.size)
            assertEquals(
                listOf(
                    "lesson:hsk1:1:section:1:card:2",
                    "lesson:hsk1:1:section:1:card:3",
                    "lesson:hsk1:1:section:1:card:4",
                ),
                sent.mistakes.map { it.materialRef },
            )
            // Only the learner's raw selection travels; the server rebuilds
            // the question and decides what was wrong.
            assertEquals(1, sent.mistakes[0].selectedIndex)
            assertEquals(listOf("好", "你"), sent.mistakes[1].selectedTokens)
            assertEquals(0, sent.mistakes[2].selectedLeftIndex)
            assertEquals(1, sent.mistakes[2].selectedRightIndex)
        }

    @Test
    fun `answering twice on the same card is ignored`() = runTest {
        val model = viewModel()
        advanceUntilIdle()
        model.acknowledge()

        val card = model.state.value.currentCard as ChoiceCard
        model.answerChoice(card, 1)
        model.answerChoice(card, 0)

        // The first answer stands; accuracy cannot be farmed by re-tapping.
        assertFalse((model.state.value.answer as AnswerState.Checked).isCorrect)
        assertEquals(0, model.state.value.correctCount)
        assertEquals(1, model.state.value.gradedAnswered)
    }

    @Test
    fun `finishing reports the completion once with the stable event id`() = runTest {
        val api = FakeLessonApi()
        val model = viewModel(api)
        advanceUntilIdle()
        repeat(6) {
            val card = model.state.value.currentCard
            if (card is ChoiceCard) model.answerChoice(card, card.correctIndex)
            model.advance()
        }
        advanceUntilIdle()

        assertEquals(1, api.completions.size)
        assertEquals(
            "android:0d1f2e3a4b5c6d7e8f90a1b2c3d4e5f6",
            api.completions.single().eventId,
        )
        val outcome = model.state.value.outcome as LessonOutcome.Completed
        assertFalse(outcome.duplicate)
    }

    @Test
    fun `a failed completion can be retried with the same event id`() = runTest {
        val failing = object : FakeLessonApi() {
            var shouldFail = true
            override suspend fun complete(
                authorization: String,
                body: CourseCompleteRequest,
            ): Response<CourseCompleteResponse> {
                if (shouldFail) {
                    shouldFail = false
                    completions += body
                    throw java.io.IOException("offline")
                }
                return super.complete(authorization, body)
            }
        }
        val model = viewModel(failing)
        advanceUntilIdle()
        repeat(6) { model.advanceThroughCard() }
        advanceUntilIdle()

        assertTrue(model.state.value.outcome is LessonOutcome.Failed)

        model.retryCompletion()
        advanceUntilIdle()

        assertTrue(model.state.value.outcome is LessonOutcome.Completed)
        // Same id both times, so the server treats the retry as the same
        // attempt instead of awarding XP twice.
        assertEquals(1, failing.completions.map { it.eventId }.distinct().size)
    }

    @Test
    fun `reopening the same lesson starts a clean attempt with a new event id`() = runTest {
        val api = FakeLessonApi()
        var sequence = 0
        val model = viewModel(api) {
            sequence++
            "android:" + sequence.toString().padStart(32, '0')
        }
        advanceUntilIdle()
        repeat(6) { model.advanceThroughCard() }
        advanceUntilIdle()
        assertTrue(model.state.value.outcome is LessonOutcome.Completed)

        model.beginAttempt("attempt-2")
        advanceUntilIdle()

        assertEquals(LessonOutcome.InProgress, model.state.value.outcome)
        assertEquals(0, model.state.value.cardIndex)
        assertEquals(0, model.state.value.correctCount)
        repeat(6) { model.advanceThroughCard() }
        advanceUntilIdle()

        assertEquals(2, api.completions.size)
        assertEquals(2, api.completions.map { it.eventId }.distinct().size)
    }

    @Test
    fun `completion sends at most fifty mistakes`() = runTest {
        val api = FakeLessonApi()
        val model = viewModel(api)
        advanceUntilIdle()

        model.acknowledge()
        val choice = model.state.value.currentCard as ChoiceCard
        model.answerChoice(choice, choice.correctIndex)
        model.advance()
        val builder = model.state.value.currentCard as SentenceBuilderCard
        model.answerBuilder(builder, builder.answerTokens)
        model.advance()
        val pairs = model.state.value.currentCard as MatchPairsCard
        model.answerMatchPairs(pairs, List(60) { it % 2 to (it + 1) % 2 })
        model.advance()
        model.acknowledge()
        model.acknowledge()
        advanceUntilIdle()

        assertEquals(LessonViewModel.MAX_MISTAKES_PER_COMPLETION, api.completions.single().mistakes.size)
    }

    @Test
    fun `audio uses bearer endpoint and is handed to the player`() = runTest {
        val api = FakeLessonApi()
        val player = FakeLessonAudioPlayer()
        val model = viewModel(api, audioPlayer = player)
        advanceUntilIdle()

        model.playAudio("你好")
        advanceUntilIdle()

        assertEquals("Bearer access-1", api.lastTtsAuthorization)
        assertEquals("你好", api.lastTtsText)
        assertEquals("audio:你好", player.clips.single().decodeToString())
        assertFalse(model.state.value.isAudioLoading)
    }

    @Test
    fun `ending an attempt before TTS returns never plays stale audio`() = runTest {
        val requestStarted = CompletableDeferred<Unit>()
        val response = CompletableDeferred<Response<ResponseBody>>()
        val api = object : FakeLessonApi() {
            override suspend fun tts(
                authorization: String,
                text: String,
                rate: String,
            ): Response<ResponseBody> {
                requestStarted.complete(Unit)
                return response.await()
            }
        }
        val player = FakeLessonAudioPlayer()
        val model = viewModel(api, audioPlayer = player)
        advanceUntilIdle()

        model.playAudio("你好")
        runCurrent()
        assertTrue(requestStarted.isCompleted)

        model.endAttempt("attempt-1")
        response.complete(Response.success("stale-audio".toResponseBody()))
        advanceUntilIdle()

        assertTrue(player.clips.isEmpty())
        assertFalse(model.state.value.isAudioLoading)
        assertTrue(player.releaseCalls >= 2)
    }

    @Test
    fun `a half preview stops midway and never reports a completion`() = runTest {
        val api = FakeLessonApi(previewHalf = true, previewCardLimit = 3)
        val model = viewModel(api)
        advanceUntilIdle()

        // The lesson endpoint, not the client, owns this limit.
        repeat(3) { model.advanceThroughCard() }
        advanceUntilIdle()

        assertEquals(LessonOutcome.PreviewExhausted, model.state.value.outcome)
        assertTrue(api.completions.isEmpty())
    }

    @Test
    fun `a load failure surfaces the mapped error`() = runTest {
        val broken = object : FakeLessonApi() {
            override suspend fun lesson(
                authorization: String,
                lessonOrder: Int,
            ): Response<CourseLessonResponse> = throw java.io.IOException("offline")
        }
        val model = viewModel(broken)
        advanceUntilIdle()

        assertEquals(ApiError.Offline, model.state.value.error)
        assertEquals(0, model.state.value.totalCards)
    }

    private fun LessonViewModel.advanceThroughCard() {
        val card = state.value.currentCard
        if (card is ChoiceCard) answerChoice(card, card.correctIndex)
        advance()
    }
}
