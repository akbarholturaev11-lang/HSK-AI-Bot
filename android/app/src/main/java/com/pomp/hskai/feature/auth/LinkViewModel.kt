package com.pomp.hskai.feature.auth

import android.app.Activity
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.pomp.hskai.core.auth.AuthProvider
import com.pomp.hskai.core.auth.AuthRepository
import com.pomp.hskai.core.auth.PendingLink
import com.pomp.hskai.core.auth.SignupReferral
import com.pomp.hskai.core.i18n.AppLanguage
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
    val referralCode: String = "",
    val referralInvalid: Boolean = false,
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

    private val _state = MutableStateFlow(LinkUiState(referralCode = authRepository.signupReferralCode.value))
    val state: StateFlow<LinkUiState> = _state.asStateFlow()

    private var pollJob: Job? = null
    /** The in-flight start of a link, so stepping back can cancel it. */
    private var startJob: Job? = null
    private var attemptGeneration = 0L

    init {
        viewModelScope.launch {
            authRepository.signupReferralCode.collect { code ->
                _state.update { if (it.referralCode == code) it else it.copy(referralCode = code, referralInvalid = false) }
            }
        }
    }

    fun updateReferralCode(value: String) {
        if (_state.value.busyProvider != null || _state.value.isRequestingCode) return
        authRepository.updateSignupReferralCode(value)
        _state.update { it.copy(referralCode = authRepository.signupReferralCode.value, referralInvalid = false) }
    }

    private fun validReferral(): Boolean {
        val code = authRepository.signupReferralCode.value
        val valid = code.isBlank() || SignupReferral.code(code) != null
        if (!valid) _state.update { it.copy(referralInvalid = true) }
        return valid
    }

    /**
     * Loads the provider list.
     *
     * Failure is silent on purpose: Telegram always works, so a provider probe
     * that cannot reach the server must not put an error on the login screen.
     */
    fun loadProviders() {
        viewModelScope.launch {
            val providers = authRepository.availableBrowserProviders()
            _state.update { it.copy(providers = providers) }
        }
    }

    fun signInWithGoogle(activity: Activity?, language: AppLanguage? = null) = startProvider(AuthProvider.GOOGLE) {
        authRepository.startGoogleBrowserSignIn(language = language)
    }

    fun signInWithApple(language: AppLanguage? = null) = startProvider(AuthProvider.APPLE) {
        authRepository.startAppleSignIn(language = language)
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
    fun continueWithTelegram(language: AppLanguage) {
        val current = _state.value
        if (current.isRequestingCode || current.busyProvider?.let { it != AuthProvider.TELEGRAM } == true) return
        val pending = current.pending
        if (pending == null || pending.provider != AuthProvider.TELEGRAM || current.isExpired || remainingSeconds(pending) <= 0) {
            requestCode(openTelegram = true, language = language)
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
        cancelAttempt()
        _state.value = LinkUiState(providers = _state.value.providers, referralCode = authRepository.signupReferralCode.value)
    }

    private fun startProvider(
        provider: AuthProvider,
        start: suspend () -> ApiResult<PendingLink>,
    ) {
        if (_state.value.busyProvider != null || _state.value.isRequestingCode) return
        if (!validReferral()) return
        val generation = cancelAttempt()
        _state.value = LinkUiState(providers = _state.value.providers, busyProvider = provider, referralCode = authRepository.signupReferralCode.value)
        startJob = viewModelScope.launch {
            val result = start()
            if (attemptGeneration != generation) return@launch
            when (result) {
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
                    startPolling(pending, generation)
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
    fun requestCode(
        openTelegram: Boolean = false,
        language: AppLanguage? = null,
    ) {
        if (_state.value.isRequestingCode || _state.value.busyProvider != null) return
        if (!validReferral()) return
        val generation = cancelAttempt()
        val providers = _state.value.providers
        _state.value = LinkUiState(isRequestingCode = true, providers = providers, referralCode = authRepository.signupReferralCode.value)
        startJob = viewModelScope.launch {
            val result = authRepository.startLink(language)
            if (attemptGeneration != generation) return@launch
            when (result) {
                is ApiResult.Failure -> _state.value =
                    LinkUiState(error = result.error, providers = providers, referralCode = authRepository.signupReferralCode.value)

                is ApiResult.Success -> {
                    val pending = result.value
                    _state.value = LinkUiState(
                        referralCode = authRepository.signupReferralCode.value,
                        pending = pending,
                        secondsRemaining = remainingSeconds(pending),
                        isWaitingForApproval = true,
                        providers = providers,
                        busyProvider = AuthProvider.TELEGRAM.takeIf { openTelegram },
                        pendingTelegramUrl = pending.botDeepLink
                            .ifEmpty { null }
                            .takeIf { openTelegram },
                    )
                    startPolling(pending, generation)
                }
            }
        }
    }

    fun dismissError() = _state.update { it.copy(error = null) }

    private fun startPolling(pending: PendingLink, generation: Long) {
        pollJob = viewModelScope.launch {
            while (true) {
                if (attemptGeneration != generation) return@launch
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
                val result = authRepository.pollLink(pending)
                if (attemptGeneration != generation) return@launch
                when (result) {
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
        cancelAttempt()
        super.onCleared()
    }

    private fun cancelAttempt(): Long {
        attemptGeneration++
        startJob?.cancel()
        pollJob?.cancel()
        return attemptGeneration
    }

    private companion object {
        const val POLL_INTERVAL_MILLIS = 2_000L
    }
}
