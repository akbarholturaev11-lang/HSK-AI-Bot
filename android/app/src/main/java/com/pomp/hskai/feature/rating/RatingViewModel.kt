package com.pomp.hskai.feature.rating

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.data.api.ChallengeDto
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
    /** Duels this learner is part of: waiting on them, or on the other side. */
    val challenges: List<ChallengeDto> = emptyList(),
    val isChallengeBusy: Boolean = false,
    val error: ApiError? = null,
) {
    val pendingChallenges: List<ChallengeDto>
        get() = challenges.filter { it.status == "pending" && it.viewerRole == "opponent" }

    val activeChallenges: List<ChallengeDto>
        get() = challenges.filter { it.status == "accepted" && !it.viewerDone }
}

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
            val duels = async { repository.challenges() }

            val ratingResult = rating.await()
            val referralResult = referral.await()
            val duelResult = duels.await()

            val firstError = listOf(ratingResult, referralResult)
                .filterIsInstance<ApiResult.Failure>()
                .firstOrNull()
                ?.error

            _state.update {
                it.copy(
                    isLoading = false,
                    rating = (ratingResult as? ApiResult.Success)?.value ?: it.rating,
                    referral = (referralResult as? ApiResult.Success)?.value ?: it.referral,
                    // A leaderboard that loads without its duels is still a
                    // leaderboard; only the rating failure is worth reporting.
                    challenges = (duelResult as? ApiResult.Success)?.value?.items
                        ?: it.challenges,
                    error = firstError,
                )
            }
        }
    }

    /** Challenges the learner behind an opaque leaderboard reference. */
    fun challenge(opponentRef: String, level: String, language: String) {
        if (opponentRef.isBlank() || _state.value.isChallengeBusy) return
        _state.update { it.copy(isChallengeBusy = true, error = null) }
        viewModelScope.launch {
            val result = repository.createChallenge(opponentRef, level, language)
            _state.update {
                it.copy(
                    isChallengeBusy = false,
                    error = (result as? ApiResult.Failure)?.error,
                )
            }
            if (result is ApiResult.Success) load()
        }
    }

    fun respond(challengeId: Int, accept: Boolean) {
        if (_state.value.isChallengeBusy) return
        _state.update { it.copy(isChallengeBusy = true, error = null) }
        viewModelScope.launch {
            val result = repository.respondToChallenge(challengeId, accept)
            _state.update {
                it.copy(
                    isChallengeBusy = false,
                    error = (result as? ApiResult.Failure)?.error,
                )
            }
            if (result is ApiResult.Success) load()
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
