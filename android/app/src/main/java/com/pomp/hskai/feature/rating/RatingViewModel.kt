package com.pomp.hskai.feature.rating

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.RatingResponse
import com.pomp.hskai.data.api.ReferralOverviewResponse
import com.pomp.hskai.data.repository.FeatureRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/** The two lists the Mini App's Reyting tab switches between. */
enum class RatingTab { LEAGUE, FRIENDS }

data class RatingUiState(
    val isLoading: Boolean = true,
    val tab: RatingTab = RatingTab.LEAGUE,
    val rating: RatingResponse? = null,
    val referral: ReferralOverviewResponse? = null,
    val error: ApiError? = null,
)

class RatingViewModel(
    private val repository: FeatureRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(RatingUiState())
    val state: StateFlow<RatingUiState> = _state.asStateFlow()

    init {
        load()
    }

    fun selectTab(tab: RatingTab) {
        _state.update { it.copy(tab = tab) }
    }

    fun load() {
        _state.update { it.copy(isLoading = true, error = null) }
        viewModelScope.launch {
            val rating = async { repository.rating() }
            val referral = async { repository.referral() }

            val ratingResult = rating.await()
            val referralResult = referral.await()

            val firstError = listOf(ratingResult, referralResult)
                .filterIsInstance<ApiResult.Failure>()
                .firstOrNull()
                ?.error

            _state.update {
                it.copy(
                    isLoading = false,
                    rating = (ratingResult as? ApiResult.Success)?.value ?: it.rating,
                    referral = (referralResult as? ApiResult.Success)?.value ?: it.referral,
                    error = firstError,
                )
            }
        }
    }

    class Factory(
        private val repository: FeatureRepository,
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            RatingViewModel(repository) as T
    }
}
