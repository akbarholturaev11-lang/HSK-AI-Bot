package com.pomp.hskai.feature.practice

import com.pomp.hskai.core.audio.LessonAudioPlayer
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.AndroidCourseApi
import com.pomp.hskai.data.api.AndroidFeatureApi
import com.pomp.hskai.data.api.ExamCompleteRequest
import com.pomp.hskai.data.api.ExamCompleteResponse
import com.pomp.hskai.data.api.ExamQuestionDto
import com.pomp.hskai.data.api.ExamSessionDto
import com.pomp.hskai.data.api.ExamStartRequest
import com.pomp.hskai.data.api.ExamStartResponse
import com.pomp.hskai.data.api.MistakeReviewAnswerRequest
import com.pomp.hskai.data.api.MistakeReviewAnswerResponse
import com.pomp.hskai.data.api.MistakeReviewCompleteRequest
import com.pomp.hskai.data.api.MistakeReviewCompleteResponse
import com.pomp.hskai.data.api.MistakeReviewQuestionDto
import com.pomp.hskai.data.api.MistakeReviewSessionDto
import com.pomp.hskai.data.api.MistakeReviewStartRequest
import com.pomp.hskai.data.api.MistakeReviewStartResponse
import com.pomp.hskai.data.api.MistakeTargetDto
import com.pomp.hskai.data.api.MistakesOverviewResponse
import com.pomp.hskai.data.api.PracticeCompleteRequest
import com.pomp.hskai.data.api.PracticeCompleteResponse
import com.pomp.hskai.data.api.PracticeQuestionDto
import com.pomp.hskai.data.api.PracticeSessionDto
import com.pomp.hskai.data.api.PracticeStartRequest
import com.pomp.hskai.data.api.PracticeStartResponse
import com.pomp.hskai.data.local.CourseMapCacheEntity
import com.pomp.hskai.data.local.CourseMapDao
import com.pomp.hskai.data.repository.CourseRepository
import com.pomp.hskai.data.repository.FeatureRepository
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
import okhttp3.ResponseBody
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import retrofit2.Response

/** Unrelated API methods fail loudly; the delegated methods below exercise real repositories. */
private fun <T> unusedApi(type: Class<T>): T = type.cast(Proxy.newProxyInstance(
    type.classLoader,
    arrayOf(type),
) { _, method, _ -> error("Unexpected API call: ${method.name}") })

private fun practiceSession(level: String) = PracticeStartResponse(
    ok = true,
    session = PracticeSessionDto(
        id = "practice:$level", mode = "placement", level = level,
        questions = listOf(PracticeQuestionDto(id = "p1", options = listOf("是", "不"), answerIndex = 0)),
    ),
)

private fun examSession(level: String) = ExamStartResponse(
    ok = true,
    session = ExamSessionDto(
        id = "exam:$level", level = level,
        questions = listOf(ExamQuestionDto(id = "e1", options = listOf("是", "不"))),
    ),
)

private fun reviewSession(id: String, builder: Boolean = false, autoplay: Boolean = false) =
    MistakeReviewStartResponse(
        ok = true,
        session = MistakeReviewSessionDto(
            id = id,
            questions = listOf(MistakeReviewQuestionDto(
                id = "r1", options = if (builder) emptyList() else listOf("是", "不"),
                tokens = if (builder) listOf("我", "是") else emptyList(),
                autoplay = autoplay, audioText = if (autoplay) "你好" else "",
            )),
        ),
    )

private class CoursePracticeApi : AndroidFeatureApi by unusedApi(AndroidFeatureApi::class.java) {
    val practiceStarts = mutableListOf<PracticeStartRequest>()
    val examStarts = mutableListOf<ExamStartRequest>()
    val reviewStarts = mutableListOf<MistakeReviewStartRequest>()
    var mistakesCalls = 0
    var practiceStartReply: suspend (PracticeStartRequest) -> Response<PracticeStartResponse> = {
        Response.success(practiceSession(it.level))
    }
    var practiceCompleteReply: suspend () -> Response<PracticeCompleteResponse> = {
        Response.success(PracticeCompleteResponse(ok = true, score = 1, total = 1))
    }
    var examStartReply: suspend (ExamStartRequest) -> Response<ExamStartResponse> = {
        Response.success(examSession(it.level))
    }
    var examCompleteReply: suspend () -> Response<ExamCompleteResponse> = {
        Response.success(ExamCompleteResponse(ok = true, score = 1, total = 1))
    }
    var reviewStartReply: suspend () -> Response<MistakeReviewStartResponse> = {
        Response.success(reviewSession("review:old"))
    }
    var reviewAnswerReply: suspend () -> Response<MistakeReviewAnswerResponse> = {
        Response.success(MistakeReviewAnswerResponse(ok = true, correct = true))
    }
    var reviewCompleteReply: suspend () -> Response<MistakeReviewCompleteResponse> = {
        Response.success(MistakeReviewCompleteResponse(ok = true, score = 1, total = 1))
    }
    var mistakesReply: suspend () -> Response<MistakesOverviewResponse> = {
        Response.success(MistakesOverviewResponse(ok = true))
    }

    override suspend fun practiceStart(authorization: String, body: PracticeStartRequest): Response<PracticeStartResponse> {
        practiceStarts += body
        return practiceStartReply(body)
    }
    override suspend fun practiceComplete(authorization: String, body: PracticeCompleteRequest) = practiceCompleteReply()
    override suspend fun examStart(authorization: String, body: ExamStartRequest): Response<ExamStartResponse> {
        examStarts += body
        return examStartReply(body)
    }
    override suspend fun examComplete(authorization: String, body: ExamCompleteRequest) = examCompleteReply()
    override suspend fun mistakeReviewStart(authorization: String, body: MistakeReviewStartRequest): Response<MistakeReviewStartResponse> {
        reviewStarts += body
        return reviewStartReply()
    }
    override suspend fun mistakeReviewAnswer(authorization: String, body: MistakeReviewAnswerRequest) = reviewAnswerReply()
    override suspend fun mistakeReviewComplete(authorization: String, body: MistakeReviewCompleteRequest) = reviewCompleteReply()
    override suspend fun mistakes(
        authorization: String, category: String?, limit: Int, offset: Int, view: String?,
    ): Response<MistakesOverviewResponse> {
        mistakesCalls++
        return mistakesReply()
    }
}

@OptIn(ExperimentalCoroutinesApi::class)
class PracticeCourseChangeTest {
    private val dispatcher = StandardTestDispatcher()
    private val tool = PracticeToolSpec("placement", "", 0, 0, "HSK")
    @Before fun setUp() { Dispatchers.setMain(dispatcher) }
    @After fun tearDown() { Dispatchers.resetMain() }

    private class Audio : LessonAudioPlayer {
        var played = 0
        var releases = 0
        override suspend fun play(mp3: ByteArray, speed: Float) { played++ }
        override fun release() { releases++ }
    }

    private class Fixture {
        val api = CoursePracticeApi()
        val audio = Audio()
        var ttsReply: suspend () -> Response<ResponseBody> = { Response.success("audio".toResponseBody()) }
        val courseApi = object : AndroidCourseApi by unusedApi(AndroidCourseApi::class.java) {
            override suspend fun tts(authorization: String, text: String, rate: String) = ttsReply()
        }
        private val dao = object : CourseMapDao {
            override suspend fun find(level: String): CourseMapCacheEntity? = null
            override suspend fun findMostRecent(): CourseMapCacheEntity? = null
            override suspend fun upsert(entity: CourseMapCacheEntity) = Unit
            override suspend fun clear() = Unit
        }
        val vm = PracticeViewModel(
            FeatureRepository(api, accessToken = { ApiResult.Success("test-access") }),
            CourseRepository(courseApi, accessToken = { ApiResult.Success("test-access") }, dao = dao,
                json = Json { ignoreUnknownKeys = true }),
            audio,
        ).also { it.onCourseChanged("hsk1") }
    }

    @Test
    fun `same course preserves an active run but changed course clears it`() = runTest(dispatcher) {
        val f = Fixture()
        f.vm.startPractice(tool, "hsk1", "uz")
        runCurrent()
        f.vm.selectPracticeOption(0)
        f.vm.onCourseChanged(" HSK1 ")
        assertEquals("practice:hsk1", f.vm.state.value.session!!.id)
        assertEquals(0, f.vm.state.value.selectedIndex)
        f.vm.onCourseChanged("nhsk2")
        assertEquals(PracticeUiState(), f.vm.state.value)
        assertEquals(0, f.api.mistakesCalls)
    }

    @Test
    fun `completed old-course practice exam and review results do not survive switches`() = runTest(dispatcher) {
        val f = Fixture()
        f.vm.startPractice(tool, "hsk1", "uz")
        runCurrent()
        f.vm.selectPracticeOption(0); f.vm.advancePractice("uz"); runCurrent()
        assertTrue(f.vm.state.value.result != null)
        f.vm.onCourseChanged("nhsk1"); runCurrent()
        assertNull(f.vm.state.value.result)
        f.vm.startExam("nhsk1", "uz"); runCurrent()
        f.vm.selectExamOption(0); f.vm.advanceExam("uz"); runCurrent()
        assertTrue(f.vm.state.value.examResult != null)
        f.vm.onCourseChanged("nhsk2"); runCurrent()
        assertNull(f.vm.state.value.examResult)
        f.vm.startMistakeReview(); runCurrent()
        f.vm.answerReview(0); runCurrent(); f.vm.advanceReview(); runCurrent()
        assertTrue(f.vm.state.value.reviewResult != null)
        f.vm.onCourseChanged("hsk1"); runCurrent()
        assertNull(f.vm.state.value.reviewResult)
    }

    @Test
    fun `a changed course never retries blocked practice exam or review attempts`() = runTest(dispatcher) {
        for (kind in listOf("practice", "exam", "review")) {
            val f = Fixture()
            val errorBody = """{"ok":false,"error":"free_feature_limit_reached"}"""
            f.api.practiceStartReply = { Response.error(429, errorBody.toResponseBody()) }
            f.api.examStartReply = { Response.error(429, errorBody.toResponseBody()) }
            f.api.reviewStartReply = { Response.error(429, errorBody.toResponseBody()) }
            when (kind) {
                "practice" -> f.vm.startPractice(tool, "hsk1", "uz")
                "exam" -> f.vm.startExam("hsk1", "uz")
                else -> f.vm.startMistakeReview()
            }
            runCurrent()
            assertTrue(f.vm.state.value.error is ApiError.LimitReached)
            f.vm.onCourseChanged("nhsk3")
            f.vm.onAccessChanged()
            f.vm.startWithAd("old-ad")
            runCurrent()
            assertNull(f.vm.state.value.error)
            assertNull(f.vm.state.value.pendingTool)
            assertEquals("No saved retry survives a course change", 1,
                f.api.practiceStarts.size + f.api.examStarts.size + f.api.reviewStarts.size)
        }
    }

    @Test
    fun `queued old-course start is discarded before it spends server access`() = runTest(dispatcher) {
        val f = Fixture()
        f.vm.startPractice(tool, "hsk1", "uz")
        f.vm.onCourseChanged("nhsk1")
        runCurrent()
        assertTrue(f.api.practiceStarts.isEmpty())
        assertFalse(f.vm.state.value.isStarting)
        assertNull(f.vm.state.value.session)
    }

    @Test
    fun `late practice start cannot replace or clear loading for the new-course start`() = runTest(dispatcher) {
        val f = Fixture()
        val old = CompletableDeferred<Response<PracticeStartResponse>>()
        val fresh = CompletableDeferred<Response<PracticeStartResponse>>()
        f.api.practiceStartReply = { if (it.level == "hsk1") old.await() else fresh.await() }
        f.vm.startPractice(tool, "hsk1", "uz"); runCurrent()
        f.vm.onCourseChanged("nhsk1")
        f.vm.startPractice(tool, "nhsk1", "uz"); runCurrent()
        old.complete(Response.success(practiceSession("hsk1"))); runCurrent()
        assertNull(f.vm.state.value.session)
        assertTrue(f.vm.state.value.isStarting)
        fresh.complete(Response.success(practiceSession("nhsk1"))); runCurrent()
        assertEquals("nhsk1", f.vm.state.value.session!!.level)
        assertFalse(f.vm.state.value.isStarting)
    }

    @Test
    fun `late practice completion cannot attach an old result to the new course`() = runTest(dispatcher) {
        val f = Fixture()
        val old = CompletableDeferred<Response<PracticeCompleteResponse>>()
        f.api.practiceCompleteReply = { old.await() }
        f.vm.startPractice(tool, "hsk1", "uz"); runCurrent()
        f.vm.selectPracticeOption(0); f.vm.advancePractice("uz"); runCurrent()
        f.vm.onCourseChanged("nhsk1")
        f.vm.startPractice(tool, "nhsk1", "uz"); runCurrent()
        old.complete(Response.success(PracticeCompleteResponse(ok = true, percent = 100))); runCurrent()
        assertEquals("nhsk1", f.vm.state.value.session!!.level)
        assertNull(f.vm.state.value.result)
        assertFalse(f.vm.state.value.isCompleting)
    }

    @Test
    fun `late exam start and completion cannot restore the old course exam`() = runTest(dispatcher) {
        val f = Fixture()
        val start = CompletableDeferred<Response<ExamStartResponse>>()
        f.api.examStartReply = { start.await() }
        f.vm.startExam("hsk1", "uz"); runCurrent()
        f.vm.onCourseChanged("nhsk1")
        start.complete(Response.success(examSession("hsk1"))); runCurrent()
        assertNull(f.vm.state.value.examSession)
        assertEquals("", f.vm.state.value.examLevel)
        f.api.examStartReply = { Response.success(examSession(it.level)) }
        val completion = CompletableDeferred<Response<ExamCompleteResponse>>()
        f.api.examCompleteReply = { completion.await() }
        f.vm.startExam("nhsk1", "uz"); runCurrent()
        f.vm.selectExamOption(0); f.vm.advanceExam("uz"); runCurrent()
        f.vm.onCourseChanged("hsk1")
        completion.complete(Response.success(ExamCompleteResponse(ok = true, percent = 100))); runCurrent()
        assertNull(f.vm.state.value.examResult)
        assertFalse(f.vm.state.value.isCompleting)
    }

    @Test
    fun `late review start does not resurrect an old session or autoplay audio`() = runTest(dispatcher) {
        val f = Fixture()
        val old = CompletableDeferred<Response<MistakeReviewStartResponse>>()
        f.api.reviewStartReply = { old.await() }
        f.vm.startMistakeReview(); runCurrent()
        f.vm.onCourseChanged("nhsk1")
        old.complete(Response.success(reviewSession("old", autoplay = true))); runCurrent()
        assertNull(f.vm.state.value.reviewSession)
        assertFalse(f.vm.state.value.isStarting)
        assertEquals(0, f.audio.played)
    }

    @Test
    fun `late option and builder verdicts cannot mark answers in the new course review`() = runTest(dispatcher) {
        for (builder in listOf(false, true)) {
            val f = Fixture()
            f.api.reviewStartReply = { Response.success(reviewSession("old", builder = builder)) }
            val old = CompletableDeferred<Response<MistakeReviewAnswerResponse>>()
            f.api.reviewAnswerReply = { old.await() }
            f.vm.startMistakeReview(); runCurrent()
            if (builder) f.vm.answerReviewTokens(listOf("我", "是")) else f.vm.answerReview(0)
            runCurrent()
            f.vm.onCourseChanged("nhsk1")
            f.api.reviewStartReply = { Response.success(reviewSession("fresh", builder = builder)) }
            f.vm.startMistakeReview(); runCurrent()
            old.complete(Response.success(MistakeReviewAnswerResponse(ok = true, correct = true))); runCurrent()
            assertEquals("fresh", f.vm.state.value.reviewSession!!.id)
            assertNull(f.vm.state.value.reviewFeedback)
            assertTrue(f.vm.state.value.reviewAnswers.isEmpty())
            assertEquals(0, f.vm.state.value.reviewStreak)
        }
    }

    @Test
    fun `late review completion cannot attach a result to a changed course`() = runTest(dispatcher) {
        val f = Fixture()
        val old = CompletableDeferred<Response<MistakeReviewCompleteResponse>>()
        f.api.reviewCompleteReply = { old.await() }
        f.vm.startMistakeReview(); runCurrent()
        f.vm.answerReview(0); runCurrent(); f.vm.advanceReview(); runCurrent()
        f.vm.onCourseChanged("nhsk1")
        old.complete(Response.success(MistakeReviewCompleteResponse(ok = true, percent = 100))); runCurrent()
        assertNull(f.vm.state.value.reviewResult)
        assertFalse(f.vm.state.value.isCompleting)
    }

    @Test
    fun `late mistakes page cannot replace the new list or unlock its in-flight guard`() = runTest(dispatcher) {
        val f = Fixture()
        val old = CompletableDeferred<Response<MistakesOverviewResponse>>()
        val fresh = CompletableDeferred<Response<MistakesOverviewResponse>>()
        f.api.mistakesReply = { if (f.api.mistakesCalls == 1) old.await() else fresh.await() }
        f.vm.ensureMistakesLoaded(); runCurrent()
        f.vm.onCourseChanged("nhsk1"); runCurrent()
        old.complete(Response.success(MistakesOverviewResponse(ok = true,
            targets = listOf(MistakeTargetDto(id = 1, level = "hsk1"))))); runCurrent()
        f.vm.ensureMistakesLoaded(); runCurrent()
        assertEquals(2, f.api.mistakesCalls)
        assertTrue(f.vm.state.value.isLoadingMistakes)
        assertNull(f.vm.state.value.mistakes)
        fresh.complete(Response.success(MistakesOverviewResponse(ok = true,
            targets = listOf(MistakeTargetDto(id = 2, level = "nhsk1"))))); runCurrent()
        assertEquals(listOf(2), f.vm.state.value.mistakes!!.targets.map { it.id })
        assertFalse(f.vm.state.value.isLoadingMistakes)
    }

    @Test
    fun `old review audio is stopped and cannot play after course change`() = runTest(dispatcher) {
        val f = Fixture()
        val old = CompletableDeferred<Response<ResponseBody>>()
        f.ttsReply = { old.await() }
        f.vm.playReviewAudio("你好"); runCurrent()
        assertTrue(f.vm.state.value.isReviewAudioLoading)
        f.vm.onCourseChanged("nhsk1")
        old.complete(Response.success("old-audio".toResponseBody())); runCurrent()
        assertEquals(0, f.audio.played)
        assertTrue(f.audio.releases > 0)
        assertFalse(f.vm.state.value.isReviewAudioLoading)
        assertNull(f.vm.state.value.reviewAudioError)
    }
}
