package com.pomp.hskai.feature.profile

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
    val telegramLinked: Boolean = true,
    val identities: List<LinkedIdentity> = emptyList(),
    val available: List<AuthProvider> = emptyList(),
    val busyProvider: AuthProvider? = null,
    val pendingBrowserUrl: String? = null,
    val sessionsRevoked: Int? = null,
    val error: ApiError? = null,
)

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
) : ViewModel() {

    private val _state = MutableStateFlow(IdentitiesUiState())
    val state: StateFlow<IdentitiesUiState> = _state.asStateFlow()

    private var pollJob: Job? = null

    fun refresh() {
        _state.update { it.copy(isLoading = true, error = null, sessionsRevoked = null) }
        viewModelScope.launch {
            val available = authRepository.availableProviders()
            when (val result = authRepository.linkedIdentities()) {
                is ApiResult.Failure -> _state.update {
                    it.copy(isLoading = false, available = available, error = result.error)
                }

                is ApiResult.Success -> _state.update {
                    it.copy(
                        isLoading = false,
                        identities = result.value,
                        available = available,
                    )
                }
            }
        }
    }

    fun connect(provider: AuthProvider) {
        if (_state.value.busyProvider != null) return
        pollJob?.cancel()
        _state.update { it.copy(busyProvider = provider, error = null, sessionsRevoked = null) }
        viewModelScope.launch {
            val started = when (provider) {
                AuthProvider.GOOGLE -> authRepository.startGoogleSignIn(bindToCurrentAccount = true)
                AuthProvider.APPLE -> authRepository.startAppleSignIn(bindToCurrentAccount = true)
                AuthProvider.TELEGRAM -> return@launch
            }
            when (started) {
                is ApiResult.Failure -> _state.update {
                    it.copy(
                        busyProvider = null,
                        error = started.error.takeIf { error ->
                            error !is ApiError.ProviderCancelled
                        },
                    )
                }

                is ApiResult.Success -> {
                    val pending = started.value
                    _state.update {
                        it.copy(pendingBrowserUrl = pending.authorizeUrl.ifEmpty { null })
                    }
                    startPolling(pending)
                }
            }
        }
    }

    fun browserUrlOpened() = _state.update { it.copy(pendingBrowserUrl = null) }

    fun dismissError() = _state.update { it.copy(error = null, sessionsRevoked = null) }

    private fun startPolling(pending: PendingLink) {
        pollJob = viewModelScope.launch {
            repeat(MAX_POLLS) {
                when (val result = authRepository.pollIdentityLink(pending)) {
                    is ApiResult.Success -> when (result.value) {
                        "linked" -> {
                            _state.update { it.copy(busyProvider = null) }
                            refresh()
                            return@launch
                        }

                        "expired" -> {
                            _state.update {
                                it.copy(busyProvider = null, error = ApiError.Unknown)
                            }
                            return@launch
                        }
                    }

                    is ApiResult.Failure -> {
                        val transient = result.error is ApiError.Offline ||
                            result.error is ApiError.Timeout
                        if (!transient) {
                            _state.update {
                                it.copy(busyProvider = null, error = result.error)
                            }
                            return@launch
                        }
                    }
                }
                delay(POLL_INTERVAL_MILLIS)
            }
            _state.update { it.copy(busyProvider = null) }
        }
    }

    fun disconnect(identityId: String) {
        if (_state.value.busyProvider != null) return
        viewModelScope.launch {
            when (val result = authRepository.unlinkIdentity(identityId)) {
                is ApiResult.Failure -> _state.update { it.copy(error = result.error) }
                is ApiResult.Success -> {
                    _state.update { it.copy(sessionsRevoked = result.value) }
                    refresh()
                }
            }
        }
    }

    override fun onCleared() {
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
) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T =
        IdentitiesViewModel(authRepository) as T
}
