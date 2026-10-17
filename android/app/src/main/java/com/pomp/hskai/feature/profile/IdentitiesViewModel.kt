package com.pomp.hskai.feature.profile

import android.app.Activity
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.pomp.hskai.core.auth.AuthProvider
import com.pomp.hskai.core.auth.AuthRepository
import com.pomp.hskai.core.auth.LinkedIdentity
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

data class IdentitiesUiState(
    val isLoading: Boolean = false,
    val telegramLinked: Boolean = false,
    val identities: List<LinkedIdentity> = emptyList(),
    val available: List<AuthProvider> = emptyList(),
    val busyProvider: AuthProvider? = null,
    val pendingBrowserUrl: String? = null,
    val telegramApprovalUrl: String? = null,
    val sessionsRevoked: Int? = null,
    val error: ApiError? = null,
) {
    val canUnlinkProvider: Boolean get() = !isLoading && (telegramLinked || identities.size > 1)
}

/**
 * Manages the sign-in methods attached to the current account.
 *
 * Linking here is the deliberately safe path: it runs inside an already
 * authenticated session and can only ever attach a provider to *this* account,
 * never create one and never sign anyone in. The server enforces that; this
 * screen simply never has a way to ask for anything else.
 */
class IdentitiesViewModel(
    private val authRepository: AuthRepository,
    private val onLinked: () -> Unit = {},
    private val now: () -> Long = System::currentTimeMillis,
) : ViewModel() {

    private val _state = MutableStateFlow(IdentitiesUiState())
    val state: StateFlow<IdentitiesUiState> = _state.asStateFlow()

    private var pollJob: Job? = null
    private var refreshGeneration = 0L
    private var operationGeneration = 0L
    private var pendingLink: PendingLink? = null

    fun refresh() {
        cancelConnection()
        val generation = ++refreshGeneration
        _state.update { it.copy(isLoading = true, error = null, sessionsRevoked = null) }
        viewModelScope.launch {
            val available = authRepository.availableProviders()
            val result = authRepository.linkedIdentities()
            if (refreshGeneration != generation) return@launch
            when (result) {
                is ApiResult.Failure -> _state.update {
                    it.copy(isLoading = false, available = available, error = result.error)
                }

                is ApiResult.Success -> _state.update {
                    it.copy(
                        isLoading = false,
                        identities = result.value.identities,
                        telegramLinked = result.value.telegramLinked,
                        available = available,
                    )
                }
            }
        }
    }

    fun connect(provider: AuthProvider, activity: Activity?) {
        val current = _state.value
        if (current.busyProvider != null || current.isLoading) return
        if (provider == AuthProvider.TELEGRAM && current.telegramLinked) return
        if (provider != AuthProvider.TELEGRAM && provider !in current.available) return
        val generation = ++operationGeneration
        refreshGeneration++
        pollJob?.cancel()
        _state.update { it.copy(busyProvider = provider, error = null, sessionsRevoked = null) }
        // Keep a start request alive after dismissal long enough to cancel a
        // proof returned by a late response. Its generation cannot update UI.
        viewModelScope.launch {
            val started = when (provider) {
                AuthProvider.GOOGLE -> authRepository.startGoogleSignIn(
                    activity = activity,
                    bindToCurrentAccount = true,
                )
                AuthProvider.APPLE -> authRepository.startAppleSignIn(bindToCurrentAccount = true)
                AuthProvider.TELEGRAM -> authRepository.startTelegramIdentityLink()
            }
            if (generation != operationGeneration) {
                if (started is ApiResult.Success) cancelPendingTelegram(started.value)
                return@launch
            }
            when (started) {
                is ApiResult.Failure -> _state.update {
                    it.copy(
                        busyProvider = null,
                        error = started.error.takeIf { error -> error !is ApiError.ProviderCancelled },
                    )
                }
                is ApiResult.Success -> {
                    val pending = started.value
                    pendingLink = pending
                    _state.update {
                        it.copy(
                            pendingBrowserUrl = pending.authorizeUrl.ifEmpty { null },
                            telegramApprovalUrl = pending.authorizeUrl.takeIf { provider == AuthProvider.TELEGRAM },
                        )
                    }
                    startPolling(pending, generation)
                }
            }
        }
    }

    fun browserUrlOpened() = _state.update { it.copy(pendingBrowserUrl = null) }

    fun reopenTelegram() {
        if (_state.value.busyProvider == AuthProvider.TELEGRAM) {
            _state.update { it.copy(pendingBrowserUrl = it.telegramApprovalUrl) }
        }
    }

    /** Closing the sheet cannot leave an invisible proof polling or reopen Telegram later. */
    fun cancelConnection() {
        operationGeneration++
        refreshGeneration++
        pollJob?.cancel()
        pollJob = null
        val abandoned = pendingLink
        pendingLink = null
        _state.update {
            it.copy(busyProvider = null, pendingBrowserUrl = null, telegramApprovalUrl = null, isLoading = false)
        }
        if (abandoned != null) viewModelScope.launch { cancelPendingTelegram(abandoned) }
    }

    private suspend fun cancelPendingTelegram(pending: PendingLink) {
        if (pending.provider == AuthProvider.TELEGRAM) authRepository.cancelIdentityLink(pending)
    }

    fun dismissError() = _state.update { it.copy(error = null, sessionsRevoked = null) }

    private fun finishConnection(error: ApiError? = null) {
        pendingLink = null
        _state.update {
            it.copy(busyProvider = null, pendingBrowserUrl = null, telegramApprovalUrl = null, error = error)
        }
    }

    private fun startPolling(pending: PendingLink, generation: Long) {
        pollJob = viewModelScope.launch {
            repeat(MAX_POLLS) {
                if (generation != operationGeneration) return@launch
                if (now() >= pending.expiresAtMillis) {
                    finishConnection(ApiError.fromCode("desktop_link_expired"))
                    return@launch
                }
                val result = authRepository.pollIdentityLink(pending)
                if (generation != operationGeneration) return@launch
                when (result) {
                    is ApiResult.Success -> when (result.value) {
                        "linked" -> {
                            finishConnection()
                            onLinked()
                            // End this poll before refresh cancels its job.
                            pollJob = null
                            refresh()
                            return@launch
                        }
                        "expired" -> {
                            finishConnection(ApiError.fromCode("desktop_link_expired"))
                            return@launch
                        }
                        "denied" -> {
                            finishConnection(ApiError.fromCode("oauth_cancelled"))
                            return@launch
                        }
                    }
                    is ApiResult.Failure -> {
                        val transient = result.error is ApiError.Offline || result.error is ApiError.Timeout
                        if (!transient) {
                            finishConnection(result.error)
                            return@launch
                        }
                    }
                }
                delay(POLL_INTERVAL_MILLIS)
            }
            if (generation == operationGeneration) finishConnection(ApiError.fromCode("desktop_link_expired"))
        }
    }

    fun disconnect(identityId: String) {
        if (_state.value.busyProvider != null || _state.value.isLoading) return
        if (!_state.value.canUnlinkProvider) {
            _state.update { it.copy(error = ApiError.fromCode("oauth_last_identity")) }
            return
        }
        val provider = _state.value.identities.firstOrNull { it.id == identityId }?.provider ?: return
        val generation = ++operationGeneration
        _state.update { it.copy(busyProvider = provider, error = null, sessionsRevoked = null) }
        viewModelScope.launch {
            val result = authRepository.unlinkIdentity(identityId)
            if (generation != operationGeneration) return@launch
            when (result) {
                is ApiResult.Failure -> _state.update { it.copy(busyProvider = null, error = result.error) }
                is ApiResult.Success -> {
                    _state.update { it.copy(busyProvider = null, sessionsRevoked = result.value) }
                    refresh()
                }
            }
        }
    }

    override fun onCleared() {
        operationGeneration++
        refreshGeneration++
        pollJob?.cancel()
        super.onCleared()
    }

    private companion object {
        const val POLL_INTERVAL_MILLIS = 2_000L
        // The link request itself expires server-side; this only stops the
        // client from polling forever if the user abandons the browser tab.
        const val MAX_POLLS = 300
    }
}

class IdentitiesViewModelFactory(
    private val authRepository: AuthRepository,
    private val onLinked: () -> Unit = {},
) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T =
        IdentitiesViewModel(authRepository, onLinked = onLinked) as T
}
