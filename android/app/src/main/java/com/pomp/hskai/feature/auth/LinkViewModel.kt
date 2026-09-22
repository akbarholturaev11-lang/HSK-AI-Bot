package com.pomp.hskai.feature.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.pomp.hskai.core.auth.AuthProvider
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
    /** Providers this server and build can actually offer, beyond Telegram. */
    val providers: List<AuthProvider> = emptyList(),
    /** A provider sheet or browser tab is in flight. */
    val busyProvider: AuthProvider? = null,
    /**
     * Apple's authorization page, to be opened in a Custom Tab. Consumed once
     * by the screen so a recomposition cannot reopen the browser.
     */
    val pendingBrowserUrl: String? = null,
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

    /**
     * Loads the provider list.
     *
     * Failure is silent on purpose: Telegram always works, so a provider probe
     * that cannot reach the server must not put an error on the login screen.
     */
    fun loadProviders() {
        viewModelScope.launch {
            val providers = authRepository.availableProviders()
            _state.update { it.copy(providers = providers) }
        }
    }

    fun signInWithGoogle() = startProvider(AuthProvider.GOOGLE) {
        authRepository.startGoogleSignIn()
    }

    fun signInWithApple() = startProvider(AuthProvider.APPLE) {
        authRepository.startAppleSignIn()
    }

    /** The screen calls this once it has opened the browser. */
    fun browserUrlOpened() = _state.update { it.copy(pendingBrowserUrl = null) }

    private fun startProvider(
        provider: AuthProvider,
        start: suspend () -> ApiResult<PendingLink>,
    ) {
        if (_state.value.busyProvider != null) return
        pollJob?.cancel()
        _state.update {
            it.copy(busyProvider = provider, error = null, isExpired = false)
        }
        viewModelScope.launch {
            when (val result = start()) {
                is ApiResult.Failure -> _state.update {
                    it.copy(
                        busyProvider = null,
                        // A dismissed sheet is a choice, not a failure worth
                        // shouting about; the screen stays as it was.
                        error = result.error.takeIf { error ->
                            error !is ApiError.ProviderCancelled
                        },
                    )
                }

                is ApiResult.Success -> {
                    val pending = result.value
                    _state.update {
                        it.copy(
                            busyProvider = provider,
                            pending = pending,
                            secondsRemaining = remainingSeconds(pending),
                            isWaitingForApproval = true,
                            pendingBrowserUrl = pending.authorizeUrl.ifEmpty { null },
                        )
                    }
                    startPolling(pending)
                }
            }
        }
    }

    fun requestCode() {
        if (_state.value.isRequestingCode) return
        pollJob?.cancel()
        val providers = _state.value.providers
        _state.value = LinkUiState(isRequestingCode = true, providers = providers)
        viewModelScope.launch {
            when (val result = authRepository.startLink()) {
                is ApiResult.Failure -> _state.value =
                    LinkUiState(error = result.error, providers = providers)

                is ApiResult.Success -> {
                    _state.value = LinkUiState(
                        pending = result.value,
                        secondsRemaining = remainingSeconds(result.value),
                        isWaitingForApproval = true,
                        providers = providers,
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
                        it.copy(
                            isWaitingForApproval = false,
                            isExpired = true,
                            busyProvider = null,
                        )
                    }
                    return@launch
                }
                when (val result = authRepository.pollLink(pending)) {
                    is ApiResult.Success -> if (result.value) {
                        _state.update {
                            it.copy(
                                isWaitingForApproval = false,
                                isLinked = true,
                                busyProvider = null,
                            )
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
                                    busyProvider = null,
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
