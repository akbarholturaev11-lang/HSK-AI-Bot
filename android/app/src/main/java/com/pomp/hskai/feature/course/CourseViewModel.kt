package com.pomp.hskai.feature.course

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.repository.CourseMapSnapshot
import com.pomp.hskai.data.repository.CourseRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

data class CourseUiState(
    val isLoading: Boolean = true,
    val isRefreshing: Boolean = false,
    val snapshot: CourseMapSnapshot? = null,
    val error: ApiError? = null,
    val isOpeningChest: Boolean = false,
    val chestRewardXp: Int? = null,
    val chestError: ApiError? = null,
    val isSwitchingTrack: Boolean = false,
    val trackError: ApiError? = null,
    val isClaimingHsk30Promo: Boolean = false,
    val hsk30PromoVisible: Boolean = false,
    val hasAttemptedHsk30Promo: Boolean = false,
    /** Real server-map LOCKED -> non-LOCKED transition awaiting one reveal. */
    val unlockedLessonOrder: Int? = null,
) {
    val map get() = snapshot?.map
    val isStale get() = snapshot?.isStale == true
}

/** One server course map owns path, daily plan, XP, streak and reward state. */
class CourseViewModel(
    private val repository: CourseRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(CourseUiState())
    val state: StateFlow<CourseUiState> = _state.asStateFlow()
    private val courseMapRefreshMutex = Mutex()

    init {
        load()
    }

    fun load() {
        if (_state.value.isRefreshing || _state.value.isSwitchingTrack) return
        _state.update {
            it.copy(
                isLoading = it.snapshot == null,
                isRefreshing = true,
                error = null,
            )
        }
        viewModelScope.launch { refreshCourseMap() }
    }

    private suspend fun refreshCourseMap(completeTrackSwitch: Boolean = false) {
        courseMapRefreshMutex.withLock {
            _state.update {
                it.copy(
                    isLoading = it.snapshot == null,
                    isRefreshing = true,
                    error = null,
                )
            }
            // Draw the previous map first when there is nothing on screen yet.
            // The refresh below replaces it a moment later; the point is that
            // the learner is looking at their course while it happens instead
            // of at an empty screen.
            if (_state.value.snapshot == null) {
                repository.cachedCourseMap()?.let { cached ->
                    _state.update {
                        if (it.snapshot == null) it.copy(isLoading = false, snapshot = cached) else it
                    }
                }
            }
            when (val result = repository.courseMap()) {
                is ApiResult.Success -> _state.update { current ->
                    val previous = current.snapshot
                    val unlockedOrder = if (
                        previous != null &&
                        !previous.isStale &&
                        !result.value.isStale
                    ) {
                        findNewlyUnlockedLesson(previous.map.lessons, result.value.map.lessons)
                    } else {
                        null
                    }
                    current.copy(
                        isLoading = false,
                        isRefreshing = false,
                        snapshot = result.value,
                        error = null,
                        isSwitchingTrack = if (completeTrackSwitch) false else current.isSwitchingTrack,
                        trackError = if (completeTrackSwitch) null else current.trackError,
                        unlockedLessonOrder = unlockedOrder,
                    )
                }

                is ApiResult.Failure -> _state.update {
                    it.copy(
                        isLoading = false,
                        isRefreshing = false,
                        error = result.error,
                        isSwitchingTrack = if (completeTrackSwitch) false else it.isSwitchingTrack,
                        trackError = if (completeTrackSwitch) result.error else it.trackError,
                    )
                }
            }
        }
    }

    fun switchCourseTrack(targetTrack: String, level: String? = null) {
        val normalized = targetTrack.trim().lowercase()
        if (
            normalized !in setOf("hsk20", "hsk30") ||
            _state.value.isSwitchingTrack
        ) return
        _state.update { it.copy(isSwitchingTrack = true, trackError = null) }
        viewModelScope.launch {
            when (val result = repository.switchCourseTrack(normalized, level)) {
                is ApiResult.Success -> {
                    refreshCourseMap(completeTrackSwitch = true)
                }
                is ApiResult.Failure -> _state.update {
                    it.copy(isSwitchingTrack = false, trackError = result.error)
                }
            }
        }
    }

    fun markHsk30PromoShown() {
        val current = _state.value
        val promo = current.map?.hsk30?.promo ?: return
        if (!promo.eligible || current.isStale || current.isRefreshing ||
            current.isClaimingHsk30Promo || current.hsk30PromoVisible ||
            current.hasAttemptedHsk30Promo
        ) return
        _state.update {
            it.copy(
                isClaimingHsk30Promo = true,
                hasAttemptedHsk30Promo = true,
            )
        }
        viewModelScope.launch {
            when (val result = repository.markHsk30PromoShown()) {
                is ApiResult.Success -> _state.update { state ->
                    val mark = result.value
                    val snapshot = state.snapshot
                    val hsk30 = snapshot?.map?.hsk30
                    state.copy(
                        isClaimingHsk30Promo = false,
                        hsk30PromoVisible = mark.ok && mark.recorded,
                        snapshot = if (mark.ok && snapshot != null && hsk30 != null) {
                            snapshot.copy(
                                map = snapshot.map.copy(
                                    hsk30 = hsk30.copy(
                                        promo = hsk30.promo.copy(
                                            eligible = mark.eligible,
                                            reason = mark.reason,
                                            recommendedLevel = mark.recommendedLevel,
                                            shownCount = mark.shownCount,
                                            maxShows = mark.maxShows,
                                        ),
                                    ),
                                ),
                            )
                        } else snapshot,
                    )
                }
                is ApiResult.Failure -> _state.update { it.copy(isClaimingHsk30Promo = false) }
            }
        }
    }

    fun dismissHsk30Promo() {
        _state.update { it.copy(hsk30PromoVisible = false) }
    }

    fun openRewardChest() {
        val chest = _state.value.map?.progress?.rewardChest ?: return
        if (!chest.ready || _state.value.isStale || _state.value.isOpeningChest) return
        _state.update { it.copy(isOpeningChest = true, chestError = null) }
        viewModelScope.launch {
            when (val result = repository.openRewardChest()) {
                is ApiResult.Success -> {
                    if (result.value.ok) {
                        _state.update {
                            it.copy(
                                isOpeningChest = false,
                                chestRewardXp = result.value.rewardValue.coerceAtLeast(0),
                                chestError = null,
                            )
                        }
                        load()
                    } else {
                        _state.update {
                            it.copy(
                                isOpeningChest = false,
                                chestError = ApiError.Unknown,
                            )
                        }
                    }
                }

                is ApiResult.Failure -> _state.update {
                    it.copy(
                        isOpeningChest = false,
                        chestError = result.error,
                    )
                }
            }
        }
    }

    fun consumeChestReward() {
        _state.update { it.copy(chestRewardXp = null) }
    }

    fun consumeLessonUnlock() {
        _state.update { it.copy(unlockedLessonOrder = null) }
    }

    class Factory(
        private val repository: CourseRepository,
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            CourseViewModel(repository) as T
    }
}

internal fun findNewlyUnlockedLesson(
    previous: List<com.pomp.hskai.domain.model.CourseLesson>,
    current: List<com.pomp.hskai.domain.model.CourseLesson>,
): Int? {
    val oldByOrder = previous.associateBy { it.order }
    return current
        .asSequence()
        .filter { lesson ->
            oldByOrder[lesson.order]?.status == com.pomp.hskai.domain.model.LessonStatus.LOCKED &&
                lesson.status != com.pomp.hskai.domain.model.LessonStatus.LOCKED
        }
        .minByOrNull { it.order }
        ?.order
}
