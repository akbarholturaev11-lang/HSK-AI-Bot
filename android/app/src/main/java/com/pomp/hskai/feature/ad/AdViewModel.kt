package com.pomp.hskai.feature.ad

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.pomp.hskai.BuildConfig
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.core.network.MediaUrl
import com.pomp.hskai.data.api.AndroidAdDto
import com.pomp.hskai.data.repository.FeatureRepository
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

data class AdUiState(
    val isLoading: Boolean = true,
    val ad: AndroidAdDto? = null,
    /** Absolute, origin-checked media URL. Null means there is nothing to play. */
    val mediaUrl: String? = null,
    val requiredSeconds: Int = AdWatch.DEFAULT_SECONDS,
    val elapsedSeconds: Int = 0,
    val isFinishing: Boolean = false,
    /** The section is open; the caller may start the session. */
    val unlocked: Boolean = false,
    /** No ad to show. An ordinary outcome, not a failure. */
    val unavailable: Boolean = false,
    val error: ApiError? = null,
) {
    val canContinue: Boolean get() = AdWatch.canContinue(elapsedSeconds, requiredSeconds)
    val remainingSeconds: Int get() = AdWatch.remainingSeconds(elapsedSeconds, requiredSeconds)
    val progress: Float get() = AdWatch.progress(elapsedSeconds, requiredSeconds)
}

/**
 * Drives one ad: fetch, open an attempt, count the watch, report it.
 *
 * Nothing here decides that the section may open. The server measures the
 * real time between the attempt and the report and answers; this only asks.
 *
 * @param accessRef ties the ad to the session it will unlock. The same value
 *   must be handed to whatever starts that session.
 */
class AdViewModel(
    private val repository: FeatureRepository,
    private val feature: String,
    private val accessRef: String,
    private val slot: String = "practice",
    private val lessonOrder: Int = 0,
) : ViewModel() {

    private val _state = MutableStateFlow(AdUiState())
    val state: StateFlow<AdUiState> = _state.asStateFlow()

    private var ticker: Job? = null

    // The attempt this watch belongs to. Held from the moment the attempt is
    // opened, not when the countdown ends: the learner can only press
    // "continue" after the countdown, but the token must never depend on the
    // ticker having finished its last loop.
    private var attemptToken: String = ""
    private var attemptAdId: Int = 0

    init {
        load()
    }

    fun load() {
        ticker?.cancel()
        attemptToken = ""
        attemptAdId = 0
        _state.value = AdUiState()
        viewModelScope.launch {
            val listing = when (val result = repository.ads(slot)) {
                is ApiResult.Failure -> {
                    // A missing ad is not a broken screen: the caller simply
                    // has nothing to offer and says so.
                    _state.update { it.copy(isLoading = false, unavailable = true) }
                    return@launch
                }

                is ApiResult.Success -> result.value
            }
            val playable = listing.ads.firstNotNullOfOrNull { ad ->
                MediaUrl.resolve(ad.mediaUrl, BuildConfig.API_ORIGIN)?.let { ad to it }
            }
            if (playable == null) {
                _state.update { it.copy(isLoading = false, unavailable = true) }
                return@launch
            }
            val (ad, mediaUrl) = playable

            when (val opened = repository.startAdAttempt(
                adId = ad.id,
                feature = feature,
                accessRef = accessRef,
                lessonOrder = lessonOrder,
            )) {
                is ApiResult.Failure -> _state.update {
                    it.copy(isLoading = false, error = opened.error)
                }

                is ApiResult.Success -> {
                    attemptToken = opened.value.attemptToken
                    attemptAdId = ad.id
                    _state.update {
                        it.copy(
                            isLoading = false,
                            ad = ad,
                            mediaUrl = mediaUrl,
                            requiredSeconds = AdWatch.requiredSeconds(
                                fromAttempt = opened.value.requiredSeconds,
                                fromCreative = ad.durationSeconds,
                            ),
                        )
                    }
                    startTicker()
                }
            }
        }
    }

    /**
     * Counts the watch from the moment the attempt was opened, which is the
     * same moment the server started measuring.
     */
    private fun startTicker() {
        ticker?.cancel()
        ticker = viewModelScope.launch {
            while (isActive && !_state.value.canContinue) {
                delay(1_000)
                _state.update { it.copy(elapsedSeconds = it.elapsedSeconds + 1) }
            }
        }
    }

    /** Reports the watch. The server decides whether the section opens. */
    fun onContinue() {
        val current = _state.value
        if (!current.canContinue || current.isFinishing) return
        _state.update { it.copy(isFinishing = true, error = null) }
        viewModelScope.launch {
            val result = repository.recordAdView(
                adId = attemptAdId,
                watchedSeconds = current.elapsedSeconds,
                feature = feature,
                accessRef = accessRef,
                attemptToken = attemptToken,
                lessonOrder = lessonOrder,
            )
            when (result) {
                is ApiResult.Failure -> _state.update {
                    it.copy(isFinishing = false, error = result.error)
                }

                is ApiResult.Success -> _state.update {
                    it.copy(
                        isFinishing = false,
                        // The server may still refuse — an ad closed early,
                        // an attempt that expired. Then nothing is unlocked
                        // and the learner watches again.
                        unlocked = result.value.ok &&
                            result.value.authorization?.recorded == true,
                        error = if (result.value.ok) null else it.error,
                    )
                }
            }
        }
    }

    override fun onCleared() {
        ticker?.cancel()
        super.onCleared()
    }

    class Factory(
        private val repository: FeatureRepository,
        private val feature: String,
        private val accessRef: String,
        private val slot: String = "practice",
        private val lessonOrder: Int = 0,
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            AdViewModel(repository, feature, accessRef, slot, lessonOrder) as T
    }
}
