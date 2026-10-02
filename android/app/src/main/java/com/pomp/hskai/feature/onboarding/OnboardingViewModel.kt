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

    /**
     * [showSplash] false re-reads the status behind the screen already shown,
     * for a connection that has just come back: the splash would blink over
     * the app the learner is using, and the last error stays until the
     * answer replaces it.
     */
    fun loadStatus(showSplash: Boolean = true) {
        if (showSplash) _state.update { it.copy(loading = true, error = null) }
        viewModelScope.launch {
            when (val result = repository.status()) {
                is ApiResult.Success -> {
                    val status = result.value
                    _state.update {
                        it.copy(
                            loading = false,
                            completed = status.ok && status.completed,
                            ui = it.ui.copy(
                                selectedTrack = if (status.level.lowercase().startsWith("nhsk")) "hsk30" else it.ui.selectedTrack,
                                selectedLevel = normalizeLevel(status.level),
                                selectedGoal = status.profile.goal.takeIf(::validGoal) ?: "hsk_exam",
                                hsk30Enabled = status.hsk30.enabled,
                                hsk30Allowed = status.hsk30.allowed,
                                hsk30LiveLevels = status.hsk30.liveLevels.filter { level -> level in HSK30_LEVELS }
                                    .ifEmpty { listOf("nhsk1") },
                                hsk30IsNew = status.hsk30.newBadge.isNew,
                                hsk30PaymentEnabled = status.hsk30.paymentEnabled,
                                hsk30PriceTjs = status.hsk30.priceTjs.coerceAtLeast(0),
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

    fun selectTrack(track: String) {
        val current = _state.value.ui
        if (current.submitting || track !in TRACKS) return
        if (track == "hsk30" && !current.hsk30Enabled) return
        val levels = if (track == "hsk30") current.hsk30LiveLevels else HSK20_LEVELS.toList()
        val selected = current.selectedLevel.takeIf { it in levels }
            ?: if (track == "hsk30") levels.firstOrNull().orEmpty().ifBlank { "nhsk1" }
            else "beginner"
        _state.update {
            it.copy(ui = it.ui.copy(
                selectedTrack = track,
                selectedLevel = selected,
                error = false,
            ))
        }
    }

    fun selectLevel(level: String) {
        val current = _state.value.ui
        val allowed = if (current.selectedTrack == "hsk30") current.hsk30LiveLevels else HSK20_LEVELS
        if (current.submitting || level !in allowed) return
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
        if (current.ui.step >= 2 && current.ui.needsHsk30Unlock) return
        if (current.ui.step < 2) {
            _state.update { it.copy(ui = it.ui.copy(step = it.ui.step + 1, error = false)) }
            return
        }
        submit()
    }

    fun startWithHsk20() {
        val current = _state.value.ui
        if (current.submitting || current.step < 2 || !current.needsHsk30Unlock) return
        val fallbackLevel = when (current.selectedLevel) {
            "nhsk1" -> "hsk2"
            "nhsk2" -> "hsk3"
            "nhsk3" -> "hsk4"
            else -> "hsk1"
        }
        _state.update {
            it.copy(
                ui = it.ui.copy(
                    selectedTrack = "hsk20",
                    selectedLevel = fallbackLevel,
                    error = false,
                ),
            )
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
        return if (normalized in LEVELS) normalized else "beginner"
    }

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
        val TRACKS = setOf("hsk20", "hsk30")
        val HSK20_LEVELS = setOf("beginner", "hsk1", "hsk2", "hsk3", "hsk4")
        val HSK30_LEVELS = setOf("nhsk1", "nhsk2", "nhsk3")
        val LEVELS = HSK20_LEVELS + HSK30_LEVELS
        val GOALS = setOf("hsk_exam", "study_china", "work_china", "daily_communication", "travel")
    }
}
