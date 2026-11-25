package com.pomp.hskai.feature.subscription

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.pomp.hskai.core.network.ApiResult
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.net.URI

internal fun safeLavaPaymentUrl(value: String?): String? = runCatching {
    val uri = URI(value ?: return null)
    value.takeIf { uri.scheme == "https" && (uri.host == "lava.top" || uri.host?.endsWith(".lava.top") == true) &&
        uri.rawUserInfo == null && (uri.port == -1 || uri.port == 443) }
}.getOrNull()

data class NativeLavaState(
    val loading: Boolean = true, val block: LavaBlock? = null, val busy: Boolean = false,
    val plan: String = "", val email: String = "", val mode: String = "subscription",
    val checkoutId: Int = 0, val status: String = "", val paymentUrl: String? = null,
    val launchUrl: String? = null, val error: Boolean = false,
    val offer: ExitReply? = null, val closeRequested: Boolean = false,
    val uncertainStart: Boolean = false,
    val region: String = "",
    val currency: String = "",
) {
    val visiblePlans: List<LavaPlan> get() = block?.let {
        if (mode == "exit_discount" || currency.isBlank()) it.plans.filter { row -> row.amount != null }
        else it.providerPlans(currency)
    }.orEmpty()
}

class LavaCheckoutViewModel(
    private val repository: LavaCheckoutRepository, private val language: String,
    private val savedRegion: suspend () -> String? = { null },
    private val saveRegion: suspend (String) -> Unit = {},
    private val regionHint: () -> String = { "other" },
) : ViewModel() {
    private val _state = MutableStateFlow(NativeLavaState())
    val state = _state.asStateFlow()
    private var generation = 0
    private var offerAsked = false
    private val _closeEvents = MutableSharedFlow<Unit>(extraBufferCapacity = 1)
    val closeEvents = _closeEvents.asSharedFlow()
    init { load() }

    fun load() {
        if (_state.value.busy) return
        val current = ++generation
        _state.update { it.copy(loading = true, error = false) }
        viewModelScope.launch {
            val region = _state.value.region.ifBlank {
                runCatching { savedRegion() }.getOrNull()?.takeIf { it in CHECKOUT_REGIONS } ?: regionHint()
            }
            when (val result = repository.providerOverview(_state.value.mode)) {
                is ApiResult.Success -> if (current == generation) _state.update { old ->
                    val block = result.value.lava
                    val id = old.checkoutId.takeIf { it > 0 } ?: block?.pending_checkout_id ?: 0
                    val selected = old.copy(loading = false, block = block, region = old.region.ifBlank { region },
                        currency = if (old.mode == "exit_discount") "" else block?.currencyFor(old.region.ifBlank { region }).orEmpty())
                    selected.copy(
                        plan = old.plan.takeIf { plan -> selected.visiblePlans.any { it.plan_type == plan } }
                            ?: selected.visiblePlans.firstOrNull()?.plan_type.orEmpty(),
                        email = old.email.ifBlank { block?.email.orEmpty() }, checkoutId = id,
                        status = old.status.ifBlank { if (id > 0) "pending" else "" },
                        uncertainStart = false, error = !result.value.ok || (old.mode == "exit_discount" && block == null))
                }
                is ApiResult.Failure -> if (current == generation) _state.update { it.copy(loading = false, error = true) }
            }
        }
    }
    fun chooseRegion(region: String, persist: Boolean = true) {
        val old = _state.value
        if (region !in CHECKOUT_REGIONS || old.loading || old.busy || old.checkoutId > 0 ||
            old.uncertainStart || old.mode != "subscription" || old.block?.subscription != null) return
        val selected = old.copy(region = region, currency = old.block?.currencyFor(region).orEmpty(), error = false)
        _state.value = selected.copy(plan = selected.plan.takeIf { plan -> selected.visiblePlans.any { it.plan_type == plan } }
            ?: selected.visiblePlans.firstOrNull()?.plan_type.orEmpty())
        if (persist) viewModelScope.launch { runCatching { saveRegion(region) } }
    }

    fun email(value: String) { if (!_state.value.busy) _state.update { it.copy(email = value.take(254)) } }
    fun chooseProviderPlan(value: String) {
        if (!_state.value.busy && _state.value.visiblePlans.any { it.plan_type == value && it.amount != null })
            _state.update { it.copy(plan = value, error = false) }
    }
    fun start() {
        val old = _state.value
        if (old.busy || old.checkoutId > 0 || old.uncertainStart || old.block?.blocked_reason != null ||
            old.visiblePlans.none { it.plan_type == old.plan && it.amount != null }) return
        _state.update { it.copy(busy = true, error = false) }
        viewModelScope.launch {
            when (val reply = repository.start(old.plan, old.email, old.mode, language,
                old.currency.takeIf { old.mode == "subscription" && it.isNotBlank() })) {
                is ApiResult.Success -> {
                    val value = reply.value
                    val url = safeLavaPaymentUrl(value.payment_url)
                    _state.update { it.copy(busy = false, checkoutId = value.checkout_id,
                        status = if (value.ok && value.checkout_id > 0) "pending" else "",
                        paymentUrl = url, launchUrl = url, error = !value.ok || url == null) }
                }
                is ApiResult.Failure -> {
                    // A provider invoice may exist even if its HTTP reply was lost.
                    // Re-read canonical pending ID before offering another start.
                    _state.update { it.copy(busy = false, error = true, uncertainStart = true) }
                }
            }
        }
    }
    fun refresh() {
        val old = _state.value
        if (old.busy || old.checkoutId <= 0) return
        _state.update { it.copy(busy = true, error = false) }
        viewModelScope.launch {
            when (val reply = repository.status(old.checkoutId)) {
                is ApiResult.Success -> _state.update { it.copy(busy = false, status = reply.value.status, error = !reply.value.ok) }
                is ApiResult.Failure -> _state.update { it.copy(busy = false, error = true) }
            }
        }
    }
    fun cancelRenewal() {
        if (_state.value.busy) return
        _state.update { it.copy(busy = true, error = false) }
        viewModelScope.launch {
            when (val reply = repository.cancel()) {
                is ApiResult.Success -> {
                    _state.update { it.copy(busy = false, error = !reply.value.ok) }
                    if (reply.value.ok) load()
                }
                is ApiResult.Failure -> _state.update { it.copy(busy = false, error = true) }
            }
        }
    }
    fun urlOpened(success: Boolean) { _state.update { it.copy(launchUrl = null, error = !success) } }
    fun reopenPayment() { _state.update { it.copy(launchUrl = it.paymentUrl) } }
    fun requestProviderClose() {
        val old = _state.value
        if (old.busy) return
        if (offerAsked || old.checkoutId > 0 || old.block?.subscription != null || old.block == null) {
            close(); return
        }
        offerAsked = true
        _state.update { it.copy(busy = true) }
        viewModelScope.launch {
            when (val reply = repository.exitOffer("view")) {
                is ApiResult.Success -> {
                    val offer = reply.value.takeIf { it.ok && it.available && it.percent == 20 }
                    _state.update { it.copy(busy = false, offer = offer) }
                    if (offer == null) close()
                }
                is ApiResult.Failure -> close()
            }
        }
    }
    fun close() {
        _state.update { it.copy(busy = false, offer = null, closeRequested = true) }
        _closeEvents.tryEmit(Unit)
    }
    fun claim() {
        if (_state.value.busy) return
        _state.update { it.copy(busy = true, error = false) }
        viewModelScope.launch {
            when (val reply = repository.exitOffer("claim")) {
                is ApiResult.Success -> {
                    val accepted = reply.value.ok && reply.value.available && reply.value.accepted
                    _state.update { it.copy(busy = false, offer = if (accepted) null else it.offer,
                        mode = if (accepted) "exit_discount" else it.mode, error = !accepted) }
                    if (accepted) load()
                }
                is ApiResult.Failure -> _state.update { it.copy(busy = false, error = true) }
            }
        }
    }
}
