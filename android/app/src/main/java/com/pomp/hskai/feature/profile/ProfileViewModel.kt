package com.pomp.hskai.feature.profile

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.AndroidProfileResponse
import com.pomp.hskai.data.api.AndroidSubscriptionOverviewResponse
import com.pomp.hskai.data.api.RatingResponse
import com.pomp.hskai.data.api.ReferralOverviewResponse
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
    val rating: RatingResponse? = null,
    val referral: ReferralOverviewResponse? = null,
    val subscription: AndroidSubscriptionOverviewResponse? = null,
    val error: ApiError? = null,
)

class ProfileViewModel(
    private val repository: FeatureRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(ProfileUiState())
    val state: StateFlow<ProfileUiState> = _state.asStateFlow()

    init {
        load()
    }

    fun load() {
        _state.update { it.copy(isLoading = true, error = null) }
        viewModelScope.launch {
            val profile = async { repository.profile() }
            val rating = async { repository.rating() }
            val referral = async { repository.referral() }
            val subscription = async { repository.subscriptionOverview() }

            val profileResult = profile.await()
            val ratingResult = rating.await()
            val referralResult = referral.await()
            val subscriptionResult = subscription.await()

            val firstError = listOf(
                profileResult,
                ratingResult,
                referralResult,
                subscriptionResult,
            ).filterIsInstance<ApiResult.Failure>().firstOrNull()?.error

            _state.value = ProfileUiState(
                isLoading = false,
                profile = (profileResult as? ApiResult.Success)?.value,
                rating = (ratingResult as? ApiResult.Success)?.value,
                referral = (referralResult as? ApiResult.Success)?.value,
                subscription = (subscriptionResult as? ApiResult.Success)?.value,
                error = firstError,
            )
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
