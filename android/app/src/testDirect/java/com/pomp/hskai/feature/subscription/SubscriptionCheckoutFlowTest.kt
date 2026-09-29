package com.pomp.hskai.feature.subscription

import com.pomp.hskai.data.api.SubscriptionPriceDto
import org.junit.Assert.assertEquals
import org.junit.Test

class SubscriptionCheckoutFlowTest {

    private val card = mapOf("1_month" to SubscriptionPriceDto(baseAmount = 89, finalAmount = 89, currency = "TJS"))
    private val yuan = mapOf("1_month" to SubscriptionPriceDto(baseAmount = 66, finalAmount = 66, currency = "¥"))

    @Test
    fun `regions follow the priced methods`() {
        assertEquals(listOf("tj", "uz", "ru", "cn", "other"),
            availableRegions(mapOf("visa" to card, "alipay" to yuan)))
        // A card-only campaign has no China; a wallet-only one has only China.
        assertEquals(listOf("tj", "uz", "ru", "other"), availableRegions(mapOf("visa" to card, "alipay" to emptyMap())))
        assertEquals(listOf("cn"), availableRegions(mapOf("wechat" to yuan)))
    }

    @Test
    fun `only Tajikistan and China ask for a payment type`() {
        val withMethod = listOf(CheckoutStep.REGION, CheckoutStep.PLANS, CheckoutStep.METHOD, CheckoutStep.PAY)
        val direct = listOf(CheckoutStep.REGION, CheckoutStep.PLANS, CheckoutStep.PAY)
        assertEquals(withMethod, checkoutFlow("tj"))
        assertEquals(withMethod, checkoutFlow("cn"))
        assertEquals(direct, checkoutFlow("ru"))
        assertEquals(direct, checkoutFlow("uz"))
        assertEquals(direct, checkoutFlow("other"))
    }

    @Test
    fun `cards outside Tajikistan always pay to Alif`() {
        assertEquals("dc_city", cardBankFor("tj", "dc_city"))
        assertEquals("alif", cardBankFor("tj", "alif"))
        assertEquals("alif", cardBankFor("ru", "dc_city"))
        assertEquals("alif", cardBankFor("other", "dc_city"))
    }

    @Test
    fun `China keeps the chosen wallet and cards use visa`() {
        val prices = mapOf("visa" to card, "alipay" to yuan, "wechat" to yuan)
        assertEquals("wechat", methodFor("cn", "wechat", prices))
        assertEquals("alipay", methodFor("cn", "visa", prices))
        assertEquals("visa", methodFor("tj", "alipay", prices))
        assertEquals("wechat", methodFor("cn", "alipay", mapOf("wechat" to yuan)))
    }

    @Test
    fun `card bank is only sent for card payments`() {
        assertEquals("alif", SubscriptionCheckoutState(method = "visa", country = "uz").cardBank)
        assertEquals("dc_city", SubscriptionCheckoutState(method = "visa", country = "tj").cardBank)
        assertEquals(null, SubscriptionCheckoutState(method = "alipay", country = "tj").cardBank)
    }
}
