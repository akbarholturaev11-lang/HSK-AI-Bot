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

data class CourseUiState(
    val isLoading: Boolean = true,
    val isRefreshing: Boolean = false,
    val snapshot: CourseMapSnapshot? = null,
    val error: ApiError? = null,
    val isOpeningChest: Boolean = false,
    val chestRewardXp: Int? = null,
    val chestError: ApiError? = null,
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

    init {
        load()
    }

    fun load() {
        if (_state.value.isRefreshing) return
        _state.update {
            it.copy(
                isLoading = it.snapshot == null,
                isRefreshing = true,
                error = null,
            )
        }
        viewModelScope.launch {
            when (val result = repository.courseMap()) {
                is ApiResult.Success -> _state.update {
                    it.copy(
                        isLoading = false,
                        isRefreshing = false,
                        snapshot = result.value,
                        error = null,
                    )
                }

                is ApiResult.Failure -> _state.update {
                    it.copy(
                        isLoading = false,
                        isRefreshing = false,
                        error = result.error,
                    )
                }
            }
        }
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

    class Factory(
        private val repository: CourseRepository,
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            CourseViewModel(repository) as T
    }
}
