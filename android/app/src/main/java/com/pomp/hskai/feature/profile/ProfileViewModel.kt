package com.pomp.hskai.feature.profile

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.AndroidProfileResponse
import com.pomp.hskai.data.api.AndroidSubscriptionOverviewResponse
import com.pomp.hskai.data.api.AndroidTrialDto
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
    /** Serverning javobi: bu odam 7 kunlik bepul Pro ola oladimi. */
    val trial: AndroidTrialDto? = null,
    /** Trial boshlanayotgan lahza — tugma ikki marta bosilmasin. */
    val trialStarting: Boolean = false,
    /** Server rad etsa sababi. Jimgina "hech narsa bo'lmadi" eng yomon variant. */
    val trialError: String = "",
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
            val trial = async { repository.trialStatus() }

            val profileResult = profile.await()
            val ratingResult = rating.await()
            val referralResult = referral.await()
            val subscriptionResult = subscription.await()
            val trialResult = trial.await()

            val firstError = listOf(
                profileResult,
                ratingResult,
                referralResult,
                subscriptionResult,
                // Trial ATAYLAB ro'yxatda yo'q: u qo'shimcha taklif, va uning
                // yiqilishi butun profilni xato holatiga tushirmasligi kerak.
            ).filterIsInstance<ApiResult.Failure>().firstOrNull()?.error

            _state.value = ProfileUiState(
                isLoading = false,
                profile = (profileResult as? ApiResult.Success)?.value,
                rating = (ratingResult as? ApiResult.Success)?.value,
                referral = (referralResult as? ApiResult.Success)?.value,
                subscription = (subscriptionResult as? ApiResult.Success)?.value,
                trial = (trialResult as? ApiResult.Success)?.value?.trial,
                error = firstError,
            )
        }
    }

    /**
     * 7 kunlik bepul Pro. Muvaffaqiyatda profil qayta yuklanadi, chunki obuna
     * holati ham, limitlar ham o'zgargan bo'ladi.
     */
    fun startTrial() {
        if (_state.value.trialStarting) return
        _state.update { it.copy(trialStarting = true, trialError = "") }
        viewModelScope.launch {
            when (val result = repository.trialStart()) {
                is ApiResult.Success ->
                    if (result.value.ok) {
                        load()
                    } else {
                        _state.update {
                            it.copy(trialStarting = false, trialError = result.value.error)
                        }
                    }

                is ApiResult.Failure ->
                    _state.update {
                        it.copy(trialStarting = false, trialError = result.error.toString())
                    }
            }
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
