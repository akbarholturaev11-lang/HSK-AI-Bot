package com.pomp.hskai.feature.limit

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.repository.FeatureRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class SubscriptionHandoffState(
    val isOpening: Boolean = false,
    val error: ApiError? = null,
    /**
     * Set once the bot chat has been opened, so returning to the app can
     * re-read entitlement from the server instead of guessing locally.
     */
    val awaitingReturn: Boolean = false,
)

/** One-shot request to open a Telegram link, consumed by the host activity. */
data class TelegramHandoff(val id: String, val url: String)

/**
 * Drives the "Limitsiz o'qish" button.
 *
 * It asks the server to post the subscription menu into the learner's Telegram
 * chat, then reports where to open it. This ViewModel never decides who is
 * paid: entitlement is re-read from the server after the learner comes back.
 */
class SubscriptionHandoffViewModel(
    private val repository: FeatureRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(SubscriptionHandoffState())
    val state: StateFlow<SubscriptionHandoffState> = _state.asStateFlow()

    private val _handoff = MutableStateFlow<TelegramHandoff?>(null)
    val handoff: StateFlow<TelegramHandoff?> = _handoff.asStateFlow()

    fun openSubscription() {
        if (_state.value.isOpening) return
        _state.update { it.copy(isOpening = true, error = null) }
        viewModelScope.launch {
            when (val result = repository.subscriptionOpen()) {
                is ApiResult.Success -> {
                    val url = result.value.botUrl
                    if (url.isBlank()) {
                        // Nothing to open. Say so rather than launching an
                        // intent that resolves to nowhere.
                        _state.update {
                            it.copy(
                                isOpening = false,
                                error = ApiError.fromCode(
                                    "android_subscription_handoff_unavailable",
                                ),
                            )
                        }
                    } else {
                        _handoff.value = TelegramHandoff(
                            id = java.util.UUID.randomUUID().toString(),
                            url = url,
                        )
                        _state.update {
                            it.copy(isOpening = false, awaitingReturn = true)
                        }
                    }
                }

                is ApiResult.Failure -> _state.update {
                    it.copy(isOpening = false, error = result.error)
                }
            }
        }
    }

    /**
     * Reports the outcome of the launch attempt.
     *
     * When nothing on the device could open the link there is no Telegram trip
     * to come back from, so the pending return is dropped and the learner is
     * told — a silent no-op would look like a broken button.
     */
    fun onHandoffDelivered(id: String, opened: Boolean) {
        if (_handoff.value?.id != id) return
        _handoff.value = null
        if (!opened) {
            _state.update {
                it.copy(
                    awaitingReturn = false,
                    error = ApiError.fromCode("android_subscription_handoff_unavailable"),
                )
            }
        }
    }

    /** Called once entitlement has been re-read after the learner returned. */
    fun onReturnHandled() {
        _state.update { it.copy(awaitingReturn = false) }
    }

    fun clearError() {
        _state.update { it.copy(error = null) }
    }

    class Factory(
        private val repository: FeatureRepository,
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            SubscriptionHandoffViewModel(repository) as T
    }
}
