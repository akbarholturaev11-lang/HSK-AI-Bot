package com.pomp.hskai.feature.subscription

import com.pomp.hskai.data.api.SubscriptionCheckoutOverviewDto
import java.math.BigDecimal
import java.math.RoundingMode
import java.util.Locale
import java.util.TimeZone

/** Device hints only, not IP/VPN location or proof of the country of a card. */
internal fun inferCheckoutRegion(zone: String, locale: String, language: String): String {
    val zoneRegion = when {
        zone == "Asia/Dushanbe" -> "tj"
        zone in setOf("Asia/Tashkent", "Asia/Samarkand") -> "uz"
        zone in setOf("Asia/Shanghai", "Asia/Urumqi", "Asia/Chongqing", "Asia/Harbin", "Asia/Kashgar", "PRC") -> "cn"
        zone in setOf("Europe/Moscow", "Europe/Kaliningrad", "Europe/Samara", "Europe/Volgograd",
            "Europe/Kirov", "Europe/Astrakhan", "Europe/Saratov", "Europe/Ulyanovsk", "Asia/Yekaterinburg",
            "Asia/Omsk", "Asia/Novosibirsk", "Asia/Barnaul", "Asia/Tomsk", "Asia/Novokuznetsk", "Asia/Krasnoyarsk",
            "Asia/Irkutsk", "Asia/Chita", "Asia/Yakutsk", "Asia/Khandyga", "Asia/Vladivostok", "Asia/Ust-Nera",
            "Asia/Magadan", "Asia/Sakhalin", "Asia/Srednekolymsk", "Asia/Kamchatka", "Asia/Anadyr", "W-SU") -> "ru"
        "/" in zone && !zone.startsWith("Etc/") -> "other"
        else -> ""
    }
    val country = Locale.forLanguageTag(locale).country.lowercase(Locale.ROOT)
    val localeRegion = if (country.isBlank()) "" else if (country in listOf("tj", "uz", "ru", "cn")) country else "other"
    if (zoneRegion.isNotEmpty() && localeRegion.isNotEmpty() && zoneRegion != localeRegion) return "other"
    return zoneRegion.ifBlank { localeRegion.ifBlank {
        when (language.lowercase(Locale.ROOT)) { "tg", "tj" -> "tj"; "ru" -> "ru"; "uz" -> "uz"; else -> "other" }
    } }
}

internal fun localCheckoutRegion(language: String): String =
    inferCheckoutRegion(TimeZone.getDefault().id, Locale.getDefault().toLanguageTag(), language)

private fun String.positiveMoney(): Boolean =
    replace(Regex("[\\s\\u00a0\\u202f]"), "").replace(',', '.').toBigDecimalOrNull()?.signum() == 1

internal fun regionalManualRegions(data: SubscriptionCheckoutOverviewDto): List<String> {
    if (data.mode != "subscription") return availableRegions(data.prices)
    return availableRegions(data.prices).filter { region ->
        if (region == "tj" || region == "cn") true
        else data.prices["visa"].orEmpty().keys.isNotEmpty() &&
            data.prices["visa"].orEmpty().keys.all { plan ->
                data.cardPrices[region]?.get(plan)?.let { it.currency.isNotBlank() && it.finalAmount.positiveMoney() } == true
            }
    }
}

internal fun SubscriptionCheckoutState.regionalPriceReady(): Boolean {
    val data = overview ?: return false
    if (data.mode != "subscription") return data.preferredCurrency == currencyForRegion(region)
    if (method == "visa" && region != "tj") return data.cardPrices[region]?.get(plan)?.let {
        it.currency.isNotBlank() && it.finalAmount.positiveMoney()
    } == true
    return data.prices[method]?.get(plan)?.let { it.finalAmount > 0 && it.currency.isNotBlank() } == true
}

/** Comparison display only. Never used in quote, receipt, invoice or entitlement requests. */
internal fun comparisonPrice(amount: String): String? {
    val n = amount.replace(Regex("[\\s\\u00a0\\u202f]"), "").replace(',', '.').toBigDecimalOrNull() ?: return null
    if (n.signum() <= 0) return null
    val ending = BigDecimal("0.99")
    var result = n.multiply(BigDecimal("1.3")).subtract(ending).setScale(0, RoundingMode.HALF_UP).add(ending)
    if (result <= n) result = n.subtract(ending).add(BigDecimal("0.000000001")).setScale(0, RoundingMode.CEILING).add(ending)
    return result.setScale(2).toPlainString()
}

internal fun LavaBlock.providerCurrencies(): List<String> =
    listOf("USD", "RUB").filter { providerPlans(it).isNotEmpty() }

internal fun LavaBlock.providerPlans(currency: String): List<LavaPlan> {
    val rows = plans_by_currency[currency] ?: plans.filter { it.currency == currency }
    return rows.filter { it.currency == currency && it.amount?.positiveMoney() == true }
}

internal fun LavaBlock.currencyFor(region: String): String {
    val currencies = providerCurrencies()
    val wanted = if (region == "ru") "RUB" else "USD"
    return wanted.takeIf { it in currencies } ?: currency.takeIf { it in currencies } ?: currencies.firstOrNull().orEmpty()
}

internal fun NativeLavaState.hasManualPending(): Boolean =
    !loading && !busy && !error && mode == "subscription" && checkoutId == 0 &&
        !uncertainStart && block?.pending_checkout_id == null && block?.blocked_reason == "payment_pending"

internal fun LavaBlock.prefersManual(region: String): Boolean =
    mode == "both" && (region in listOf("tj", "cn") ||
        (if (region == "ru") "RUB" else "USD") !in providerCurrencies())
