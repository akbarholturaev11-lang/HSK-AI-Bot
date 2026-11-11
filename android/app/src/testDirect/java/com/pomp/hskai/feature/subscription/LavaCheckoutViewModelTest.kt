package com.pomp.hskai.feature.subscription

import com.pomp.hskai.core.network.ApiResult
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.*
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.*
import org.junit.Assert.*
import retrofit2.Response

@OptIn(ExperimentalCoroutinesApi::class)
class LavaCheckoutViewModelTest {
    private val dispatcher = StandardTestDispatcher()
    @Before fun setup() = Dispatchers.setMain(dispatcher)
    @After fun teardown() = Dispatchers.resetMain()
    private class Fake : AndroidLavaApi {
        val plans = listOf(LavaPlan("1_month", 1, 30, "10.00", "USD"), LavaPlan("12_months", 12, 365, "90.00", "USD"))
        var overview = LavaOverview(true, LavaBlock(mode = "both", plans = plans))
        var startReply = CompletableDeferred<Response<LavaReply>>()
        var statusReply = LavaReply(ok = true, checkout_id = 7, status = "pending")
        var offer = ExitReply(true, true, false, 20, "2026-11-12T00:00:00Z")
        var starts = 0
        var checks = 0
        var claims = 0
        override suspend fun providerOverview(auth: String, body: LavaContext) = Response.success(overview)
        override suspend fun start(auth: String, body: LavaStart): Response<LavaReply> { starts++; return startReply.await() }
        override suspend fun status(auth: String, body: LavaId): Response<LavaReply> { checks++; return Response.success(statusReply) }
        override suspend fun cancel(auth: String, body: Map<String, String>) = Response.success(LavaReply(ok = true))
        override suspend fun exitOffer(auth: String, body: ExitAction): Response<ExitReply> {
            if (body.action == "claim") claims++
            return Response.success(offer)
        }
        fun model() = LavaCheckoutViewModel(LavaCheckoutRepository(this, { ApiResult.Success("token") }), "tj")
    }
    @Test fun duplicateStartAndBrowserReturnNeverGrantAccess() = runTest(dispatcher) {
        val fake = Fake(); val vm = fake.model(); runCurrent()
        vm.email("a@b.co"); vm.start(); vm.start(); runCurrent()
        assertEquals(1, fake.starts)
        fake.startReply.complete(Response.success(LavaReply(true, 7, "https://pay.lava.top/verified")))
        runCurrent()
        assertEquals("pending", vm.state.value.status)
        vm.urlOpened(true); vm.refresh(); runCurrent()
        assertEquals("pending", vm.state.value.status)
        fake.statusReply = LavaReply(ok = true, checkout_id = 7, status = "paid")
        vm.refresh(); runCurrent()
        assertEquals("paid", vm.state.value.status)
        vm.start(); runCurrent(); assertEquals(1, fake.starts)
    }
    @Test fun lostStartReplyRequiresCanonicalPendingReadBeforeAnotherStart() = runTest(dispatcher) {
        val fake = Fake(); val vm = fake.model(); runCurrent()
        vm.email("a@b.co"); vm.start(); runCurrent()
        fake.startReply.complete(Response.error(503, "{}".toResponseBody())); runCurrent()
        assertTrue(vm.state.value.uncertainStart)
        vm.start(); runCurrent(); assertEquals(1, fake.starts)
        fake.overview = fake.overview.copy(lava = fake.overview.lava!!.copy(pending_checkout_id = 9))
        vm.load(); runCurrent()
        assertEquals(9, vm.state.value.checkoutId)
        vm.start(); runCurrent(); assertEquals(1, fake.starts)
    }
    @Test fun serverBlockedAndUnpricedPlansCannotStart() = runTest(dispatcher) {
        val fake = Fake()
        fake.overview = fake.overview.copy(lava = LavaBlock(mode = "lava_only", plans = listOf(LavaPlan("12_months",12)), blocked_reason = "checkout_needs_review"))
        val vm = fake.model(); runCurrent(); vm.email("a@b.co"); vm.chooseProviderPlan("1_month"); vm.start(); runCurrent()
        assertEquals(0, fake.starts)
        assertEquals("", vm.state.value.plan)
    }
    @Test fun unacceptedClaimCannotChangeCheckoutMode() = runTest(dispatcher) {
        val fake = Fake(); val vm = fake.model(); runCurrent()
        vm.requestProviderClose(); runCurrent(); assertNotNull(vm.state.value.offer)
        vm.claim(); runCurrent()
        assertEquals("subscription", vm.state.value.mode)
        assertTrue(vm.state.value.error)
        fake.offer = fake.offer.copy(accepted = true)
        vm.claim(); runCurrent()
        assertEquals("exit_discount", vm.state.value.mode)
        assertNull(vm.state.value.offer)
    }
    @Test fun missingPromoClosesWithoutInventedOffer() = runTest(dispatcher) {
        val fake = Fake(); fake.offer = ExitReply(ok = true)
        val vm = fake.model(); runCurrent(); vm.requestProviderClose(); runCurrent()
        assertTrue(vm.state.value.closeRequested)
        assertNull(vm.state.value.offer)
    }
    @Test fun providerUrlsAreHttpsAndExactHostOnly() {
        assertNotNull(safeLavaPaymentUrl("https://pay.lava.top/123"))
        listOf("http://pay.lava.top/a", "https://pay.lava.top.evil.example/a", "https://evil@pay.lava.top/a",
            "https://pay.lava.top:8443/a", "javascript:alert(1)", "https://example.com").forEach { assertNull(it, safeLavaPaymentUrl(it)) }
    }
}
