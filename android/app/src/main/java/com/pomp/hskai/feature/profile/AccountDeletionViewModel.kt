package com.pomp.hskai.feature.profile

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.AccountDeletionPrepared
import com.pomp.hskai.data.api.AccountDeletionReceipt
import com.pomp.hskai.data.repository.AccountDeletionRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class AccountDeletionUiState(
    val isOpen: Boolean = false,
    val isPreparing: Boolean = false,
    val isSubmitting: Boolean = false,
    val accountLabel: String? = null,
    val receipt: AccountDeletionReceipt? = null,
    val error: ApiError? = null,
) {
    val canConfirm: Boolean get() = accountLabel != null && !isPreparing && !isSubmitting && receipt == null
}

/** A request is submitted only after the learner explicitly confirms in the app. */
class AccountDeletionViewModel(private val repository: AccountDeletionRepository) : ViewModel() {
    private val _state = MutableStateFlow(AccountDeletionUiState())
    val state: StateFlow<AccountDeletionUiState> = _state.asStateFlow()
    // Keep proof out of UI state, saved state, external links and local persistence.
    private var challenge: AccountDeletionPrepared? = null
    private var generation = 0L

    fun open() {
        if (_state.value.isPreparing || _state.value.isSubmitting) return
        if (_state.value.receipt != null) {
            _state.value = _state.value.copy(isOpen = true)
            return
        }
        val requestedGeneration = ++generation
        challenge = null
        _state.value = AccountDeletionUiState(isOpen = true, isPreparing = true)
        viewModelScope.launch {
            val result = repository.prepare()
            if (generation != requestedGeneration) return@launch
            when (result) {
                is ApiResult.Success -> {
                    challenge = result.value
                    _state.value = AccountDeletionUiState(isOpen = true, accountLabel = result.value.accountLabel)
                }
                is ApiResult.Failure -> _state.value = AccountDeletionUiState(isOpen = true, error = result.error)
            }
        }
    }

    fun confirm() {
        val prepared = challenge ?: return
        if (!_state.value.isOpen || !_state.value.canConfirm) return
        val requestedGeneration = generation
        _state.value = _state.value.copy(isSubmitting = true, error = null)
        viewModelScope.launch {
            val result = repository.confirm(prepared)
            if (generation != requestedGeneration) return@launch
            when (result) {
                is ApiResult.Success -> {
                    challenge = null
                    _state.value = AccountDeletionUiState(isOpen = true, receipt = result.value)
                }
                is ApiResult.Failure -> {
                    val proofExpired = result.error is ApiError.Server && result.error.code in setOf(
                        "deletion_expired", "deletion_invalid", "deletion_verification_required",
                    )
                    if (proofExpired) challenge = null
                    _state.value = _state.value.copy(
                        isSubmitting = false,
                        accountLabel = if (proofExpired) null else _state.value.accountLabel,
                        error = result.error,
                    )
                }
            }
        }
    }

    fun dismiss() {
        if (_state.value.isSubmitting) return
        generation++
        challenge = null
        _state.value = _state.value.copy(isOpen = false, isPreparing = false, accountLabel = null, error = null)
    }

    class Factory(private val repository: AccountDeletionRepository) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T = AccountDeletionViewModel(repository) as T
    }
}
