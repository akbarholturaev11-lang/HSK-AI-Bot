package com.pomp.hskai.feature.subscription

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.provider.OpenableColumns
import android.util.Base64
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.pomp.hskai.R
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.SubscriptionCheckoutEventRequest
import com.pomp.hskai.data.api.SubscriptionCheckoutOverviewDto
import com.pomp.hskai.data.api.SubscriptionDiscountDto
import com.pomp.hskai.data.api.SubscriptionPriceDto
import com.pomp.hskai.data.api.SubscriptionQuoteDto
import com.pomp.hskai.data.api.SubscriptionQuoteRequest
import com.pomp.hskai.data.api.SubscriptionSubmitRequest
import com.pomp.hskai.data.repository.FeatureRepository
import java.io.ByteArrayOutputStream
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** Region → plans → payment type (Tajikistan and China only) → payment, as in the Mini App. */
enum class CheckoutStep { REGION, PLANS, METHOD, PAY, DONE }

/** The card's country, or China for Alipay/WeChat — the Mini App's `REGION_ORDER`. */
internal val CHECKOUT_REGIONS = listOf("tj", "uz", "ru", "cn", "other")
internal val CHINA_METHODS = listOf("alipay", "wechat")

/** A Tajik card pays to one of two banks; the requisites are set per bank in the admin panel. */
internal val CARD_BANKS = listOf("dc_city", "alif")

internal fun regionMethods(region: String): List<String> =
    if (region == "cn") CHINA_METHODS else listOf("visa")

/** Regions that have at least one priced method in this overview (a campaign may cover only some). */
internal fun availableRegions(prices: Map<String, Map<String, SubscriptionPriceDto>>): List<String> =
    CHECKOUT_REGIONS.filter { region -> regionMethods(region).any { !prices[it].isNullOrEmpty() } }

/** Only Tajikistan (the bank) and China (the wallet) ask for a payment type. */
internal fun hasMethodStep(region: String): Boolean = region == "tj" || region == "cn"

internal fun checkoutFlow(region: String, includePlans: Boolean = true): List<CheckoutStep> {
    val flow = mutableListOf(CheckoutStep.REGION)
    if (includePlans) flow += CheckoutStep.PLANS
    if (hasMethodStep(region)) flow += CheckoutStep.METHOD
    flow += CheckoutStep.PAY
    return flow
}

/** A card from outside Tajikistan always pays to Alif (Visa); the server applies the same rule. */
internal fun cardBankFor(country: String, bank: String): String = if (country == "tj") bank else "alif"

/** The method the region pays with, keeping the current one when it still fits. */
internal fun methodFor(
    region: String,
    current: String,
    prices: Map<String, Map<String, SubscriptionPriceDto>>,
): String {
    val priced = { method: String -> !prices[method].isNullOrEmpty() }
    if (region.isEmpty()) {
        return current.takeIf(priced) ?: listOf("visa", "alipay", "wechat").firstOrNull(priced) ?: current
    }
    val options = regionMethods(region).filter(priced)
    return current.takeIf { it in options } ?: options.firstOrNull() ?: current
}

data class SubscriptionCheckoutState(
    val loading: Boolean = true,
    val quoting: Boolean = false,
    val submitting: Boolean = false,
    val discountStarting: Boolean = false,
    val overview: SubscriptionCheckoutOverviewDto? = null,
    val discount: SubscriptionDiscountDto? = null,
    val quote: SubscriptionQuoteDto? = null,
    val step: CheckoutStep = CheckoutStep.REGION,
    val region: String = "",
    val plan: String = "1_month",
    val method: String = "visa",
    val country: String = "tj",
    val bank: String = CARD_BANKS.first(),
    val language: String = "uz",
    val receiptName: String = "",
    val receiptBytes: Int = 0,
    val receiptNoteRes: Int? = null,
    val submitted: Boolean = false,
    val alreadyPending: Boolean = false,
    val errorRes: Int? = null,
) {
    val isHsk30Unlock: Boolean get() = overview?.mode == "hsk30_unlock"
    val flow: List<CheckoutStep> get() = checkoutFlow(region, includePlans = !isHsk30Unlock)

    /** `dc_city` or `alif` for a card payment, null for the QR wallets. */
    val cardBank: String? get() = if (method == "visa") cardBankFor(country, bank) else null
}

class SubscriptionCheckoutViewModel(
    private val repository: FeatureRepository,
    private val origin: String,
    private val onPendingPayment: (Int) -> Unit = {},
    private val savedRegion: suspend () -> String? = { null },
    private val saveRegion: suspend (String) -> Unit = {},
) : ViewModel() {
    private val _state = MutableStateFlow(SubscriptionCheckoutState())
    val state = _state.asStateFlow()
    private var receiptDataUrl: String? = null
    private var quoteGeneration = 0

    fun load() {
        quoteGeneration++
        clearReceipt()
        _state.update { it.copy(loading = true, quoting = false, errorRes = null, quote = null,
            submitted = false, alreadyPending = false) }
        viewModelScope.launch {
            // A region confirmed earlier opens checkout on the plans, like the Mini App.
            val remembered = runCatching { savedRegion() }.getOrNull()
            val overviewResult = repository.checkoutOverview(origin)
            when (overviewResult) {
                is ApiResult.Success -> {
                    val data = overviewResult.value
                    _state.update { current ->
                        val regions = availableRegions(data.prices)
                        val confirmed = current.region.takeIf { it.isNotEmpty() && current.step != CheckoutStep.REGION }
                        val region = (confirmed ?: remembered)?.takeIf { it in regions }.orEmpty()
                        val method = methodFor(region, current.method, data.prices)
                        current.copy(
                            loading = false,
                            overview = data,
                            discount = data.discount,
                            region = region,
                            method = method,
                            country = if (method == "visa" && region.isNotEmpty()) region else current.country,
                            plan = planFor(method, current.plan, data.prices),
                            language = normalizeLanguage(data.language),
                            step = when {
                                region.isEmpty() -> CheckoutStep.REGION
                                data.mode == "hsk30_unlock" && hasMethodStep(region) -> CheckoutStep.METHOD
                                data.mode == "hsk30_unlock" -> CheckoutStep.PAY
                                else -> CheckoutStep.PLANS
                            },
                            errorRes = if (data.ok) null else R.string.sub_unavailable,
                        )
                    }
                    data.pendingPayment?.id?.takeIf { it > 0 }?.let(onPendingPayment)
                }
                is ApiResult.Failure -> _state.update {
                    it.copy(loading = false, errorRes = overviewResult.error.messageRes)
                }
            }
        }
    }

    fun chooseRegion(region: String) {
        val current = _state.value
        val prices = current.overview?.prices ?: return
        if (region !in availableRegions(prices) || region == current.region) return
        val method = methodFor(region, if (region == "cn") current.method else "visa", prices)
        quoteGeneration++
        clearReceipt()
        _state.update { it.copy(region = region, method = method,
            country = if (method == "visa") region else it.country,
            plan = planFor(method, it.plan, prices),
            quoting = false, quote = null, errorRes = null, receiptNoteRes = null) }
    }

    fun choosePlan(plan: String) {
        val current = _state.value
        if (current.overview?.prices?.get(current.method)?.containsKey(plan) != true) return
        quoteGeneration++
        clearReceipt()
        _state.update { it.copy(plan = plan, quoting = false, quote = null, errorRes = null, receiptNoteRes = null) }
    }

    /** China's wallet: Alipay or WeChat Pay. */
    fun chooseMethod(method: String) {
        val current = _state.value
        val prices = current.overview?.prices ?: return
        if (method !in CHINA_METHODS || prices[method].isNullOrEmpty()) return
        quoteGeneration++
        clearReceipt()
        _state.update { it.copy(method = method, plan = planFor(method, it.plan, prices),
            quoting = false, quote = null, errorRes = null, receiptNoteRes = null) }
    }

    /** A Tajik card: Dushanbe City or Alif. */
    fun chooseBank(bank: String) {
        if (bank !in CARD_BANKS) return
        quoteGeneration++
        clearReceipt()
        _state.update { it.copy(bank = bank, quoting = false, quote = null, errorRes = null, receiptNoteRes = null) }
    }

    fun next() {
        val current = _state.value
        val overview = current.overview ?: return
        if (current.loading || current.quoting || overview.checkoutAllowed != true) return
        when (current.step) {
            CheckoutStep.REGION -> {
                val region = current.region.takeIf { it.isNotEmpty() } ?: return
                viewModelScope.launch { runCatching { saveRegion(region) } }
                if (current.isHsk30Unlock) {
                    if (hasMethodStep(region)) _state.update { it.copy(step = CheckoutStep.METHOD) }
                    else loadQuote()
                } else {
                    _state.update { it.copy(step = CheckoutStep.PLANS) }
                }
            }
            CheckoutStep.PLANS -> {
                if (overview.prices[current.method]?.get(current.plan) == null) return
                if (hasMethodStep(current.region)) _state.update { it.copy(step = CheckoutStep.METHOD) }
                else loadQuote()
            }
            CheckoutStep.METHOD -> if (overview.prices[current.method]?.get(current.plan) != null) loadQuote()
            else -> Unit
        }
    }

    /** One step back; the first step is left to the caller, which closes checkout. */
    fun back() {
        val current = _state.value
        val flow = current.flow
        val index = flow.indexOf(current.step)
        if (index <= 0) return
        quoteGeneration++
        clearReceipt()
        _state.update { it.copy(step = flow[index - 1], quoting = false, quote = null,
            errorRes = null, receiptNoteRes = null) }
    }

    private fun loadQuote() {
        val current = _state.value
        val requestGeneration = ++quoteGeneration
        _state.update { it.copy(quoting = true, step = CheckoutStep.PAY, quote = null, errorRes = null) }
        viewModelScope.launch {
            val result = repository.checkoutQuote(SubscriptionQuoteRequest(
                planType = current.plan, paymentMethod = current.method,
                cardCountry = current.country.takeIf { current.method == "visa" },
                cardBank = current.cardBank,
            ))
            if (requestGeneration != quoteGeneration) return@launch
            when (result) {
                is ApiResult.Success -> {
                    val quote = result.value.quote
                    val available = if (current.method == "visa") quote.paymentDetails.isNotBlank()
                        else quote.qr?.let { it.available && it.imageDataUrl.isNotBlank() } == true
                    _state.update { it.copy(quoting = false,
                        quote = quote.takeIf { available && result.value.ok },
                        errorRes = if (available && result.value.ok) null else if (current.method == "visa")
                            R.string.sub_unavailable else R.string.sub_qr_missing) }
                    if (available && result.value.ok) trackEvent("payment_instructions_viewed")
                }
                is ApiResult.Failure -> _state.update {
                    it.copy(quoting = false, errorRes = result.error.messageRes)
                }
            }
        }
    }

    fun startDiscount() {
        if (_state.value.discountStarting) return
        _state.update { it.copy(discountStarting = true, errorRes = null) }
        viewModelScope.launch {
            when (val result = repository.checkoutDiscountStart()) {
                is ApiResult.Success -> _state.update { it.copy(discountStarting = false,
                    discount = result.value.discount,
                    errorRes = if (result.value.ok) null else R.string.sub_unavailable) }
                is ApiResult.Failure -> _state.update {
                    it.copy(discountStarting = false, errorRes = result.error.messageRes)
                }
            }
        }
    }

    fun selectReceipt(context: Context, uri: Uri?) {
        if (uri == null) return
        _state.update { it.copy(errorRes = null, receiptNoteRes = null) }
        viewModelScope.launch {
            val prepared = withContext(Dispatchers.IO) { prepareReceipt(context, uri) }
            receiptDataUrl = prepared?.first
            _state.update { it.copy(
                receiptName = if (prepared != null) receiptName(context, uri) else "",
                receiptBytes = prepared?.second ?: 0,
                receiptNoteRes = if (prepared == null) R.string.sub_receipt_invalid else null,
            ) }
            if (prepared != null) trackEvent("payment_receipt_selected")
        }
    }

    fun submit() {
        val current = _state.value
        val receipt = receiptDataUrl
        if (current.submitting || current.quote == null || receipt == null) {
            if (receipt == null) _state.update { it.copy(receiptNoteRes = R.string.sub_receipt_invalid) }
            return
        }
        _state.update { it.copy(submitting = true, errorRes = null) }
        viewModelScope.launch {
            when (val result = repository.checkoutSubmit(SubscriptionSubmitRequest(
                planType = current.plan, paymentMethod = current.method,
                cardCountry = current.country.takeIf { current.method == "visa" },
                cardBank = current.cardBank,
                screenshotDataUrl = receipt, attemptId = current.overview?.attemptId,
            ))) {
                is ApiResult.Success -> {
                    val success = result.value.ok && result.value.status == "pending"
                    if (success) {
                        clearReceipt()
                        if (result.value.paymentId > 0) onPendingPayment(result.value.paymentId)
                    }
                    _state.update { it.copy(submitting = false, submitted = success,
                        alreadyPending = result.value.alreadyPending,
                        step = if (success) CheckoutStep.DONE else it.step,
                        errorRes = if (success) null else R.string.sub_unavailable) }
                }
                is ApiResult.Failure -> _state.update {
                    it.copy(submitting = false, errorRes = result.error.messageRes)
                }
            }
        }
    }

    private fun trackEvent(stage: String) {
        val current = _state.value
        val attemptId = current.overview?.attemptId ?: return
        viewModelScope.launch { repository.checkoutEvent(SubscriptionCheckoutEventRequest(
            attemptId = attemptId, stage = stage, planType = current.plan,
            paymentMethod = current.method,
        )) }
    }

    private fun clearReceipt() {
        receiptDataUrl = null
        _state.update { it.copy(receiptName = "", receiptBytes = 0) }
    }

    class Factory(
        private val repository: FeatureRepository,
        private val origin: String,
        private val onPendingPayment: (Int) -> Unit = {},
        private val savedRegion: suspend () -> String? = { null },
        private val saveRegion: suspend (String) -> Unit = {},
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            SubscriptionCheckoutViewModel(repository, origin, onPendingPayment, savedRegion, saveRegion) as T
    }

    private companion object {
        val PLANS = listOf("hsk30_unlock", "1_month", "10_days", "3_months")
        const val MAX_RECEIPT_BYTES = 8 * 1024 * 1024
        const val MAX_SOURCE_BYTES = 24 * 1024 * 1024
        const val TARGET_BASE64_CHARS = 300 * 1024
        val STEPS = listOf(1280 to 72, 1100 to 65, 900 to 60, 720 to 55)

        fun planFor(method: String, current: String, prices: Map<String, Map<String, SubscriptionPriceDto>>): String =
            current.takeIf { prices[method]?.containsKey(it) == true }
                ?: PLANS.firstOrNull { prices[method]?.containsKey(it) == true } ?: current

        fun normalizeLanguage(value: String): String = when (value.lowercase()) {
            "ru" -> "ru"
            "tj", "tg", "tg-cyrl" -> "tj"
            else -> "uz"
        }

        fun receiptName(context: Context, uri: Uri): String = runCatching {
            context.contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)
                ?.use { cursor -> if (cursor.moveToFirst()) cursor.getString(0) else null }
        }.getOrNull().orEmpty().ifBlank { "screenshot" }

        fun prepareReceipt(context: Context, uri: Uri): Pair<String, Int>? = runCatching {
            val source = context.contentResolver.openInputStream(uri)?.use { input ->
                val output = ByteArrayOutputStream()
                val buffer = ByteArray(8192)
                while (true) {
                    val read = input.read(buffer)
                    if (read < 0) break
                    output.write(buffer, 0, read)
                    if (output.size() > MAX_SOURCE_BYTES) return null
                }
                output.toByteArray()
            } ?: return null
            if (source.isEmpty()) return null
            val mime = when {
                source.size >= 3 && source[0] == 0xff.toByte() && source[1] == 0xd8.toByte() && source[2] == 0xff.toByte() -> "image/jpeg"
                source.size >= 8 && source.copyOfRange(0, 8).contentEquals(byteArrayOf(0x89.toByte(), 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a)) -> "image/png"
                source.size >= 12 && String(source, 0, 4, Charsets.US_ASCII) == "RIFF" &&
                    String(source, 8, 4, Charsets.US_ASCII) == "WEBP" -> "image/webp"
                else -> null
            }
            val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
            BitmapFactory.decodeByteArray(source, 0, source.size, bounds)
            val sample = (maxOf(bounds.outWidth, bounds.outHeight) / 2560).coerceAtLeast(1)
            val bitmap = BitmapFactory.decodeByteArray(source, 0, source.size,
                BitmapFactory.Options().apply { inSampleSize = sample })
            var best = source.takeIf { mime != null && it.size <= MAX_RECEIPT_BYTES }
            if (bitmap != null) {
                for ((maxSide, quality) in STEPS) {
                    val scale = (maxSide.toFloat() / maxOf(bitmap.width, bitmap.height)).coerceAtMost(1f)
                    val scaled = Bitmap.createScaledBitmap(bitmap,
                        (bitmap.width * scale).toInt().coerceAtLeast(1),
                        (bitmap.height * scale).toInt().coerceAtLeast(1), true)
                    val output = ByteArrayOutputStream()
                    scaled.compress(Bitmap.CompressFormat.JPEG, quality, output)
                    if (scaled !== bitmap) scaled.recycle()
                    val candidate = output.toByteArray()
                    if (candidate.isNotEmpty() && candidate.size <= MAX_RECEIPT_BYTES &&
                        (best == null || candidate.size < best.size)) best = candidate
                    if (candidate.size * 4 / 3 <= TARGET_BASE64_CHARS) break
                }
                bitmap.recycle()
            }
            val bytes = best ?: return null
            val outMime = if (bytes === source) mime ?: return null else "image/jpeg"
            Pair("data:$outMime;base64," + Base64.encodeToString(bytes, Base64.NO_WRAP), bytes.size)
        }.getOrNull()
    }
}
