package com.pomp.hskai.feature.subscription

import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.*
import com.pomp.hskai.data.repository.FeatureRepository
import java.lang.reflect.Proxy
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.*
import org.junit.Assert.*
import org.junit.Test
import retrofit2.Response

@OptIn(ExperimentalCoroutinesApi::class)
class SubscriptionCheckoutSequenceTest {
    @Test fun chinaWalletAndForeignCardUseTheExactPwaSequence() = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {
            for (region in listOf("cn", "other")) {
                val requests = mutableListOf<SubscriptionQuoteRequest>()
                val currency = if (region == "cn") "CNY" else "USD"
                val price = SubscriptionPriceDto(baseAmount = 10, finalAmount = 10, currency = currency)
                val api = Proxy.newProxyInstance(AndroidFeatureApi::class.java.classLoader,
                    arrayOf(AndroidFeatureApi::class.java)) { _, method, args ->
                    when (method.name) {
                        "checkoutOverview" -> Response.success(SubscriptionCheckoutOverviewDto(ok = true,
                            mode = "subscription", checkoutAllowed = true, language = "uz", preferredCurrency = currency,
                            prices = mapOf("visa" to mapOf("1_month" to price), "alipay" to mapOf("1_month" to price),
                                "wechat" to mapOf("1_month" to price)),
                            cardPrices = mapOf("other" to mapOf("1_month" to SubscriptionCardPriceDto(
                                finalAmount = "10", baseAmount = "10", currency = "USD")))))
                        "checkoutQuote" -> {
                            requests += args[1] as SubscriptionQuoteRequest
                            Response.success(SubscriptionQuoteResponse(ok = true, quote = SubscriptionQuoteDto(
                                payAmount = "10", payCurrency = currency, paymentDetails = "fixture",
                                qr = SubscriptionQrDto(available = true, imageDataUrl = "fixture"))))
                        }
                        "checkoutEvent" -> Response.success(SubscriptionCheckoutEventResponse(ok = true))
                        else -> error("Unexpected endpoint ${method.name}")
                    }
                } as AndroidFeatureApi
                val vm = SubscriptionCheckoutViewModel(FeatureRepository(api, { ApiResult.Success("fixture") }),
                    "course_limit", savedRegion = { region })
                vm.load(); advanceUntilIdle(); vm.next(); advanceUntilIdle()
                if (region == "cn") {
                    assertEquals(CheckoutStep.METHOD, vm.state.value.step)
                    assertTrue(requests.isEmpty())
                    vm.chooseMethod("wechat"); vm.next(); advanceUntilIdle()
                    assertEquals("wechat", requests.single().paymentMethod)
                    assertNull(requests.single().cardBank)
                } else {
                    assertEquals("visa", requests.single().paymentMethod)
                    assertEquals("other", requests.single().cardCountry)
                    assertEquals("alif", requests.single().cardBank)
                }
                assertEquals(CheckoutStep.PAY, vm.state.value.step)
            }
        } finally { Dispatchers.resetMain() }
    }

    @Test fun confirmedInlinePlanUsesPwaMethodStepWithoutARepeatedPlanChoice() = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {
            var quotes = 0
            val requests = mutableListOf<SubscriptionQuoteRequest>()
            val price = SubscriptionPriceDto(baseAmount = 89, finalAmount = 89, currency = "TJS")
            val api = Proxy.newProxyInstance(AndroidFeatureApi::class.java.classLoader,
                arrayOf(AndroidFeatureApi::class.java)) { _, method, args ->
                when (method.name) {
                    "checkoutOverview" -> Response.success(SubscriptionCheckoutOverviewDto(ok = true,
                        mode = "subscription", checkoutAllowed = true, language = "uz", preferredCurrency = "TJS",
                        prices = mapOf("visa" to mapOf("1_month" to price, "3_months" to price))))
                    "checkoutQuote" -> {
                        quotes++; requests += args[1] as SubscriptionQuoteRequest
                        Response.success(SubscriptionQuoteResponse(ok = true, quote = SubscriptionQuoteDto(
                            payAmount = "89", payCurrency = "TJS", paymentDetails = "fixture requisites")))
                    }
                    "checkoutEvent" -> Response.success(SubscriptionCheckoutEventResponse(ok = true))
                    else -> error("Unexpected endpoint ${method.name}")
                }
            } as AndroidFeatureApi
            val vm = SubscriptionCheckoutViewModel(FeatureRepository(api, { ApiResult.Success("fixture") }),
                "course_limit", savedRegion = { "tj" })
            vm.load(); advanceUntilIdle()
            vm.choosePlan("3_months"); vm.next(); advanceUntilIdle()
            assertEquals(CheckoutStep.METHOD, vm.state.value.step)
            assertEquals(0, quotes)
            vm.chooseBank("alif"); vm.next(); advanceUntilIdle()
            assertEquals(CheckoutStep.PAY, vm.state.value.step)
            assertEquals("3_months", requests.single().planType)
            assertEquals("alif", requests.single().cardBank)
            vm.back()
            assertEquals(CheckoutStep.METHOD, vm.state.value.step)
            vm.back()
            assertEquals(CheckoutStep.PLANS, vm.state.value.step)
            assertEquals("3_months", vm.state.value.plan)
        } finally { Dispatchers.resetMain() }
    }
}
