package com.pomp.hskai.data.repository

import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.core.network.apiCall
import com.pomp.hskai.data.api.AndroidFeatureApi
import com.pomp.hskai.data.api.AndroidProfileResponse
import com.pomp.hskai.data.api.AndroidSubscriptionOverviewResponse
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

    suspend fun practiceStart(
        mode: String,
        level: String,
        language: String,
        skill: String,
    ): ApiResult<PracticeStartResponse> = authorized {
        api.practiceStart(
            it,
            PracticeStartRequest(
                mode = mode,
                level = level,
                language = language,
                skill = skill,
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
