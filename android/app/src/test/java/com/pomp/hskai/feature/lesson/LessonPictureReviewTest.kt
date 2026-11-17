package com.pomp.hskai.feature.lesson

import com.pomp.hskai.R
import com.pomp.hskai.core.audio.VoiceRecorder
import com.pomp.hskai.core.audio.VoiceRecording
import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.core.settings.LessonResumeStore
import com.pomp.hskai.data.api.CourseLessonResponse
import com.pomp.hskai.data.api.VoicePronounceResponse
import com.pomp.hskai.data.repository.CourseRepository
import com.pomp.hskai.domain.model.PictureReviewCard
import com.pomp.hskai.domain.model.PronunciationCard
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceTimeBy
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import retrofit2.Response

private const val CHOICE =
    """{"type":"hanzi_choice","prompt":"?","title":"?","options":["你","好"],"correct_index":0,"explanation":"?"}"""

/**
 * Served: 3 practice cards, then a review section with one pronunciation card
 * and a closing practice card (5 cards). The plan drops practice card 2 and
 * opens section 2 with the deck, so the learner sees
 * [choice, choice, deck, pronunciation, choice].
 */
private val PLANNED_LESSON = Json.parseToJsonElement(
    """
    {"source_lesson":1,"part_no":1,"part_count":1,"checkpoint":false,"title":"1","subtitle":"1",
     "sections":[
      {"section_no":1,"section_purpose":"practice","cards":[$CHOICE,$CHOICE,$CHOICE]},
      {"section_no":2,"section_purpose":"retention_review","cards":[
        {"type":"pronunciation","phrase":"你","pinyin":"nǐ","translation":{"uz":"sen","ru":"ты","tj":"ту"}}]},
      {"section_no":3,"section_purpose":"practice","cards":[$CHOICE]}
     ],
     "lesson_plan":{"version":1,"daily_minutes":5,
      "omit":[{"section_no":1,"card_no":2}],
      "picture_review":{"anchor":{"section_no":2,"position":"start"},"words":[
        {"zh":"苹果","pinyin":"píngguǒ","image":"🍎","meaning":{"uz":"olma","ru":"яблоко","tj":"себ"}},
        {"zh":"猫","pinyin":"māo","image":"🐈","meaning":{"uz":"mushuk","ru":"кошка","tj":"гурба"}},
        {"zh":"书","pinyin":"shū","image":"📕","meaning":{"uz":"kitob","ru":"книга","tj":"китоб"}}]}}}
    """
).jsonObject

private const val DECK_INDEX = 2

private class PlannedLessonApi(
    private val previewHalf: Boolean = false,
) : FakeLessonApi(previewHalf = previewHalf, previewCardLimit = if (previewHalf) 2 else 5) {
    override suspend fun lesson(
        authorization: String,
        lessonOrder: Int,
        accessRef: String,
    ): Response<CourseLessonResponse> {
        val base = checkNotNull(super.lesson(authorization, lessonOrder, accessRef).body())
        // total_cards counts the lesson as served, before the plan.
        return Response.success(base.copy(totalCards = 5, lesson = PLANNED_LESSON))
    }
}

private class PictureRecorder : VoiceRecorder {
    override var isRecording: Boolean = false
        private set
    var cancelCalls = 0

    override fun start() {
        isRecording = true
    }

    override suspend fun stop(): VoiceRecording {
        check(isRecording)
        isRecording = false
        return VoiceRecording("data:audio/mp4;base64,dGVzdA==", 4)
    }

    override fun cancel() {
        isRecording = false
        cancelCalls++
    }
}

/** Answers each request with the next queued reply. */
private class ScriptedScorer(vararg replies: ApiResult<VoicePronounceResponse>) : PronunciationScorer {
    private val replies = ArrayDeque(replies.toList())
    val targets = mutableListOf<String>()

    override suspend fun score(
        target: String,
        targetPinyin: String,
        language: String,
        level: String,
        audioDataUrl: String,
    ): ApiResult<VoicePronounceResponse> {
        targets += target
        return replies.removeFirst()
    }
}

private class StartAt(private val index: Int) : LessonResumeStore {
    override suspend fun lessonResumeIndex(level: String, order: Int): Int = index
    override suspend fun setLessonResumeIndex(level: String, order: Int, index: Int) = Unit
    override suspend fun clearLessonResume(level: String, order: Int) = Unit
}

private fun heard(score: Int) = ApiResult.Success(VoicePronounceResponse(ok = true, score = score))

@OptIn(ExperimentalCoroutinesApi::class)
class LessonPictureReviewTest {

    private val dispatcher = StandardTestDispatcher()

    @Before
    fun setUp() = Dispatchers.setMain(dispatcher)

    @After
    fun tearDown() = Dispatchers.resetMain()

    private fun repository(api: FakeLessonApi = PlannedLessonApi()) = CourseRepository(
        api = api,
        accessToken = { ApiResult.Success("access-1") },
        dao = NoopDao(),
        json = Json { ignoreUnknownKeys = true },
        ioDispatcher = dispatcher,
    )

    private fun viewModel(
        scorer: PronunciationScorer,
        recorder: PictureRecorder = PictureRecorder(),
        startAt: Int = DECK_INDEX,
    ) = LessonViewModel(
        repository = repository(),
        audioPlayer = FakeLessonAudioPlayer(),
        level = "hsk1",
        lessonOrder = 1,
        language = AppLanguage.RUSSIAN,
        eventIdFactory = { "android:0d1f2e3a4b5c6d7e8f90a1b2c3d4e5f6" },
        resumeStore = StartAt(startAt),
        voiceRecorder = recorder,
        pronunciationScorer = scorer,
    ).also { it.beginAttempt("attempt-1") }

    /** One full try: record, score, and let the reveal and leave play out. */
    private fun kotlinx.coroutines.test.TestScope.sayFront(model: LessonViewModel) {
        model.speakPicture()
        advanceTimeBy(LessonViewModel.PRONUNCIATION_WINDOW_MILLIS + 1)
        runCurrent()
    }

    private fun kotlinx.coroutines.test.TestScope.letItLeave(holdMillis: Long) {
        advanceTimeBy(holdMillis + 1)
        runCurrent()
        advanceTimeBy(LessonViewModel.PICTURE_LEAVE_MILLIS + 1)
        runCurrent()
    }

    // ------------------------------------------------------------ queue rule

    @Test
    fun `a missed word goes to the back until it has been missed three times`() {
        var deck = PictureDeckState(order = listOf(0, 1))
        deck = deck.after(PictureOutcome.WRONG)
        assertEquals(listOf(1, 0), deck.order)
        deck = deck.after(PictureOutcome.PASS)
        assertEquals(listOf(0), deck.order)
        deck = deck.after(PictureOutcome.WRONG)
        assertEquals(listOf(0), deck.order)
        deck = deck.after(PictureOutcome.WRONG)
        assertTrue(deck.order.isEmpty())
        assertEquals(3, deck.tries[0])
        assertEquals(4, deck.moves)
    }

    @Test
    fun `a skipped word leaves without being counted as right or wrong`() {
        val deck = PictureDeckState(order = listOf(0, 1), unclear = true).after(PictureOutcome.SKIP)
        assertEquals(listOf(1), deck.order)
        assertTrue(deck.tries.isEmpty())
        assertFalse(deck.unclear)
        assertEquals(PicturePhase.Ask, deck.phase)
    }

    // ---------------------------------------------------------- repository

    @Test
    fun `the plan is applied after the served card count is checked`() = runTest(dispatcher) {
        val snapshot = (repository().lesson("hsk1", 1, AppLanguage.UZBEK) as ApiResult.Success).value
        val cards = snapshot.lesson.cards

        assertEquals(5, cards.size)
        assertTrue(cards[DECK_INDEX] is PictureReviewCard)
        assertTrue(cards[DECK_INDEX + 1] is PronunciationCard)
        assertEquals(
            listOf("section:1:card:1", "section:1:card:3", "picture_review", "section:2:card:1", "section:3:card:1"),
            cards.map { it.materialRef.substringAfter("lesson:hsk1:1:") },
        )
        assertEquals(listOf("olma", "mushuk", "kitob"), (cards[DECK_INDEX] as PictureReviewCard).words.map { it.meaning })
    }

    @Test
    fun `a free preview keeps the lesson as served`() = runTest(dispatcher) {
        val snapshot = (
            repository(PlannedLessonApi(previewHalf = true)).lesson("hsk1", 1, AppLanguage.UZBEK)
                as ApiResult.Success
            ).value

        assertTrue(snapshot.lesson.cards.none { it is PictureReviewCard })
        assertEquals(5, snapshot.lesson.cards.size)
        assertFalse(snapshot.completionAllowed)
    }

    // ---------------------------------------------------------- lesson flow

    @Test
    fun `a right answer flips the card, then it leaves and the lesson waits for the deck`() = runTest(dispatcher) {
        val scorer = ScriptedScorer(heard(90))
        val model = viewModel(scorer)
        advanceUntilIdle()

        assertEquals(DECK_INDEX, model.state.value.cardIndex)
        assertEquals(listOf(0, 1, 2), model.state.value.pictureDeck?.order)
        val before = model.state.value

        sayFront(model)
        assertEquals(listOf("苹果"), scorer.targets)
        assertEquals(PicturePhase.Reveal(passed = true), model.state.value.pictureDeck?.phase)

        letItLeave(LessonViewModel.PICTURE_PASS_HOLD_MILLIS)
        val after = model.state.value
        assertEquals(DECK_INDEX, after.cardIndex)
        assertEquals(listOf(1, 2), after.pictureDeck?.order)
        assertEquals(PicturePhase.Ask, after.pictureDeck?.phase)
        // The deck is ungraded practice.
        assertEquals(before.hearts, after.hearts)
        assertEquals(before.correctCount, after.correctCount)
        assertEquals(before.gradedAnswered, after.gradedAnswered)
        assertEquals(before.answerStreak, after.answerStreak)
    }

    @Test
    fun `a wrong answer shows the answer and asks the word again later`() = runTest(dispatcher) {
        val model = viewModel(ScriptedScorer(heard(20)))
        advanceUntilIdle()
        val hearts = model.state.value.hearts

        sayFront(model)
        assertEquals(PicturePhase.Reveal(passed = false), model.state.value.pictureDeck?.phase)

        // The answer stays up longer after a miss.
        advanceTimeBy(LessonViewModel.PICTURE_PASS_HOLD_MILLIS + 1)
        runCurrent()
        assertEquals(PicturePhase.Reveal(passed = false), model.state.value.pictureDeck?.phase)

        advanceTimeBy(LessonViewModel.PICTURE_WRONG_HOLD_MILLIS - LessonViewModel.PICTURE_PASS_HOLD_MILLIS)
        runCurrent()
        assertEquals(PicturePhase.Leaving(PictureOutcome.WRONG), model.state.value.pictureDeck?.phase)
        advanceTimeBy(LessonViewModel.PICTURE_LEAVE_MILLIS + 1)
        runCurrent()

        assertEquals(listOf(1, 2, 0), model.state.value.pictureDeck?.order)
        assertEquals(1, model.state.value.pictureDeck?.tries?.get(0))
        assertEquals(hearts, model.state.value.hearts)
        assertEquals(DECK_INDEX, model.state.value.cardIndex)
    }

    @Test
    fun `an unclear recording is not a verdict`() = runTest(dispatcher) {
        val model = viewModel(
            ScriptedScorer(ApiResult.Success(VoicePronounceResponse(ok = true, score = 0, unclear = true)))
        )
        advanceUntilIdle()

        sayFront(model)
        val deck = model.state.value.pictureDeck
        assertEquals(PicturePhase.Ask, deck?.phase)
        assertTrue(deck?.unclear == true)
        assertEquals(listOf(0, 1, 2), deck?.order)
        assertTrue(deck?.tries.isNullOrEmpty())
    }

    @Test
    fun `skip moves only the front card and the last one opens the next lesson card`() = runTest(dispatcher) {
        val recorder = PictureRecorder()
        val model = viewModel(ScriptedScorer(), recorder)
        advanceUntilIdle()

        model.skipPicture()
        assertEquals(PicturePhase.Leaving(PictureOutcome.SKIP), model.state.value.pictureDeck?.phase)
        advanceTimeBy(LessonViewModel.PICTURE_LEAVE_MILLIS + 1)
        runCurrent()
        assertEquals(listOf(1, 2), model.state.value.pictureDeck?.order)

        // Skipping while recording drops the recording too.
        model.speakPicture()
        assertTrue(recorder.isRecording)
        model.skipPicture()
        assertFalse(recorder.isRecording)
        advanceTimeBy(LessonViewModel.PICTURE_LEAVE_MILLIS + 1)
        runCurrent()
        assertEquals(listOf(2), model.state.value.pictureDeck?.order)

        model.skipPicture()
        advanceTimeBy(LessonViewModel.PICTURE_LEAVE_MILLIS + 1)
        runCurrent()

        assertEquals(DECK_INDEX + 1, model.state.value.cardIndex)
        assertTrue(model.state.value.currentCard is PronunciationCard)
        assertNull(model.state.value.pictureDeck)
        assertEquals(0, model.state.value.gradedAnswered)
    }

    @Test
    fun `a spent daily allowance ends the deck with the usual limit message`() = runTest(dispatcher) {
        val limit = ApiError.Server("PRONOUNCE_LIMIT_EXCEEDED", R.string.error_feature_limit)
        val model = viewModel(ScriptedScorer(ApiResult.Failure(limit)))
        advanceUntilIdle()

        sayFront(model)

        assertEquals(DECK_INDEX + 1, model.state.value.cardIndex)
        assertNull(model.state.value.pictureDeck)
        assertEquals(limit, model.state.value.pronunciationError)
    }

    @Test
    fun `leaving the lesson mid-recording releases the microphone`() = runTest(dispatcher) {
        val recorder = PictureRecorder()
        val model = viewModel(ScriptedScorer(heard(90)), recorder)
        advanceUntilIdle()

        model.speakPicture()
        model.endAttempt("attempt-1")
        advanceUntilIdle()

        assertFalse(recorder.isRecording)
        assertTrue(recorder.cancelCalls > 0)
    }
}
