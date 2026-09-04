package com.pomp.hskai.feature.limit

import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.AndroidAdAttemptRequest
import com.pomp.hskai.data.api.AndroidAdAttemptResponse
import com.pomp.hskai.data.api.AndroidAdListResponse
import com.pomp.hskai.data.api.AndroidAdViewRequest
import com.pomp.hskai.data.api.AndroidAdViewResponse
import com.pomp.hskai.data.api.AndroidFeatureApi
import com.pomp.hskai.data.api.AndroidProfileResponse
import com.pomp.hskai.data.api.AndroidSubscriptionOpenResponse
import com.pomp.hskai.data.api.AndroidSubscriptionOverviewResponse
import com.pomp.hskai.data.api.ExamCompleteRequest
import com.pomp.hskai.data.api.ExamCompleteResponse
import com.pomp.hskai.data.api.ExamStartRequest
import com.pomp.hskai.data.api.ExamStartResponse
import com.pomp.hskai.data.api.MistakeReviewAnswerRequest
import com.pomp.hskai.data.api.MistakeReviewAnswerResponse
import com.pomp.hskai.data.api.MistakeReviewCompleteRequest
import com.pomp.hskai.data.api.MistakeReviewCompleteResponse
import com.pomp.hskai.data.api.MistakeReviewStartRequest
import com.pomp.hskai.data.api.MistakeReviewStartResponse
import com.pomp.hskai.data.api.MistakesOverviewResponse
import com.pomp.hskai.data.api.PracticeCompleteRequest
import com.pomp.hskai.data.api.PracticeCompleteResponse
import com.pomp.hskai.data.api.PracticeStartRequest
import com.pomp.hskai.data.api.PracticeStartResponse
import com.pomp.hskai.data.api.RatingResponse
import com.pomp.hskai.data.api.ReferralOverviewResponse
import com.pomp.hskai.data.api.VoiceEndRequest
import com.pomp.hskai.data.api.VoiceEndResponse
import com.pomp.hskai.data.api.VoiceMessageRequest
import com.pomp.hskai.data.api.VoiceMessageResponse
import com.pomp.hskai.data.api.VoiceStartRequest
import com.pomp.hskai.data.api.VoiceStartResponse
import com.pomp.hskai.data.api.VoiceStatusResponse
import com.pomp.hskai.data.repository.FeatureRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
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

@OptIn(ExperimentalCoroutinesApi::class)
class SubscriptionHandoffViewModelTest {

    private val dispatcher = StandardTestDispatcher()

    @Before
    fun setUp() {
        Dispatchers.setMain(dispatcher)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    private fun viewModel(api: FakeFeatureApi) = SubscriptionHandoffViewModel(
        FeatureRepository(
            api = api,
            accessToken = { ApiResult.Success("token") },
        )
    )

    @Test
    fun `a successful handoff asks for the bot link and waits for the return`() = runTest {
        val api = FakeFeatureApi(
            Response.success(
                AndroidSubscriptionOpenResponse(
                    ok = true,
                    botUrl = "https://t.me/pomp_test_bot",
                    messageSent = true,
                )
            )
        )
        val model = viewModel(api)

        model.openSubscription()
        advanceUntilIdle()

        assertEquals(1, api.subscriptionOpenCalls)
        val handoff = model.handoff.value
        assertNotNull(handoff)
        assertEquals("https://t.me/pomp_test_bot", handoff!!.url)
        assertFalse(model.state.value.isOpening)
        assertNull(model.state.value.error)
        // Entitlement is only re-read after the learner comes back.
        assertTrue(model.state.value.awaitingReturn)
    }

    @Test
    fun `a second tap while opening does not fire a second request`() = runTest {
        val api = FakeFeatureApi(
            Response.success(
                AndroidSubscriptionOpenResponse(ok = true, botUrl = "https://t.me/pomp_test_bot")
            )
        )
        val model = viewModel(api)

        model.openSubscription()
        model.openSubscription()
        advanceUntilIdle()

        assertEquals(1, api.subscriptionOpenCalls)
    }

    @Test
    fun `a blank link is reported instead of launching nothing`() = runTest {
        val api = FakeFeatureApi(
            Response.success(AndroidSubscriptionOpenResponse(ok = true, botUrl = ""))
        )
        val model = viewModel(api)

        model.openSubscription()
        advanceUntilIdle()

        assertNull(model.handoff.value)
        assertNotNull(model.state.value.error)
        assertFalse(model.state.value.awaitingReturn)
    }

    @Test
    fun `a server failure surfaces an error and no handoff`() = runTest {
        val api = FakeFeatureApi(
            Response.error(
                503,
                """{"ok":false,"error":"android_subscription_handoff_unavailable"}"""
                    .toResponseBody(),
            )
        )
        val model = viewModel(api)

        model.openSubscription()
        advanceUntilIdle()

        assertNull(model.handoff.value)
        assertNotNull(model.state.value.error)
        assertFalse(model.state.value.isOpening)
        assertFalse(model.state.value.awaitingReturn)
    }

    @Test
    fun `a launch that nothing could handle drops the pending return`() = runTest {
        val api = FakeFeatureApi(
            Response.success(
                AndroidSubscriptionOpenResponse(ok = true, botUrl = "https://t.me/pomp_test_bot")
            )
        )
        val model = viewModel(api)
        model.openSubscription()
        advanceUntilIdle()
        val handoff = model.handoff.value!!

        model.onHandoffDelivered(handoff.id, opened = false)

        assertNull(model.handoff.value)
        assertFalse(model.state.value.awaitingReturn)
        assertNotNull(model.state.value.error)
    }

    @Test
    fun `a delivered launch keeps waiting for the return without an error`() = runTest {
        val api = FakeFeatureApi(
            Response.success(
                AndroidSubscriptionOpenResponse(ok = true, botUrl = "https://t.me/pomp_test_bot")
            )
        )
        val model = viewModel(api)
        model.openSubscription()
        advanceUntilIdle()
        val handoff = model.handoff.value!!

        model.onHandoffDelivered(handoff.id, opened = true)

        assertNull(model.handoff.value)
        assertTrue(model.state.value.awaitingReturn)
        assertNull(model.state.value.error)

        model.onReturnHandled()
        assertFalse(model.state.value.awaitingReturn)
    }

    @Test
    fun `a stale delivery id cannot clear a newer request`() = runTest {
        val api = FakeFeatureApi(
            Response.success(
                AndroidSubscriptionOpenResponse(ok = true, botUrl = "https://t.me/pomp_test_bot")
            )
        )
        val model = viewModel(api)
        model.openSubscription()
        advanceUntilIdle()

        model.onHandoffDelivered("some-other-id", opened = false)

        assertNotNull(model.handoff.value)
        assertTrue(model.state.value.awaitingReturn)
        assertNull(model.state.value.error)
    }
}

/**
 * Only the subscription handoff is exercised here; every other route would be
 * a bug if this ViewModel touched it, so they fail loudly.
 */
private class FakeFeatureApi(
    private val openResponse: Response<AndroidSubscriptionOpenResponse>,
) : AndroidFeatureApi {

    var subscriptionOpenCalls = 0
        private set

    override suspend fun subscriptionOpen(
        authorization: String,
    ): Response<AndroidSubscriptionOpenResponse> {
        subscriptionOpenCalls += 1
        return openResponse
    }

    override suspend fun profile(authorization: String): Response<AndroidProfileResponse> =
        error("unexpected call")

    override suspend fun subscriptionOverview(
        authorization: String,
    ): Response<AndroidSubscriptionOverviewResponse> = error("unexpected call")

    override suspend fun practiceStart(
        authorization: String,
        body: PracticeStartRequest,
    ): Response<PracticeStartResponse> = error("unexpected call")

    override suspend fun examStart(
        authorization: String,
        body: ExamStartRequest,
    ): Response<ExamStartResponse> = error("unexpected call")

    override suspend fun examComplete(
        authorization: String,
        body: ExamCompleteRequest,
    ): Response<ExamCompleteResponse> = error("unexpected call")

    override suspend fun practiceComplete(
        authorization: String,
        body: PracticeCompleteRequest,
    ): Response<PracticeCompleteResponse> = error("unexpected call")

    override suspend fun mistakes(
        authorization: String,
        category: String?,
        limit: Int,
        offset: Int,
    ): Response<MistakesOverviewResponse> = error("unexpected call")

    override suspend fun mistakeReviewStart(
        authorization: String,
        body: MistakeReviewStartRequest,
    ): Response<MistakeReviewStartResponse> = error("unexpected call")

    override suspend fun mistakeReviewAnswer(
        authorization: String,
        body: MistakeReviewAnswerRequest,
    ): Response<MistakeReviewAnswerResponse> = error("unexpected call")

    override suspend fun mistakeReviewComplete(
        authorization: String,
        body: MistakeReviewCompleteRequest,
    ): Response<MistakeReviewCompleteResponse> = error("unexpected call")

    override suspend fun rating(
        authorization: String,
        timezoneOffsetMinutes: Int,
    ): Response<RatingResponse> = error("unexpected call")

    override suspend fun referral(
        authorization: String,
        timezoneOffsetMinutes: Int,
    ): Response<ReferralOverviewResponse> = error("unexpected call")

    override suspend fun voiceStatus(authorization: String): Response<VoiceStatusResponse> =
        error("unexpected call")

    override suspend fun voiceStart(
        authorization: String,
        body: VoiceStartRequest,
    ): Response<VoiceStartResponse> = error("unexpected call")

    override suspend fun voiceMessage(
        authorization: String,
        body: VoiceMessageRequest,
    ): Response<VoiceMessageResponse> = error("unexpected call")

    override suspend fun voiceEnd(
        authorization: String,
        body: VoiceEndRequest,
    ): Response<VoiceEndResponse> = error("unexpected call")

    override suspend fun ads(
        authorization: String,
        slot: String,
        channel: String,
    ): Response<AndroidAdListResponse> = error("unexpected call")

    override suspend fun adAttempt(
        authorization: String,
        body: AndroidAdAttemptRequest,
    ): Response<AndroidAdAttemptResponse> = error("unexpected call")

    override suspend fun adView(
        authorization: String,
        body: AndroidAdViewRequest,
    ): Response<AndroidAdViewResponse> = error("unexpected call")
}
