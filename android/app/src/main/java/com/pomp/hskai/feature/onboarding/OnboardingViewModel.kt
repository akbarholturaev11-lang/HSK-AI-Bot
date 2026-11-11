package com.pomp.hskai.feature.onboarding

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.AndroidOnboardingCompleteDto
import com.pomp.hskai.data.api.AndroidOnboardingStatusDto
import java.io.IOException
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

/** Welcome -> course version -> level -> goal, matching the Mini App flow. */
internal class OnboardingViewModel(
    private val repository: OnboardingRepository,
    private val language: String,
    private val guestPreview: AndroidOnboardingStatusDto? = null,
    initialDraft: GuestLiDraft? = null,
    private val onGuestReady: (suspend (GuestLiDraft) -> Unit)? = null,
    private val claimGuestDraft: (suspend () -> GuestLiDraft?)? = null,
) : ViewModel() {

    private val _state = MutableStateFlow(OnboardingFlowState())
    val state: StateFlow<OnboardingFlowState> = _state.asStateFlow()
    private var statusGeneration = 0L

    private var checkedGuestDraft = false
    private var claimingGuestDraft = false

    init {
        if (guestPreview == null) loadStatus()
        else _state.update { initial ->
            val state = initial.withStatus(guestPreview)
            val preview = state.ui.copy(selectedTrack = "hsk20", selectedLevel = "beginner")
            val restored = initialDraft?.takeIf {
                it.track != "hsk30" || (preview.hsk30Enabled && it.level in preview.hsk30LiveLevels)
            }
            state.copy(ui = restored?.applyTo(preview)?.copy(step = 7) ?: preview)
        }
    }

    /** Refresh behind the current screen after connectivity changes. */
    fun loadStatus(showSplash: Boolean = true) {
        if (guestPreview != null || _state.value.ui.submitting || claimingGuestDraft) return
        val generation = ++statusGeneration
        val claim = if (checkedGuestDraft) null else claimGuestDraft
        claimingGuestDraft = claim != null
        if (showSplash) _state.update { it.copy(loading = true, error = null) }
        viewModelScope.launch {
            val (result, verified) = try {
                repository.statusWithDraft(claim)
            } finally {
                claimingGuestDraft = false
            }
            if (generation != statusGeneration) return@launch
            when (result) {
                is ApiResult.Success -> {
                    val status = result.value
                    checkedGuestDraft = status.ok
                    _state.update { it.withStatus(status) }
                    if (verified != null && status.ok && status.liEnabled && !status.completed) {
                        val draft = verified.draft
                        val trackAllowed = draft.track != "hsk30" ||
                            (status.hsk30.allowed && status.hsk30.enabled && draft.level in status.hsk30.liveLevels)
                        _state.update { state ->
                            val restored = draft.applyTo(state.ui)
                            state.copy(ui = if (trackAllowed) restored.copy(step = 7)
                                else restored.copy(step = 1, selectedTrack = "hsk20", selectedLevel = "beginner"))
                        }
                        if (trackAllowed) submit(verified.token)
                    }
                }
                is ApiResult.Failure -> _state.update {
                    it.copy(loading = false, error = result.error)
                }
            }
        }
    }

    private fun OnboardingFlowState.withStatus(status: AndroidOnboardingStatusDto): OnboardingFlowState {
        val liveHsk30Levels = status.hsk30.liveLevels.filter { it in HSK30_LEVELS }
        val hasLiveHsk30 = status.hsk30.enabled && liveHsk30Levels.isNotEmpty()
        val serverLevel = normalizeLevel(status.level)
        val selectedTrack = when {
            hasLiveHsk30 && serverLevel in HSK30_LEVELS -> "hsk30"
            !status.completed && hasLiveHsk30 -> "hsk30"
            else -> "hsk20"
        }
        val selectedLevel = when {
            selectedTrack == "hsk30" && serverLevel in liveHsk30Levels -> serverLevel
            selectedTrack == "hsk30" -> liveHsk30Levels.first()
            serverLevel in HSK20_LEVELS -> serverLevel
            else -> "beginner"
        }
        return copy(
            loading = false,
            completed = status.ok && status.completed,
            ui = ui.copy(
                liEnabled = status.liEnabled,
                step = if (status.liEnabled) ui.step else ui.step.coerceAtMost(3),
                selectedGoals = status.profile.goals.filter(::validGoal).ifEmpty { listOf(status.profile.goal.takeIf(::validGoal) ?: "hsk_exam") },
                dailyMinutes = status.profile.dailyMinutes.takeIf { it in setOf(5, 10, 15, 20, 30) } ?: 10,
                preferredFocus = status.profile.preferredFocus ?: "none",
                streakTargetDays = status.profile.streakTargetDays ?: 7,
                selectedTrack = selectedTrack,
                selectedLevel = selectedLevel,
                selectedGoal = status.profile.goal.takeIf(::validGoal) ?: "hsk_exam",
                hsk30Enabled = hasLiveHsk30,
                hsk30Allowed = status.hsk30.allowed,
                hsk30LiveLevels = liveHsk30Levels.ifEmpty { listOf("nhsk1") },
                hsk30IsNew = status.hsk30.newBadge.isNew,
                hsk30PaymentEnabled = status.hsk30.paymentEnabled,
                hsk30PriceTjs = status.hsk30.priceTjs.coerceAtLeast(0),
                hsk30PriceDisplay = status.hsk30.priceDisplay,
            ),
            error = if (status.ok) null else ApiError.Unknown,
        )
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
        _state.update {
            val goals = if (!it.ui.liEnabled) listOf(goal) else when {
                goal !in it.ui.selectedGoals -> it.ui.selectedGoals + goal
                it.ui.selectedGoals.size > 1 -> it.ui.selectedGoals - goal
                else -> it.ui.selectedGoals
            }
            it.copy(ui = it.ui.copy(selectedGoal = goals.first(), selectedGoals = goals, error = false))
        }
    }

    fun back() {
        if (_state.value.ui.submitting || _state.value.launch != null) return
        _state.update {
            it.copy(ui = it.ui.copy(step = (it.ui.step - 1).coerceAtLeast(0), error = false))
        }
    }

    fun next() {
        val current = _state.value
        if (current.completed || current.ui.submitting || current.launch != null) return
        if (current.ui.step < if (current.ui.liEnabled) 7 else 3) {
            _state.update { it.copy(ui = it.ui.copy(step = it.ui.step + 1, error = false)) }
            return
        }
        submit()
    }

    fun selectDailyMinutes(value: Int) {
        if (!_state.value.ui.submitting && value in setOf(5, 10, 15, 20, 30))
            _state.update { it.copy(ui = it.ui.copy(dailyMinutes = value)) }
    }

    fun selectFocus(value: String) {
        if (!_state.value.ui.submitting && value in setOf("speaking", "listening", "vocabulary", "grammar", "none"))
            _state.update { it.copy(ui = it.ui.copy(preferredFocus = value)) }
    }

    fun selectStreak(value: Int) {
        if (!_state.value.ui.submitting && value in setOf(7, 14, 30, 50))
            _state.update { it.copy(ui = it.ui.copy(streakTargetDays = value)) }
    }

    fun finishIntro() {
        if (_state.value.launch?.ok == true) _state.update { it.copy(completed = true) }
    }

    private fun submit(guestResumeToken: String? = null) {
        statusGeneration++
        val current = _state.value.ui
        _state.update { it.copy(error = null, ui = current.copy(submitting = true, error = false)) }
        viewModelScope.launch {
            if (guestPreview != null) {
                try {
                    onGuestReady?.invoke(GuestLiDraft.from(current))
                    _state.update { it.copy(ui = it.ui.copy(submitting = false)) }
                } catch (_: IOException) {
                    _state.update { it.copy(ui = it.ui.copy(submitting = false, error = true)) }
                }
                return@launch
            }
            when (
                val result = repository.complete(
                    level = current.selectedLevel,
                    goal = current.selectedGoal,
                    language = language,
                    dailyMinutes = current.dailyMinutes,
                    goals = current.selectedGoals.takeIf { current.liEnabled },
                    streakTargetDays = current.streakTargetDays.takeIf { current.liEnabled },
                    preferredFocus = current.preferredFocus.takeIf { current.liEnabled },
                    guestResumeToken = guestResumeToken,
                )
            ) {
                is ApiResult.Success -> {
                    val launch = result.value
                    if (launch.ok) {
                        _state.update {
                            it.copy(
                                completed = !current.liEnabled,
                                launch = launch,
                                error = null,
                                ui = it.ui.copy(submitting = false, error = false, step = if (current.liEnabled) 8 else it.ui.step),
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
                is ApiResult.Failure -> {
                    _state.update {
                        it.copy(error = result.error, ui = it.ui.copy(submitting = false, error = true))
                    }
                    when ((result.error as? ApiError.Server)?.code) {
                        "android_li_onboarding_disabled" -> loadStatus(showSplash = false)
                        "android_li_guest_not_fresh" -> {
                            _state.update { it.copy(ui = it.ui.copy(step = 0, error = false)) }
                            loadStatus(showSplash = false)
                        }
                        "android_li_guest_track_locked" -> _state.update {
                            it.copy(ui = it.ui.copy(step = 1, selectedTrack = "hsk20", selectedLevel = "beginner"))
                        }
                    }
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
        private val guestPreview: AndroidOnboardingStatusDto? = null,
        private val initialDraft: GuestLiDraft? = null,
        private val onGuestReady: (suspend (GuestLiDraft) -> Unit)? = null,
        private val claimGuestDraft: (suspend () -> GuestLiDraft?)? = null,
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            OnboardingViewModel(repository, language, guestPreview, initialDraft, onGuestReady, claimGuestDraft) as T
    }

    private companion object {
        val TRACKS = setOf("hsk20", "hsk30")
        val HSK20_LEVELS = setOf("beginner", "hsk1", "hsk2", "hsk3", "hsk4")
        val HSK30_LEVELS = setOf("nhsk1", "nhsk2", "nhsk3")
        val LEVELS = HSK20_LEVELS + HSK30_LEVELS
        val GOALS = setOf("hsk_exam", "study_china", "work_china", "daily_communication", "travel")
    }
}
