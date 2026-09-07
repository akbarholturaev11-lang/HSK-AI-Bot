package com.pomp.hskai.feature.onboarding

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.AndroidOnboardingCompleteDto
import com.pomp.hskai.data.repository.OnboardingRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class OnboardingFlowState(
    val loading: Boolean = true,
    val completed: Boolean = false,
    val ui: OnboardingUiState = OnboardingUiState(),
    val error: ApiError? = null,
    val launch: AndroidOnboardingCompleteDto? = null,
)

/** Welcome -> level -> goal, matching the Mini App's two-question flow. */
class OnboardingViewModel(
    private val repository: OnboardingRepository,
    private val language: String,
) : ViewModel() {

    private val _state = MutableStateFlow(OnboardingFlowState())
    val state: StateFlow<OnboardingFlowState> = _state.asStateFlow()

    init {
        loadStatus()
    }

    fun loadStatus() {
        _state.update { it.copy(loading = true, error = null) }
        viewModelScope.launch {
            when (val result = repository.status()) {
                is ApiResult.Success -> {
                    val status = result.value
                    _state.update {
                        it.copy(
                            loading = false,
                            completed = status.ok && status.completed,
                            ui = it.ui.copy(
                                selectedLevel = normalizeLevel(status.level),
                                selectedGoal = status.profile.goal.takeIf(::validGoal) ?: "hsk_exam",
                            ),
                            error = if (status.ok) null else ApiError.Unknown,
                        )
                    }
                }
                is ApiResult.Failure -> _state.update {
                    it.copy(loading = false, error = result.error)
                }
            }
        }
    }

    fun selectLevel(level: String) {
        if (_state.value.ui.submitting || !validLevel(level)) return
        _state.update { it.copy(ui = it.ui.copy(selectedLevel = level, error = false)) }
    }

    fun selectGoal(goal: String) {
        if (_state.value.ui.submitting || !validGoal(goal)) return
        _state.update { it.copy(ui = it.ui.copy(selectedGoal = goal, error = false)) }
    }

    fun back() {
        if (_state.value.ui.submitting) return
        _state.update {
            it.copy(ui = it.ui.copy(step = (it.ui.step - 1).coerceAtLeast(0), error = false))
        }
    }

    fun next() {
        val current = _state.value
        if (current.ui.submitting) return
        if (current.ui.step < 2) {
            _state.update { it.copy(ui = it.ui.copy(step = it.ui.step + 1, error = false)) }
            return
        }
        submit()
    }

    private fun submit() {
        val current = _state.value.ui
        _state.update { it.copy(error = null, ui = current.copy(submitting = true, error = false)) }
        viewModelScope.launch {
            when (
                val result = repository.complete(
                    level = current.selectedLevel,
                    goal = current.selectedGoal,
                    language = language,
                )
            ) {
                is ApiResult.Success -> {
                    val launch = result.value
                    if (launch.ok) {
                        _state.update {
                            it.copy(
                                completed = true,
                                launch = launch,
                                error = null,
                                ui = it.ui.copy(submitting = false, error = false),
                            )
                        }
                    } else {
                        _state.update {
                            it.copy(
                                error = ApiError.Unknown,
                                ui = it.ui.copy(submitting = false, error = true),
                            )
                        }
                    }
                }
                is ApiResult.Failure -> _state.update {
                    it.copy(
                        error = result.error,
                        ui = it.ui.copy(submitting = false, error = true),
                    )
                }
            }
        }
    }

    private fun normalizeLevel(level: String): String {
        val normalized = level.lowercase()
        return if (validLevel(normalized)) normalized else "beginner"
    }

    private fun validLevel(level: String) = level in LEVELS
    private fun validGoal(goal: String) = goal in GOALS

    class Factory(
        private val repository: OnboardingRepository,
        private val language: String,
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            OnboardingViewModel(repository, language) as T
    }

    private companion object {
        val LEVELS = setOf("beginner", "hsk1", "hsk2", "hsk3", "hsk4")
        val GOALS = setOf("hsk_exam", "study_china", "work_china", "daily_communication", "travel")
    }
}
