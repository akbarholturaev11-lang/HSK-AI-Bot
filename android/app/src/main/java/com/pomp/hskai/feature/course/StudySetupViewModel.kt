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

    fun sync(server: CourseStudySetup?) {
        if (server == null || !server.pending) {
            dismissedForSession = false
            _state.update { it.copy(visible = false, setup = server, error = null) }
            return
        }
        if (dismissedForSession || _state.value.saving) {
            _state.update { it.copy(setup = server) }
            return
        }
        val stage = if (server.pendingGoal || !server.goalChosen) {
            StudySetupStage.GOAL
        } else {
            StudySetupStage.TIME
        }
        _state.update {
            it.copy(
                visible = true,
                stage = stage,
                setup = server,
                error = null,
            )
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

    class Factory(
        private val repository: StudyPreferencesRepository,
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            StudySetupViewModel(repository) as T
    }
}
