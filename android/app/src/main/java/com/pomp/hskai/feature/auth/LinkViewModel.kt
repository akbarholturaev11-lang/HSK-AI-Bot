package com.pomp.hskai.feature.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.pomp.hskai.core.auth.AuthRepository
import com.pomp.hskai.core.auth.PendingLink
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class LinkUiState(
    val isRequestingCode: Boolean = false,
    val pending: PendingLink? = null,
    val secondsRemaining: Int = 0,
    val isWaitingForApproval: Boolean = false,
    val isExpired: Boolean = false,
    val isLinked: Boolean = false,
    val error: ApiError? = null,
) {
    val displayCode: String get() = pending?.displayCode.orEmpty()
    val botDeepLink: String get() = pending?.botDeepLink.orEmpty()
}

/**
 * Drives the Telegram device-link screen.
 *
 * The polling secret never reaches the UI state that gets rendered — only the
 * display code and the bot link are shown. Polling stops on success, on
 * expiry, and on any error that cannot be resolved by waiting.
 */
class LinkViewModel(
    private val authRepository: AuthRepository,
    private val now: () -> Long = System::currentTimeMillis,
) : ViewModel() {

    private val _state = MutableStateFlow(LinkUiState())
    val state: StateFlow<LinkUiState> = _state.asStateFlow()

    private var pollJob: Job? = null

    fun requestCode() {
        if (_state.value.isRequestingCode) return
        pollJob?.cancel()
        _state.value = LinkUiState(isRequestingCode = true)
        viewModelScope.launch {
            when (val result = authRepository.startLink()) {
                is ApiResult.Failure -> _state.value = LinkUiState(error = result.error)
                is ApiResult.Success -> {
                    _state.value = LinkUiState(
                        pending = result.value,
                        secondsRemaining = remainingSeconds(result.value),
                        isWaitingForApproval = true,
                    )
                    startPolling(result.value)
                }
            }
        }
    }

    fun dismissError() = _state.update { it.copy(error = null) }

    private fun startPolling(pending: PendingLink) {
        pollJob = viewModelScope.launch {
            while (true) {
                val remaining = remainingSeconds(pending)
                _state.update { it.copy(secondsRemaining = remaining) }
                if (remaining <= 0) {
                    _state.update {
                        it.copy(isWaitingForApproval = false, isExpired = true)
                    }
                    return@launch
                }
                when (val result = authRepository.pollLink(pending)) {
                    is ApiResult.Success -> if (result.value) {
                        _state.update {
                            it.copy(isWaitingForApproval = false, isLinked = true)
                        }
                        authRepository.bootstrap()
                        return@launch
                    }

                    is ApiResult.Failure -> {
                        // Offline or a slow server is worth waiting out; an
                        // invalid/consumed/expired link is not.
                        val transient = result.error is ApiError.Offline ||
                            result.error is ApiError.Timeout
                        if (!transient) {
                            _state.update {
                                it.copy(
                                    isWaitingForApproval = false,
                                    isExpired = true,
                                    error = result.error,
                                )
                            }
                            return@launch
                        }
                    }
                }
                delay(POLL_INTERVAL_MILLIS)
            }
        }
    }

    private fun remainingSeconds(pending: PendingLink): Int =
        ((pending.expiresAtMillis - now()) / 1_000L).coerceAtLeast(0L).toInt()

    override fun onCleared() {
        pollJob?.cancel()
        super.onCleared()
    }

    private companion object {
        const val POLL_INTERVAL_MILLIS = 2_000L
    }
}
