package com.pomp.hskai.data.repository

import com.pomp.hskai.BuildConfig
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.core.network.apiCall
import com.pomp.hskai.data.api.AndroidAdAttemptRequest
import com.pomp.hskai.data.api.AndroidAdAttemptResponse
import com.pomp.hskai.data.api.AndroidAdListResponse
import com.pomp.hskai.data.api.AndroidAdViewRequest
import com.pomp.hskai.data.api.AndroidAdViewResponse
import com.pomp.hskai.data.api.AndroidFeatureApi
import com.pomp.hskai.data.api.AndroidProfileResponse
import com.pomp.hskai.data.api.AndroidSubscriptionOpenResponse
import com.pomp.hskai.data.api.AndroidSubscriptionOverviewResponse
import com.pomp.hskai.data.api.ExamAnswerDto
import com.pomp.hskai.data.api.ExamCompleteRequest
import com.pomp.hskai.data.api.ExamCompleteResponse
import com.pomp.hskai.data.api.ExamStartRequest
import com.pomp.hskai.data.api.ExamStartResponse
import com.pomp.hskai.data.api.MistakeReviewAnswerRequest
import com.pomp.hskai.data.api.MistakeReviewAnswerResponse
import com.pomp.hskai.data.api.MistakeReviewCompleteAnswerDto
import com.pomp.hskai.data.api.MistakeReviewCompleteRequest
import com.pomp.hskai.data.api.MistakeReviewCompleteResponse
import com.pomp.hskai.data.api.MistakeReviewStartRequest
import com.pomp.hskai.data.api.MistakeReviewStartResponse
import com.pomp.hskai.data.api.MistakesOverviewResponse
import com.pomp.hskai.data.api.PracticeAnswerDto
import com.pomp.hskai.data.api.PracticeCompleteRequest
import com.pomp.hskai.data.api.PracticeCompleteResponse
import com.pomp.hskai.data.api.PracticeStartRequest
import com.pomp.hskai.data.api.PracticeStartResponse
import com.pomp.hskai.data.api.RatingResponse
import com.pomp.hskai.data.api.ReferralOverviewResponse
import com.pomp.hskai.data.api.VoiceEndRequest
import com.pomp.hskai.data.api.VoiceEndResponse
import com.pomp.hskai.data.api.VoiceMessageRequest
import com.pomp.hskai.data.api.VoiceMessageResponse
import com.pomp.hskai.data.api.VoiceStartRequest
import com.pomp.hskai.data.api.VoiceStartResponse
import com.pomp.hskai.data.api.VoiceStatusResponse
import java.util.TimeZone

class FeatureRepository(
    private val api: AndroidFeatureApi,
    private val accessToken: suspend () -> ApiResult<String>,
    private val onSessionExpired: suspend () -> Unit = {},
    private val timezoneOffsetMinutes: () -> Int = {
        TimeZone.getDefault().getOffset(System.currentTimeMillis()) / 60_000
    },
) {

    suspend fun profile(): ApiResult<AndroidProfileResponse> = authorized {
        api.profile(it)
    }

    suspend fun subscriptionOverview(): ApiResult<AndroidSubscriptionOverviewResponse> =
        authorized { api.subscriptionOverview(it) }

    /**
     * Asks the bot to post the subscription menu into the learner's Telegram
     * chat and returns where to open it. Buying never happens in this app.
     */
    suspend fun subscriptionOpen(): ApiResult<AndroidSubscriptionOpenResponse> =
        authorized { api.subscriptionOpen(it) }

    suspend fun rating(): ApiResult<RatingResponse> = authorized {
        api.rating(it, timezoneOffsetMinutes())
    }

    suspend fun referral(): ApiResult<ReferralOverviewResponse> = authorized {
        api.referral(it, timezoneOffsetMinutes())
    }

    suspend fun mistakes(
        category: String? = null,
        limit: Int = 30,
        offset: Int = 0,
    ): ApiResult<MistakesOverviewResponse> = authorized {
        api.mistakes(it, category = category, limit = limit, offset = offset)
    }

    suspend fun startMistakeReview(): ApiResult<MistakeReviewStartResponse> =
        authorized { api.mistakeReviewStart(it, MistakeReviewStartRequest()) }

    suspend fun answerMistakeReview(
        sessionId: String,
        questionId: String,
        selectedIndex: Int,
    ): ApiResult<MistakeReviewAnswerResponse> = authorized {
        api.mistakeReviewAnswer(
            it,
            MistakeReviewAnswerRequest(
                sessionId = sessionId,
                questionId = questionId,
                selectedIndex = selectedIndex,
            ),
        )
    }

    suspend fun completeMistakeReview(
        sessionId: String,
        answers: Map<String, Int>,
    ): ApiResult<MistakeReviewCompleteResponse> = authorized {
        api.mistakeReviewComplete(
            it,
            MistakeReviewCompleteRequest(
                sessionId = sessionId,
                answers = answers.map { (questionId, selectedIndex) ->
                    MistakeReviewCompleteAnswerDto(questionId, selectedIndex)
                },
            ),
        )
    }

    suspend fun examStart(
        level: String,
        language: String,
        accessRef: String = "",
        adSupported: Boolean = false,
    ): ApiResult<ExamStartResponse> = authorized {
        api.examStart(
            it,
            ExamStartRequest(
                level = level,
                language = language,
                accessRef = accessRef,
                adSupported = adSupported,
            ),
        )
    }

    suspend fun examComplete(
        sessionId: String,
        level: String,
        language: String,
        answers: Map<String, Int>,
    ): ApiResult<ExamCompleteResponse> = authorized {
        api.examComplete(
            it,
            ExamCompleteRequest(
                sessionId = sessionId,
                level = level,
                language = language,
                answers = answers.map { (questionId, selectedIndex) ->
                    ExamAnswerDto(questionId, selectedIndex)
                },
            ),
        )
    }

    suspend fun practiceStart(
        mode: String,
        level: String,
        language: String,
        skill: String,
        accessRef: String = "",
        adSupported: Boolean = false,
    ): ApiResult<PracticeStartResponse> = authorized {
        api.practiceStart(
            it,
            PracticeStartRequest(
                mode = mode,
                level = level,
                language = language,
                skill = skill,
                accessRef = accessRef,
                adSupported = adSupported,
            ),
        )
    }

    suspend fun practiceComplete(
        sessionId: String,
        mode: String,
        level: String,
        language: String,
        skill: String,
        answers: Map<String, Int>,
        accessRef: String = "",
        adSupported: Boolean = false,
    ): ApiResult<PracticeCompleteResponse> = authorized {
        api.practiceComplete(
            it,
            PracticeCompleteRequest(
                sessionId = sessionId,
                mode = mode,
                level = level,
                language = language,
                skill = skill,
                answers = answers.map { (questionId, selected) ->
                    PracticeAnswerDto(questionId, selected)
                },
                accessRef = accessRef,
                adSupported = adSupported,
            ),
        )
    }

    suspend fun voiceStatus(): ApiResult<VoiceStatusResponse> = authorized {
        api.voiceStatus(it)
    }

    suspend fun voiceStart(
        role: String,
        level: String,
        language: String,
        voice: String = "female",
    ): ApiResult<VoiceStartResponse> = authorized {
        api.voiceStart(
            it,
            VoiceStartRequest(
                role = role,
                level = level.toVoiceLevel(),
                language = language,
                voice = voice,
            ),
        )
    }

    suspend fun voiceMessage(
        sessionId: String,
        audioDataUrl: String,
    ): ApiResult<VoiceMessageResponse> = authorized {
        api.voiceMessage(
            it,
            VoiceMessageRequest(
                sessionId = sessionId,
                audioDataUrl = audioDataUrl,
            ),
        )
    }

    suspend fun voiceEnd(sessionId: String): ApiResult<VoiceEndResponse> =
        authorized { api.voiceEnd(it, VoiceEndRequest(sessionId)) }

    /**
     * The ads this build's channel is allowed to show.
     *
     * The channel is compiled in, and the server — not the client — decides
     * what each channel may receive. A 404 here means "no ad to show", which
     * is an ordinary outcome, not a failure of the screen.
     */
    suspend fun ads(slot: String): ApiResult<AndroidAdListResponse> = authorized {
        api.ads(it, slot = slot, channel = BuildConfig.DISTRIBUTION_CHANNEL)
    }

    /**
     * Opens an ad attempt. The returned token is what makes a later view
     * count: without it the server unlocks nothing.
     */
    suspend fun startAdAttempt(
        adId: Int,
        feature: String,
        accessRef: String,
        lessonOrder: Int = 0,
    ): ApiResult<AndroidAdAttemptResponse> = authorized {
        api.adAttempt(
            it,
            AndroidAdAttemptRequest(
                adId = adId,
                feature = feature,
                lessonOrder = lessonOrder,
                accessRef = accessRef,
            ),
        )
    }

    /**
     * Reports a watched ad. The server measures the real elapsed time since
     * the attempt was opened, so this cannot be hurried.
     */
    suspend fun recordAdView(
        adId: Int,
        watchedSeconds: Int,
        feature: String,
        accessRef: String,
        attemptToken: String,
        lessonOrder: Int = 0,
    ): ApiResult<AndroidAdViewResponse> = authorized {
        api.adView(
            it,
            AndroidAdViewRequest(
                adId = adId,
                watchedSeconds = watchedSeconds,
                feature = feature,
                lessonOrder = lessonOrder,
                accessRef = accessRef,
                attemptToken = attemptToken,
            ),
        )
    }

    private suspend fun <T : Any> authorized(
        call: suspend (authorization: String) -> retrofit2.Response<T>,
    ): ApiResult<T> {
        val token = when (val result = accessToken()) {
            is ApiResult.Failure -> return result
            is ApiResult.Success -> result.value
        }
        val result = apiCall { call("Bearer $token") }
        if (result is ApiResult.Failure && result.error is ApiError.SessionExpired) {
            onSessionExpired()
        }
        return result
    }

    private fun String.toVoiceLevel(): String {
        val normalized = trim().lowercase()
        return if (normalized.startsWith("hsk4")) "hsk4" else normalized.ifBlank { "hsk1" }
    }
}
