package com.pomp.hskai.feature.subscription

import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.AndroidFeatureApi
import com.pomp.hskai.data.api.PaymentDecisionStatusResponse
import com.pomp.hskai.data.api.SubscriptionCheckoutOverviewDto
import com.pomp.hskai.data.api.SubscriptionPendingDto
import com.pomp.hskai.data.api.SubscriptionPriceDto
import com.pomp.hskai.data.repository.FeatureRepository
import java.lang.reflect.Proxy
import kotlin.coroutines.Continuation
import kotlin.coroutines.intrinsics.COROUTINE_SUSPENDED
import kotlin.coroutines.resume
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import retrofit2.Response

@OptIn(ExperimentalCoroutinesApi::class)
class SubscriptionCheckoutLifecycleTest {
    private val dispatcher = StandardTestDispatcher()
    private val reads = mutableListOf<Continuation<Any?>>()
    private val statuses = mutableListOf<Continuation<Any?>>()
    private val watched = mutableListOf<Int>()
    private var quoteCalls = 0

    @Before fun setUp() = Dispatchers.setMain(dispatcher)
    @After fun tearDown() = Dispatchers.resetMain()

    @Suppress("UNCHECKED_CAST")
    private fun model(): SubscriptionCheckoutViewModel {
        val api = Proxy.newProxyInstance(
            AndroidFeatureApi::class.java.classLoader, arrayOf(AndroidFeatureApi::class.java),
        ) { _, method, args ->
            when (method.name) {
                "checkoutOverview" -> {
                    reads += args.last() as Continuation<Any?>
                    COROUTINE_SUSPENDED
                }
                "checkoutPaymentStatus" -> {
                    statuses += args.last() as Continuation<Any?>
                    COROUTINE_SUSPENDED
                }
                "checkoutQuote" -> { quoteCalls++; error("Quote must require a fresh overview") }
                else -> error("Unexpected endpoint: ${method.name}")
            }
        } as AndroidFeatureApi
        return SubscriptionCheckoutViewModel(
            FeatureRepository(api, { ApiResult.Success("test-token") }), "hsk30_content",
            onPendingPayment = watched::add,
        )
    }

    private fun offer() = SubscriptionCheckoutOverviewDto(
        ok = true, mode = "hsk30_unlock", checkoutAllowed = true, preferredCurrency = "TJS",
        prices = mapOf("visa" to mapOf("hsk30_unlock" to SubscriptionPriceDto(
            baseAmount = 10, finalAmount = 10, currency = "TJS",
        ))),
    )

    @Test fun `older pending overview cannot replace a newer offer or start its monitor`() = runTest(dispatcher) {
        val model = model()
        model.load()
        runCurrent()
        model.load()
        runCurrent()
        reads[1].resume(Response.success(offer()))
        runCurrent()
        reads[0].resume(Response.success(offer().copy(
            checkoutAllowed = false,
            pendingPayment = SubscriptionPendingDto(id = 71, planType = "1_month"),
        )))
        advanceUntilIdle()

        assertTrue(model.state.value.isHsk30Unlock)
        assertEquals("hsk30_unlock", model.state.value.plan)
        assertEquals(0, model.state.value.pendingPaymentId)
        assertFalse(model.state.value.alreadyPending)
        assertTrue(watched.isEmpty())
    }

    @Test fun `failed reopen cannot reuse previous payment prices`() = runTest(dispatcher) {
        val model = model()
        model.load()
        runCurrent()
        reads[0].resume(Response.success(offer()))
        runCurrent()
        model.load()
        runCurrent()
        reads[1].resume(Response.error<SubscriptionCheckoutOverviewDto>(503, "".toResponseBody()))
        runCurrent()
        model.next()
        advanceUntilIdle()

        assertNull(model.state.value.overview)
        assertNull(model.state.value.quote)
        assertFalse(model.state.value.loading)
        assertEquals(0, quoteCalls)
    }

    @Test fun `status response from an earlier review cannot mark the new offer approved`() = runTest(dispatcher) {
        val model = model()
        model.load()
        runCurrent()
        reads[0].resume(Response.success(offer().copy(
            pendingPayment = SubscriptionPendingDto(id = 71, planType = "hsk30_unlock"),
        )))
        runCurrent()
        model.refreshPaymentStatus()
        runCurrent()
        model.load()
        runCurrent()
        reads[1].resume(Response.success(offer()))
        runCurrent()
        statuses[0].resume(Response.success(PaymentDecisionStatusResponse(
            ok = true, paymentId = 71, status = "approved", planType = "hsk30_unlock",
        )))
        advanceUntilIdle()

        assertEquals("", model.state.value.paymentDecision)
        assertEquals(0, model.state.value.pendingPaymentId)
        assertFalse(model.state.value.checkingPaymentStatus)
        assertEquals(CheckoutStep.PLANS, model.state.value.step)
    }
}
