package com.pomp.hskai.feature.profile

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.pomp.hskai.core.auth.AuthRepository
import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.repository.CourseRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ProfileSettingsState(
    val isSavingLanguage: Boolean = false,
    val isSavingNotifications: Boolean = false,
    val error: ApiError? = null,
) {
    val isBusy: Boolean get() = isSavingLanguage || isSavingNotifications
}

/**
 * The account preferences shared with every other client.
 *
 * Nothing is stored locally: the server owns both flags, so a change made here
 * is the same change the bot, the Mini App and desktop will see. The UI only
 * reflects what came back from the server.
 */
class ProfileSettingsViewModel(
    private val courseRepository: CourseRepository,
    private val authRepository: AuthRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(ProfileSettingsState())
    val state: StateFlow<ProfileSettingsState> = _state.asStateFlow()

    /** Emits when the server state changed and the screens must re-read it. */
    private val _reload = MutableStateFlow(0)
    val reload: StateFlow<Int> = _reload.asStateFlow()

    fun setLanguage(language: AppLanguage) {
        if (_state.value.isSavingLanguage) return
        _state.update { it.copy(isSavingLanguage = true, error = null) }
        viewModelScope.launch {
            when (val result = courseRepository.setLanguage(language)) {
                is ApiResult.Success -> {
                    // The linked account carries the language the rest of the
                    // app reads, so it has to be re-read before anything is
                    // rendered in the new language.
                    authRepository.bootstrap()
                    _state.update { it.copy(isSavingLanguage = false) }
                    _reload.update { it + 1 }
                }

                is ApiResult.Failure -> _state.update {
                    it.copy(isSavingLanguage = false, error = result.error)
                }
            }
        }
    }

    fun setNotifications(enabled: Boolean) {
        if (_state.value.isSavingNotifications) return
        _state.update { it.copy(isSavingNotifications = true, error = null) }
        viewModelScope.launch {
            when (val result = courseRepository.setNotifications(enabled)) {
                is ApiResult.Success -> {
                    _state.update { it.copy(isSavingNotifications = false) }
                    // The toggle's own truth is the course map's notify flag.
                    _reload.update { it + 1 }
                }

                is ApiResult.Failure -> _state.update {
                    it.copy(isSavingNotifications = false, error = result.error)
                }
            }
        }
    }

    fun clearError() {
        _state.update { it.copy(error = null) }
    }

    class Factory(
        private val courseRepository: CourseRepository,
        private val authRepository: AuthRepository,
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            ProfileSettingsViewModel(courseRepository, authRepository) as T
    }
}
