package com.pomp.hskai.feature.subscription

import com.pomp.hskai.R
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.AndroidFeatureApi
import com.pomp.hskai.data.api.AndroidSubscriptionCurrencyPreferenceRequest
import com.pomp.hskai.data.api.AndroidSubscriptionCurrencyPreferenceResponse
import com.pomp.hskai.data.api.SubscriptionCheckoutOverviewDto
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
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import retrofit2.Response

@OptIn(ExperimentalCoroutinesApi::class)
class SubscriptionCheckoutCurrencyTest {
    private val dispatcher = StandardTestDispatcher()
    private val origins = mutableListOf<String>()
    private val overviews = ArrayDeque<Response<SubscriptionCheckoutOverviewDto>>()
    private val subscriptionPrices = prices("1_month", "RUB")

    @Before
    fun setUp() = Dispatchers.setMain(dispatcher)

    @After
    fun tearDown() = Dispatchers.resetMain()

    private fun prices(plan: String, currency: String) = mapOf(
        "visa" to mapOf(plan to SubscriptionPriceDto(baseAmount = 89, finalAmount = 89, currency = currency)),
    )

    private fun overview(mode: String, currency: String) = SubscriptionCheckoutOverviewDto(
        ok = true,
        mode = mode,
        checkoutAllowed = true,
        preferredCurrency = currency,
        displayCurrency = currency,
        prices = prices(if (mode == "hsk30_unlock") mode else "1_month", currency),
    )

    private fun model(origin: String): SubscriptionCheckoutViewModel {
        // Only these two endpoints are allowed: no quote, payment or subscription activation.
        val api = Proxy.newProxyInstance(
            AndroidFeatureApi::class.java.classLoader,
            arrayOf(AndroidFeatureApi::class.java),
        ) { _, method, args ->
            when (method.name) {
                "checkoutOverview" -> {
                    origins += args[1] as String
                    overviews.removeFirst()
                }
                "updateSubscriptionCurrencyPreference" -> {
                    assertEquals("RUB", (args[1] as AndroidSubscriptionCurrencyPreferenceRequest).currency)
                    Response.success(AndroidSubscriptionCurrencyPreferenceResponse(
                        ok = true, currency = "RUB", displayCurrency = "RUB", prices = subscriptionPrices,
                    ))
                }
                else -> error("Unexpected endpoint: ${method.name}")
            }
        } as AndroidFeatureApi
        return SubscriptionCheckoutViewModel(FeatureRepository(api, { ApiResult.Success("token") }), origin)
    }

    @Test
    fun `currency change keeps the permanent unlock product and original checkout origin`() = runTest(dispatcher) {
        overviews.add(Response.success(overview("hsk30_unlock", "TJS")))
        overviews.add(Response.success(overview("hsk30_unlock", "RUB")))
        val model = model("hsk30_unlock")
        model.load()
        advanceUntilIdle()
        model.openCurrencySelector()
        model.chooseCurrency("RUB")
        advanceUntilIdle()

        assertEquals(listOf("hsk30_unlock", "hsk30_unlock"), origins)
        assertTrue(model.state.value.isHsk30Unlock)
        assertEquals("hsk30_unlock", model.state.value.plan)
        assertEquals(setOf("hsk30_unlock"), model.state.value.overview!!.prices["visa"]!!.keys)
        assertEquals("RUB", model.state.value.overview!!.displayCurrency)
        assertFalse(model.state.value.currencySaving)
        assertFalse(model.state.value.currencyDialogOpen)
    }

    @Test
    fun `failed product refresh keeps previous prices and allows retry`() = runTest(dispatcher) {
        val original = overview("hsk30_unlock", "TJS")
        overviews.add(Response.success(original))
        overviews.add(Response.error(503, "unavailable".toResponseBody()))
        val model = model("hsk30_unlock")
        model.load()
        advanceUntilIdle()
        model.openCurrencySelector()
        model.chooseCurrency("RUB")
        advanceUntilIdle()

        assertEquals(original, model.state.value.overview)
        assertEquals(R.string.sub_currency_refresh_failed, model.state.value.currencyErrorRes)
        assertFalse(model.state.value.currencySaving)
        assertTrue(model.state.value.currencyDialogOpen)
    }

    @Test
    fun `ordinary subscription uses returned prices without an extra overview request`() = runTest(dispatcher) {
        overviews.add(Response.success(overview("subscription", "TJS")))
        val model = model("profile")
        model.load()
        advanceUntilIdle()
        model.chooseCurrency("RUB")
        advanceUntilIdle()

        assertEquals(listOf("profile"), origins)
        assertFalse(model.state.value.isHsk30Unlock)
        assertEquals(subscriptionPrices, model.state.value.overview!!.prices)
        assertEquals("RUB", model.state.value.overview!!.preferredCurrency)
        assertFalse(model.state.value.currencySaving)
    }
}
