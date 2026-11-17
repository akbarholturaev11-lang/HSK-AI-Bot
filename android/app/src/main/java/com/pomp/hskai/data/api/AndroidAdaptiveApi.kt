package com.pomp.hskai.data.api

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.Header
import retrofit2.http.POST

/**
 * In-lesson personal review (UIUX-007). The owner comes from the Bearer token
 * only; the body never names an account. The question is the same public shape
 * Xatolarim uses ([MistakeReviewQuestionDto]) and the verdict is the server's.
 */
interface AndroidAdaptiveApi {
    @POST("api/v3/android/adaptive/plan")
    suspend fun plan(
        @Header("Authorization") authorization: String,
        @Body body: AdaptivePlanRequestDto,
    ): Response<AdaptivePlanResponseDto>

    @POST("api/v3/android/adaptive/answer")
    suspend fun answer(
        @Header("Authorization") authorization: String,
        @Body body: AdaptiveAnswerRequestDto,
    ): Response<AdaptiveAnswerResponseDto>
}

@Serializable
data class AdaptivePlanRequestDto(
    @SerialName("level") val level: String,
    @SerialName("lesson_order") val lessonOrder: Int,
    @SerialName("formats") val formats: List<String>,
    @SerialName("language") val language: String,
)

@Serializable
data class AdaptivePlanResponseDto(
    @SerialName("ok") val ok: Boolean = false,
    @SerialName("enabled") val enabled: Boolean = false,
    @SerialName("plan") val plan: AdaptivePlanDto? = null,
)

@Serializable
data class AdaptivePlanDto(
    @SerialName("id") val id: Long = 0,
    @SerialName("version") val version: Int = 0,
    @SerialName("level") val level: String = "",
    @SerialName("lesson_order") val lessonOrder: Int = 0,
    @SerialName("items") val items: List<AdaptiveItemDto> = emptyList(),
)

@Serializable
data class AdaptiveItemDto(
    @SerialName("id") val id: String = "",
    @SerialName("slot") val slot: Int = 0,
    @SerialName("kind") val kind: String = "",
    @SerialName("skill") val skill: String = "",
    @SerialName("question") val question: MistakeReviewQuestionDto = MistakeReviewQuestionDto(),
    @SerialName("answered") val answered: Boolean = false,
)

/** Exactly one of [selectedIndex] / [selectedTokens]; the other stays null and is not sent. */
@Serializable
data class AdaptiveAnswerRequestDto(
    @SerialName("plan_id") val planId: Long,
    @SerialName("item_id") val itemId: String,
    @SerialName("selected_index") val selectedIndex: Int? = null,
    @SerialName("selected_tokens") val selectedTokens: List<String>? = null,
)

@Serializable
data class AdaptiveAnswerResponseDto(
    @SerialName("ok") val ok: Boolean = false,
    @SerialName("item_id") val itemId: String = "",
    @SerialName("correct") val correct: Boolean = false,
    @SerialName("correct_index") val correctIndex: Int? = null,
    @SerialName("selected_index") val selectedIndex: Int? = null,
    @SerialName("correct_answer") val correctAnswer: String = "",
    @SerialName("explanation") val explanation: String = "",
    @SerialName("duplicate") val duplicate: Boolean = false,
)
