package com.pomp.hskai.feature.profile

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.AndroidProfileResponse
import com.pomp.hskai.data.api.AndroidTrialDto
import com.pomp.hskai.data.repository.FeatureRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ProfileUiState(
    val isLoading: Boolean = true,
    val profile: AndroidProfileResponse? = null,
    /** Serverning javobi: bu odam 7 kunlik bepul Pro ola oladimi. */
    val trial: AndroidTrialDto? = null,
    /** Trial boshlanayotgan lahza — tugma ikki marta bosilmasin. */
    val trialStarting: Boolean = false,
    /** Server rad etsa sababi. Jimgina "hech narsa bo'lmadi" eng yomon variant. */
    val trialError: String = "",
    val profileSaving: Boolean = false,
    val profileRevision: Int = 0,
    val error: ApiError? = null,
)

class ProfileViewModel(
    private val repository: FeatureRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(ProfileUiState())
    val state: StateFlow<ProfileUiState> = _state.asStateFlow()
    private var loadGeneration = 0L

    init {
        load()
    }

    fun load() {
        val generation = ++loadGeneration
        _state.update { it.copy(isLoading = true, error = null) }
        viewModelScope.launch {
            val profile = async { repository.profile() }
            val trial = async { repository.trialStatus() }

            val profileResult = profile.await()
            val trialResult = trial.await()
            if (generation != loadGeneration) return@launch

            // Trial is an optional offer. A trial-status failure must not turn
            // a perfectly usable profile into an error screen.
            val firstError = (profileResult as? ApiResult.Failure)?.error

            _state.update {
                it.copy(
                    isLoading = false,
                    profile = (profileResult as? ApiResult.Success)?.value ?: it.profile,
                    trial = (trialResult as? ApiResult.Success)?.value?.trial ?: it.trial,
                    error = firstError,
                )
            }
        }
    }

    fun saveProfile(displayName: String, avatarKey: String) {
        if (_state.value.profileSaving) return
        val generation = loadGeneration
        _state.update { it.copy(profileSaving = true, error = null) }
        viewModelScope.launch {
            when (val result = repository.updateProfile(displayName, avatarKey)) {
                is ApiResult.Success -> {
                    // A read started before the save cannot undo the canonical
                    // profile returned by this completed mutation.
                    val refreshedDuringSave = generation != loadGeneration
                    loadGeneration++
                    _state.update {
                        it.copy(
                            isLoading = false,
                            // A newer course/access read may already be on
                            // screen. An older save response must not undo it.
                            profile = if (refreshedDuringSave) it.profile else result.value,
                            profileSaving = false,
                            profileRevision = it.profileRevision + 1,
                        )
                    }
                    if (refreshedDuringSave) load()
                }
                is ApiResult.Failure -> {
                    val refreshedDuringSave = generation != loadGeneration
                    // Only invalidate reads that preceded this save. A newer
                    // access refresh must still be allowed to finish.
                    if (!refreshedDuringSave) loadGeneration++
                    _state.update {
                        it.copy(
                            isLoading = if (refreshedDuringSave) it.isLoading else false,
                            profileSaving = false,
                            error = result.error,
                        )
                    }
                }
            }
        }
    }

    /**
     * 7 kunlik bepul Pro. Muvaffaqiyatda profil qayta yuklanadi, chunki obuna
     * holati ham, limitlar ham o'zgargan bo'ladi.
     */
    fun startTrial() {
        if (_state.value.trialStarting) return
        _state.update { it.copy(trialStarting = true, trialError = "") }
        viewModelScope.launch {
            when (val result = repository.trialStart()) {
                is ApiResult.Success ->
                    if (result.value.ok) {
                        _state.update { it.copy(trialStarting = false) }
                        load()
                    } else {
                        _state.update {
                            it.copy(trialStarting = false, trialError = result.value.error)
                        }
                    }

                is ApiResult.Failure ->
                    _state.update {
                        it.copy(trialStarting = false, trialError = result.error.toString())
                    }
            }
        }
    }

    class Factory(
        private val repository: FeatureRepository,
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            ProfileViewModel(repository) as T
    }
}
