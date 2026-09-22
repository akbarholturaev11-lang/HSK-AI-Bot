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
    /**
     * The bot deep link, handed to the screen once for the same reason: the
     * learner asked for Telegram, so Telegram opens exactly once.
     */
    val pendingTelegramUrl: String? = null,
) {
    val displayCode: String get() = pending?.displayCode.orEmpty()
    val botDeepLink: String get() = pending?.botDeepLink.orEmpty()
}

/**
 * Drives the Telegram device-link screen.
 *
 * The polling secret never reaches the UI state that gets rendered — only the
 * bot link is handed to the screen, and only to be opened. Polling stops on
 * success, on expiry, and on any error that cannot be resolved by waiting.
 */
class LinkViewModel(
    private val authRepository: AuthRepository,
    private val now: () -> Long = System::currentTimeMillis,
) : ViewModel() {

    private val _state = MutableStateFlow(LinkUiState())
    val state: StateFlow<LinkUiState> = _state.asStateFlow()

    private var pollJob: Job? = null
    /** The in-flight start of a link, so stepping back can cancel it. */
    private var startJob: Job? = null

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

    /** The screen calls this once it has opened Telegram. */
    fun telegramUrlOpened() = _state.update { it.copy(pendingTelegramUrl = null) }

    /**
     * Opens the bot for the Telegram card.
     *
     * A link is reserved first, unless one from an earlier tap is still
     * valid. Either way the learner never sees, copies or types a code: the
     * bot reads the request out of the deep link and shows one confirm
     * button.
     */
    fun continueWithTelegram() {
        val current = _state.value
        if (current.isRequestingCode) return
        val pending = current.pending
        if (pending == null || current.isExpired || remainingSeconds(pending) <= 0) {
            requestCode(openTelegram = true)
            return
        }
        _state.update {
            it.copy(
                busyProvider = AuthProvider.TELEGRAM,
                isWaitingForApproval = true,
                error = null,
                pendingTelegramUrl = pending.botDeepLink.ifEmpty { null },
            )
        }
    }

    /** Steps back from a provider that was started, back to the cards. */
    fun dismissWaiting() {
        startJob?.cancel()
        _state.update {
            it.copy(
                isRequestingCode = false,
                busyProvider = null,
                pendingTelegramUrl = null,
                error = null,
            )
        }
    }

    private fun startProvider(
        provider: AuthProvider,
        start: suspend () -> ApiResult<PendingLink>,
    ) {
        if (_state.value.busyProvider != null) return
        pollJob?.cancel()
        _state.update {
            it.copy(busyProvider = provider, error = null, isExpired = false)
        }
        startJob = viewModelScope.launch {
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

    /**
     * Reserves a link request and starts polling for its approval.
     *
     * With [openTelegram] the bot deep link is published to the screen too,
     * which is what the Telegram card wants; Google and Apple reserve their
     * own link rows through [startProvider].
     */
    fun requestCode(openTelegram: Boolean = false) {
        if (_state.value.isRequestingCode) return
        pollJob?.cancel()
        val providers = _state.value.providers
        _state.value = LinkUiState(isRequestingCode = true, providers = providers)
        startJob = viewModelScope.launch {
            when (val result = authRepository.startLink()) {
                is ApiResult.Failure -> _state.value =
                    LinkUiState(error = result.error, providers = providers)

                is ApiResult.Success -> {
                    val pending = result.value
                    _state.value = LinkUiState(
                        pending = pending,
                        secondsRemaining = remainingSeconds(pending),
                        isWaitingForApproval = true,
                        providers = providers,
                        busyProvider = AuthProvider.TELEGRAM.takeIf { openTelegram },
                        pendingTelegramUrl = pending.botDeepLink
                            .ifEmpty { null }
                            .takeIf { openTelegram },
                    )
                    startPolling(pending)
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
        startJob?.cancel()
        pollJob?.cancel()
        super.onCleared()
    }

    private companion object {
        const val POLL_INTERVAL_MILLIS = 2_000L
    }
}
