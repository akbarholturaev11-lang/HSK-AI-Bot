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
    fun `country selection leads directly to payment in every region`() {
        val direct = listOf(CheckoutStep.PLANS, CheckoutStep.PAY)
        listOf("tj", "uz", "ru", "cn", "other").forEach { region ->
            assertEquals(direct, checkoutFlow(region))
        }
    }

    @Test
    fun `each card country determines its displayed currency without a second picker`() {
        assertEquals("TJS", currencyForRegion("tj"))
        assertEquals("UZS", currencyForRegion("uz"))
        assertEquals("RUB", currencyForRegion("ru"))
        assertEquals("CNY", currencyForRegion("cn"))
        assertEquals("USD", currencyForRegion("other"))
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
    fun `centered payment picker offers only priced methods for the selected plan`() {
        val cardPrices = mapOf("1_month" to card.getValue("1_month"))
        val walletPrices = mapOf("1_month" to yuan.getValue("1_month"))
        val methods = mapOf(
            "visa" to cardPrices,
            "alipay" to walletPrices,
            "wechat" to mapOf("10_days" to yuan.getValue("1_month")),
        )
        assertEquals(listOf("dc_city", "alif"), availablePaymentOptions("tj", "1_month", methods))
        assertEquals(listOf("alipay"), availablePaymentOptions("cn", "1_month", methods))
        assertEquals(listOf("wechat"), availablePaymentOptions("cn", "10_days", methods))
        assertEquals(emptyList<String>(), availablePaymentOptions("ru", "1_month", methods))
        assertEquals(emptyList<String>(), availablePaymentOptions("cn", "3_months", methods))
    }

    @Test
    fun `card bank is only sent for card payments`() {
        assertEquals("alif", SubscriptionCheckoutState(method = "visa", country = "uz").cardBank)
        assertEquals("dc_city", SubscriptionCheckoutState(method = "visa", country = "tj").cardBank)
        assertEquals(null, SubscriptionCheckoutState(method = "alipay", country = "tj").cardBank)
    }
}
