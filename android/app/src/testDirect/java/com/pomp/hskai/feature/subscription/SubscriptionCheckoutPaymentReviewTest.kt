package com.pomp.hskai.feature.subscription

import com.pomp.hskai.R
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.AndroidFeatureApi
import com.pomp.hskai.data.api.PaymentDecisionStatusResponse
import com.pomp.hskai.data.api.SubscriptionCheckoutOverviewDto
import com.pomp.hskai.data.api.SubscriptionPendingDto
import com.pomp.hskai.data.api.SubscriptionPriceDto
import com.pomp.hskai.data.repository.FeatureRepository
import java.lang.reflect.Proxy
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import retrofit2.Response

@OptIn(ExperimentalCoroutinesApi::class)
class SubscriptionCheckoutPaymentReviewTest {
    private val dispatcher = StandardTestDispatcher()
    private val overviews = ArrayDeque<SubscriptionCheckoutOverviewDto>()
    private val decisions = ArrayDeque<PaymentDecisionStatusResponse>()
    private var statusCalls = 0

    @Before
    fun setUp() = Dispatchers.setMain(dispatcher)

    @After
    fun tearDown() = Dispatchers.resetMain()

    private fun pending(mode: String, plan: String, provisional: Boolean = false) =
        SubscriptionCheckoutOverviewDto(
            ok = true,
            mode = mode,
            pendingPayment = SubscriptionPendingDto(
                id = 71,
                planType = plan,
                provisionalAccess = provisional,
            ),
        )

    private fun model(): SubscriptionCheckoutViewModel {
        val api = Proxy.newProxyInstance(
            AndroidFeatureApi::class.java.classLoader,
            arrayOf(AndroidFeatureApi::class.java),
        ) { _, method, args ->
            when (method.name) {
                "checkoutOverview" -> {
                    assertEquals("hsk30_content", args[1])
                    Response.success(overviews.removeFirst())
                }
                "checkoutPaymentStatus" -> {
                    statusCalls++
                    assertEquals(71, args[1])
                    Response.success(decisions.removeFirst())
                }
                else -> error("Unexpected endpoint: ${method.name}")
            }
        } as AndroidFeatureApi
        return SubscriptionCheckoutViewModel(
            FeatureRepository(api, { ApiResult.Success("test-token") }),
            "hsk30_content",
        )
    }

    @Test
    fun `ordinary pending payment in HSK checkout does not lock navigation or use HSK status check`() =
        runTest(dispatcher) {
            overviews.add(pending("hsk30_unlock", "1_month"))
            val model = model()
            model.load()
            advanceUntilIdle()

            assertFalse(model.state.value.isHsk30Unlock)
            assertFalse(model.state.value.isWaitingForHsk30Review)
            model.refreshPaymentStatus()
            advanceUntilIdle()
            assertEquals(0, statusCalls)
            assertEquals(null, model.state.value.errorRes)
        }

    @Test
    fun `existing provisional HSK payment keeps its course return action from ordinary checkout`() =
        runTest(dispatcher) {
            overviews.add(pending("subscription", "hsk30_unlock", provisional = true))
            val model = model()
            model.load()
            advanceUntilIdle()

            assertTrue(model.state.value.isHsk30Unlock)
            assertTrue(model.state.value.provisionalAccess)
            assertFalse(model.state.value.isWaitingForHsk30Review)
        }

    @Test
    fun `rejected HSK payment releases review lock and retry reloads the unlock offer`() =
        runTest(dispatcher) {
            overviews.add(pending("hsk30_unlock", "hsk30_unlock"))
            decisions.add(PaymentDecisionStatusResponse(
                ok = true, paymentId = 71, status = "rejected", planType = "hsk30_unlock",
            ))
            val model = model()
            model.load()
            advanceUntilIdle()
            assertTrue(model.state.value.isWaitingForHsk30Review)

            model.refreshPaymentStatus()
            advanceUntilIdle()
            assertEquals("rejected", model.state.value.paymentDecision)
            assertFalse(model.state.value.isWaitingForHsk30Review)
            assertEquals(null, model.state.value.errorRes)

            overviews.add(SubscriptionCheckoutOverviewDto(
                ok = true,
                mode = "hsk30_unlock",
                checkoutAllowed = true,
                preferredCurrency = "TJS",
                prices = mapOf("visa" to mapOf("hsk30_unlock" to SubscriptionPriceDto(
                    baseAmount = 10, finalAmount = 10, currency = "TJS",
                ))),
            ))
            model.retryAfterRejection()
            advanceUntilIdle()
            assertEquals("hsk30_unlock", model.state.value.plan)
            assertEquals(0, model.state.value.pendingPaymentId)
            assertEquals("", model.state.value.paymentDecision)
            assertFalse(model.state.value.isWaitingForHsk30Review)
            assertEquals(CheckoutStep.PLANS, model.state.value.step)
        }

    @Test
    fun `approved HSK payment opened from profile releases the review lock`() = runTest(dispatcher) {
        overviews.add(pending("subscription", "hsk30_unlock"))
        decisions.add(PaymentDecisionStatusResponse(
            ok = true, paymentId = 71, status = "approved", planType = "hsk30_unlock",
        ))
        val model = model()
        model.load()
        advanceUntilIdle()
        assertTrue(model.state.value.isWaitingForHsk30Review)

        model.refreshPaymentStatus()
        advanceUntilIdle()
        assertEquals("approved", model.state.value.paymentDecision)
        assertFalse(model.state.value.isWaitingForHsk30Review)
        assertEquals(null, model.state.value.errorRes)
    }

    @Test
    fun `status for another product cannot approve HSK access`() = runTest(dispatcher) {
        overviews.add(pending("hsk30_unlock", "hsk30_unlock"))
        decisions.add(PaymentDecisionStatusResponse(
            ok = true, paymentId = 71, status = "approved", planType = "1_month",
        ))
        val model = model()
        model.load()
        advanceUntilIdle()
        model.refreshPaymentStatus()
        advanceUntilIdle()

        assertEquals("", model.state.value.paymentDecision)
        assertEquals(R.string.sub_status_check_failed, model.state.value.errorRes)
        assertTrue(model.state.value.isWaitingForHsk30Review)
    }
}
