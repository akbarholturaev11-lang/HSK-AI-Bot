package com.pomp.hskai.feature.course

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.repository.StudyPreferencesRepository
import com.pomp.hskai.domain.model.CourseStudySetup
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

enum class StudySetupStage { GOAL, TIME, FOCUS }

data class StudySetupUiState(
    val visible: Boolean = false,
    val stage: StudySetupStage = StudySetupStage.TIME,
    val setup: CourseStudySetup? = null,
    val saving: Boolean = false,
    val error: ApiError? = null,
    val refreshVersion: Int = 0,
)

/** Mini App's post-first-lesson goal -> time -> focus flow. */
class StudySetupViewModel(
    private val repository: StudyPreferencesRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(StudySetupUiState())
    val state: StateFlow<StudySetupUiState> = _state.asStateFlow()
    private var dismissedForSession = false
    private var syncGeneration = 0L

    fun sync(server: CourseStudySetup?) {
        val generation = ++syncGeneration
        if (server == null || !server.pending) {
            dismissedForSession = false
            _state.update { it.copy(visible = false, setup = server, error = null) }
            return
        }
        val current = _state.value
        if (dismissedForSession || current.saving) {
            _state.update { it.copy(setup = server) }
            return
        }

        // Once a prompt flow is already open, server refreshes must only refresh
        // its data. Re-checking the 24h guard here would close TIME -> FOCUS.
        if (current.visible) {
            _state.update {
                it.copy(
                    visible = true,
                    stage = stageFor(server, current),
                    setup = server,
                    error = null,
                )
            }
            return
        }

        viewModelScope.launch {
            val lastAskedAtMillis = repository.lastSetupPromptAskedAtMillis()
            if (generation != syncGeneration) return@launch
            val nowMillis = System.currentTimeMillis()
            val coolingDown = lastAskedAtMillis != null &&
                lastAskedAtMillis > 0L &&
                nowMillis - lastAskedAtMillis < SETUP_ASK_GAP_MS
            if (coolingDown || dismissedForSession) {
                _state.update { it.copy(visible = false, setup = server, error = null) }
                return@launch
            }

            // Mini App writes hsk_v3_setup_asked when the question is shown,
            // not only when it is dismissed. Mark first so process death does
            // not immediately show the same interruption again on relaunch.
            repository.markSetupPromptAskedAtMillis(nowMillis)
            if (generation != syncGeneration) return@launch
            val latest = _state.value
            _state.update {
                it.copy(
                    visible = true,
                    stage = stageFor(server, latest),
                    setup = server,
                    error = null,
                )
            }
        }
    }

    fun dismiss() {
        if (_state.value.saving) return
        dismissedForSession = true
        _state.update { it.copy(visible = false, error = null) }
    }

    fun chooseGoal(goal: String) = save(
        request = { repository.setGoal(goal) },
        nextStage = StudySetupStage.TIME,
    )

    fun chooseTime(minutes: Int) = save(
        request = { repository.setDailyMinutes(minutes) },
        nextStage = StudySetupStage.FOCUS,
    )

    fun chooseFocus(focus: String) = save(
        request = { repository.setPreferredFocus(focus) },
        nextStage = null,
    )

    private fun save(
        request: suspend () -> ApiResult<CourseStudySetup>,
        nextStage: StudySetupStage?,
    ) {
        if (_state.value.saving) return
        _state.update { it.copy(saving = true, error = null) }
        viewModelScope.launch {
            when (val result = request()) {
                is ApiResult.Success -> {
                    val done = nextStage == null
                    _state.update {
                        it.copy(
                            visible = !done,
                            stage = nextStage ?: it.stage,
                            setup = result.value,
                            saving = false,
                            error = null,
                            refreshVersion = it.refreshVersion + 1,
                        )
                    }
                }
                is ApiResult.Failure -> _state.update {
                    it.copy(saving = false, error = result.error)
                }
            }
        }
    }

    private fun stageFor(
        server: CourseStudySetup,
        current: StudySetupUiState,
    ): StudySetupStage = when {
        server.pendingGoal || !server.goalChosen -> StudySetupStage.GOAL
        current.visible && current.stage == StudySetupStage.FOCUS -> StudySetupStage.FOCUS
        else -> StudySetupStage.TIME
    }

    class Factory(
        private val repository: StudyPreferencesRepository,
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            StudySetupViewModel(repository) as T
    }

    private companion object {
        const val SETUP_ASK_GAP_MS = 24L * 60L * 60L * 1000L
    }
}
