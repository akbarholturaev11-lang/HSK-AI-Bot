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
    /** The ad is done with; the caller may close the screen. */
    val finished: Boolean = false,
    /** No ad to show. An ordinary outcome, not a failure. */
    val unavailable: Boolean = false,
    val error: ApiError? = null,
) {
    val canContinue: Boolean get() = AdWatch.canContinue(elapsedSeconds, requiredSeconds)
    val remainingSeconds: Int get() = AdWatch.remainingSeconds(elapsedSeconds, requiredSeconds)
    val progress: Float get() = AdWatch.progress(elapsedSeconds, requiredSeconds)
}

/**
 * Drives one ad: fetch it, count the time it was on screen, report that.
 *
 * That is the whole job. There used to be more — an attempt token bound to a
 * section, a server check that the watch was long enough, a section that
 * opened as a result — because an ad was a way past a daily limit. It is not
 * one any more: a spent allowance shows the paywall. An ad is now shown in
 * exactly two places, after a lesson and in the centre of the screen, and
 * reporting it only feeds the daily cap the server keeps per account.
 *
 * @param placement `lesson_end` or `screen_center`. The server refuses
 *   anything else, and it — not this class — decides whether that place is
 *   switched on, who is in its audience and how many are left today.
 */
class AdViewModel(
    private val repository: FeatureRepository,
    private val placement: String,
    private val lessonOrder: Int = 0,
) : ViewModel() {

    private val _state = MutableStateFlow(AdUiState())
    val state: StateFlow<AdUiState> = _state.asStateFlow()

    private var ticker: Job? = null
    private var adId: Int = 0

    init {
        load()
    }

    fun load() {
        ticker?.cancel()
        adId = 0
        _state.value = AdUiState()
        viewModelScope.launch {
            val listing = when (val result = repository.ads(placement)) {
                is ApiResult.Failure -> {
                    // A missing ad is not a broken screen. The server answers
                    // this way for every ordinary reason too — the place is
                    // off, the learner is paid, the daily cap is spent — so
                    // the caller simply closes and carries on.
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
            adId = ad.id
            _state.update {
                it.copy(
                    isLoading = false,
                    ad = ad,
                    mediaUrl = mediaUrl,
                    // The server says how long before this may be closed. The
                    // creative's own duration is only the fallback.
                    requiredSeconds = AdWatch.requiredSeconds(
                        fromServer = ad.skipAfterSeconds,
                        fromCreative = ad.durationSeconds,
                    ),
                )
            }
            startTicker()
        }
    }

    private fun startTicker() {
        ticker?.cancel()
        ticker = viewModelScope.launch {
            while (isActive && !_state.value.canContinue) {
                delay(1_000)
                _state.update { it.copy(elapsedSeconds = it.elapsedSeconds + 1) }
            }
        }
    }

    /**
     * Reports the view and closes.
     *
     * The report is not a request for anything, so its outcome cannot keep
     * the learner on this screen: whether the server counted it or the call
     * never arrived, the ad is over either way.
     */
    fun onContinue() {
        val current = _state.value
        if (!current.canContinue || current.isFinishing) return
        _state.update { it.copy(isFinishing = true, error = null) }
        viewModelScope.launch {
            repository.recordAdView(
                adId = adId,
                watchedSeconds = current.elapsedSeconds,
                placement = placement,
                lessonOrder = lessonOrder,
            )
            _state.update { it.copy(isFinishing = false, finished = true) }
        }
    }

    override fun onCleared() {
        ticker?.cancel()
        super.onCleared()
    }

    companion object {
        /** One block after a finished lesson. */
        const val PLACEMENT_LESSON_END = "lesson_end"

        /** The modal in the centre of the screen, whatever section is open. */
        const val PLACEMENT_SCREEN_CENTER = "screen_center"
    }

    class Factory(
        private val repository: FeatureRepository,
        private val placement: String,
        private val lessonOrder: Int = 0,
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            AdViewModel(repository, placement, lessonOrder) as T
    }
}
