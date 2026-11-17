package com.pomp.hskai.feature.feedback

import com.pomp.hskai.core.network.ApiResult
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.*
import org.junit.*
import org.junit.Assert.*
import retrofit2.Response

@OptIn(ExperimentalCoroutinesApi::class)
class ActivityFeedbackViewModelTest {
    private val dispatcher = StandardTestDispatcher()
    @Before fun setup() = Dispatchers.setMain(dispatcher)
    @After fun teardown() = Dispatchers.resetMain()
    private val choices = FeedbackChoices(
        liked = listOf(FeedbackOption("practice","Practice"),FeedbackOption("other","Other")),
        liked_sub = mapOf("practice" to listOf(FeedbackOption("daily","Daily"))),
        disliked = listOf(FeedbackOption("limits","Limits"),FeedbackOption("unclear","Unclear")),
        disliked_detail_required = listOf("unclear"),
        paid = listOf(FeedbackOption("useful","Useful")),
        paid_sub_positive = listOf(FeedbackOption("lessons","Lessons"),FeedbackOption("other","Other")),
    )
    private class Fake(val prompt: ActivityFeedbackPrompt): AndroidActivityFeedbackApi {
        var requests = 0
        var body: Map<String,String>? = null
        val reply = CompletableDeferred<Response<FeedbackSubmitReply>>()
        override suspend fun prepareFeedback(auth: String, request: FeedbackPrepare): Response<FeedbackPrepareReply> {
            requests++; return Response.success(FeedbackPrepareReply(true,prompt))
        }
        override suspend fun submitFeedback(auth: String, request: Map<String,String>): Response<FeedbackSubmitReply> {
            body = request; return reply.await()
        }
    }
    @Test fun canonicalFreeFlowCollectsOneQuestionAtATimeAndOnlyServerCompletes() = runTest(dispatcher) {
        val api=Fake(ActivityFeedbackPrompt(5,choices=choices))
        val vm=ActivityFeedbackViewModel(ActivityFeedbackRepository(api,{ ApiResult.Success("test") }))
        vm.prepare("practice","hsk1"); runCurrent()
        assertEquals("liked_code",vm.state.value.question?.key)
        vm.answer("practice"); assertEquals("liked_sub_code",vm.state.value.question?.key)
        vm.answer("daily"); assertEquals("disliked_code",vm.state.value.question?.key)
        vm.answer("limits"); runCurrent()
        assertFalse(vm.state.value.completed)
        assertTrue(vm.state.value.busy)
        assertEquals(mapOf("feedback_id" to "5","liked_code" to "practice","liked_sub_code" to "daily","disliked_code" to "limits"), api.body)
        vm.next(); api.reply.complete(Response.success(FeedbackSubmitReply(true,true))); runCurrent()
        assertTrue(vm.state.value.completed)
        vm.close(); vm.prepare("practice","hsk1"); runCurrent(); assertEquals(1,api.requests)
    }
    @Test fun requiredDetailsAndBackNeverCarryStaleDependentAnswers() = runTest(dispatcher) {
        val api=Fake(ActivityFeedbackPrompt(6,choices=choices))
        val vm=ActivityFeedbackViewModel(ActivityFeedbackRepository(api,{ ApiResult.Success("test") }))
        vm.prepare("lesson","hsk1",1); runCurrent()
        vm.answer("other"); assertEquals("liked_other_text",vm.state.value.question?.key)
        vm.next(); assertEquals(1,vm.state.value.step)
        vm.answer("Detail"); vm.next(); vm.answer("unclear")
        assertEquals("disliked_detail_text",vm.state.value.question?.key)
        vm.back(); vm.answer("limits"); runCurrent()
        assertEquals("Detail",api.body?.get("liked_other_text"))
        assertFalse(api.body!!.containsKey("disliked_detail_text"))
        api.reply.complete(Response.success(FeedbackSubmitReply(true,true))); runCurrent()
    }
    @Test fun paidQuestionsDoNotAskTheFreeQuestionnaire() {
        val prompt=ActivityFeedbackPrompt(7,paid=true,choices=choices)
        assertEquals(listOf("paid_code"),feedbackQuestions(prompt,emptyMap()).map { it.key })
        assertEquals(listOf("paid_code","paid_sub_code","paid_other_text"),
            feedbackQuestions(prompt,mapOf("paid_code" to "useful","paid_sub_code" to "other")).map { it.key })
    }
}
