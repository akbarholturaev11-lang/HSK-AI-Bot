package com.pomp.hskai.feature.subscription

import android.content.Context
import android.net.Uri
import android.util.Base64
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.pomp.hskai.R
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.SubscriptionCheckoutOverviewDto
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

data class SubscriptionCheckoutState(
    val loading: Boolean = true,
    val quoting: Boolean = false,
    val submitting: Boolean = false,
    val overview: SubscriptionCheckoutOverviewDto? = null,
    val quote: SubscriptionQuoteDto? = null,
    val plan: String = "1_month",
    val method: String = "visa",
    val country: String = "tj",
    val receiptSelected: Boolean = false,
    val submitted: Boolean = false,
    val errorRes: Int? = null,
)

class SubscriptionCheckoutViewModel(private val repository: FeatureRepository) : ViewModel() {
    private val _state = MutableStateFlow(SubscriptionCheckoutState())
    val state = _state.asStateFlow()
    private var receiptDataUrl: String? = null

    fun load() {
        if (_state.value.loading && _state.value.overview != null) return
        receiptDataUrl = null
        _state.update { it.copy(loading = true, errorRes = null, quote = null, receiptSelected = false, submitted = false) }
        viewModelScope.launch {
            when (val result = repository.checkoutOverview()) {
                is ApiResult.Success -> _state.update {
                    it.copy(
                        loading = false, overview = result.value,
                        errorRes = if (result.value.ok) null else R.string.sub_unavailable,
                    )
                }
                is ApiResult.Failure -> _state.update {
                    it.copy(loading = false, errorRes = result.error.messageRes)
                }
            }
        }
    }

    fun choosePlan(plan: String) {
        if (plan !in setOf("10_days", "1_month", "3_months")) return
        receiptDataUrl = null
        _state.update { it.copy(plan = plan, quote = null, receiptSelected = false, errorRes = null) }
    }

    fun chooseMethod(method: String) {
        if (method !in setOf("visa", "alipay", "wechat")) return
        receiptDataUrl = null
        _state.update { it.copy(method = method, quote = null, receiptSelected = false, errorRes = null) }
    }

    fun chooseCountry(country: String) {
        if (country !in setOf("tj", "uz", "ru", "other")) return
        receiptDataUrl = null
        _state.update { it.copy(country = country, quote = null, receiptSelected = false, errorRes = null) }
    }

    fun backToPlans() {
        receiptDataUrl = null
        _state.update { it.copy(quote = null, receiptSelected = false, errorRes = null) }
    }

    fun loadQuote() {
        val current = _state.value
        if (current.quoting || current.loading || current.overview?.checkoutAllowed != true) return
        _state.update { it.copy(quoting = true, errorRes = null) }
        viewModelScope.launch {
            val result = repository.checkoutQuote(
                SubscriptionQuoteRequest(
                    planType = current.plan, paymentMethod = current.method,
                    cardCountry = current.country.takeIf { current.method == "visa" },
                )
            )
            when (result) {
                is ApiResult.Success -> {
                    val quote = result.value.quote
                    val available = if (current.method == "visa") quote.paymentDetails.isNotBlank()
                        else quote.qr?.let { it.available && it.imageDataUrl.isNotBlank() } == true
                    _state.update {
                        it.copy(
                            quoting = false, quote = quote.takeIf { available && result.value.ok },
                            errorRes = if (available && result.value.ok) null else if (current.method == "visa")
                                R.string.sub_unavailable else R.string.sub_qr_missing,
                        )
                    }
                }
                is ApiResult.Failure -> _state.update {
                    it.copy(quoting = false, errorRes = result.error.messageRes)
                }
            }
        }
    }

    fun selectReceipt(context: Context, uri: Uri?) {
        if (uri == null) return
        _state.update { it.copy(errorRes = null) }
        viewModelScope.launch {
            val dataUrl = withContext(Dispatchers.IO) {
                runCatching {
                    context.contentResolver.openInputStream(uri)?.use { input ->
                        val output = ByteArrayOutputStream()
                        val buffer = ByteArray(8192)
                        while (true) {
                            val read = input.read(buffer)
                            if (read < 0) break
                            output.write(buffer, 0, read)
                            if (output.size() > MAX_RECEIPT_BYTES) return@withContext null
                        }
                        val data = output.toByteArray()
                        val mime = when {
                            data.size >= 3 && data[0] == 0xff.toByte() && data[1] == 0xd8.toByte() && data[2] == 0xff.toByte() -> "image/jpeg"
                            data.size >= 8 && data.copyOfRange(0, 8).contentEquals(PNG_MAGIC) -> "image/png"
                            data.size >= 12 && String(data, 0, 4, Charsets.US_ASCII) == "RIFF" &&
                                String(data, 8, 4, Charsets.US_ASCII) == "WEBP" -> "image/webp"
                            else -> return@withContext null
                        }
                        "data:$mime;base64," + Base64.encodeToString(data, Base64.NO_WRAP)
                    }
                }.getOrNull()
            }
            receiptDataUrl = dataUrl
            _state.update { it.copy(receiptSelected = dataUrl != null, errorRes = if (dataUrl == null) R.string.sub_receipt_invalid else null) }
        }
    }

    fun submit() {
        val current = _state.value
        val receipt = receiptDataUrl
        if (current.submitting || current.quote == null || receipt == null) {
            if (receipt == null) _state.update { it.copy(errorRes = R.string.sub_receipt_invalid) }
            return
        }
        _state.update { it.copy(submitting = true, errorRes = null) }
        viewModelScope.launch {
            when (val result = repository.checkoutSubmit(
                SubscriptionSubmitRequest(
                    planType = current.plan, paymentMethod = current.method,
                    cardCountry = current.country.takeIf { current.method == "visa" },
                    screenshotDataUrl = receipt,
                )
            )) {
                is ApiResult.Success -> {
                    receiptDataUrl = null
                    _state.update {
                        it.copy(
                            submitting = false, submitted = result.value.ok && result.value.status == "pending",
                            receiptSelected = false,
                            errorRes = if (result.value.ok) null else R.string.sub_unavailable,
                        )
                    }
                }
                is ApiResult.Failure -> _state.update {
                    it.copy(submitting = false, errorRes = result.error.messageRes)
                }
            }
        }
    }

    class Factory(private val repository: FeatureRepository) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            SubscriptionCheckoutViewModel(repository) as T
    }

    private companion object {
        const val MAX_RECEIPT_BYTES = 8 * 1024 * 1024
        val PNG_MAGIC = byteArrayOf(0x89.toByte(), 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a)
    }
}
