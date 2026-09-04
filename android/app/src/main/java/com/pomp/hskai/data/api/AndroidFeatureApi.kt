package com.pomp.hskai.data.api

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Query

interface AndroidFeatureApi {

    @GET("api/v3/android/profile")
    suspend fun profile(
        @Header("Authorization") authorization: String,
    ): Response<AndroidProfileResponse>

    @GET("api/v3/android/subscription/overview")
    suspend fun subscriptionOverview(
        @Header("Authorization") authorization: String,
    ): Response<AndroidSubscriptionOverviewResponse>

    @POST("api/v3/android/subscription/open")
    suspend fun subscriptionOpen(
        @Header("Authorization") authorization: String,
    ): Response<AndroidSubscriptionOpenResponse>

    @POST("api/v3/android/practice/start")
    suspend fun practiceStart(
        @Header("Authorization") authorization: String,
        @Body body: PracticeStartRequest,
    ): Response<PracticeStartResponse>

    @POST("api/v3/android/practice/complete")
    suspend fun practiceComplete(
        @Header("Authorization") authorization: String,
        @Body body: PracticeCompleteRequest,
    ): Response<PracticeCompleteResponse>

    @POST("api/v3/android/exams/start")
    suspend fun examStart(
        @Header("Authorization") authorization: String,
        @Body body: ExamStartRequest,
    ): Response<ExamStartResponse>

    @POST("api/v3/android/exams/complete")
    suspend fun examComplete(
        @Header("Authorization") authorization: String,
        @Body body: ExamCompleteRequest,
    ): Response<ExamCompleteResponse>

    @GET("api/v3/android/mistakes")
    suspend fun mistakes(
        @Header("Authorization") authorization: String,
        @Query("category") category: String? = null,
        @Query("limit") limit: Int = 30,
        @Query("offset") offset: Int = 0,
    ): Response<MistakesOverviewResponse>

    @POST("api/v3/android/mistakes/review/start")
    suspend fun mistakeReviewStart(
        @Header("Authorization") authorization: String,
        @Body body: MistakeReviewStartRequest = MistakeReviewStartRequest(),
    ): Response<MistakeReviewStartResponse>

    @POST("api/v3/android/mistakes/review/answer")
    suspend fun mistakeReviewAnswer(
        @Header("Authorization") authorization: String,
        @Body body: MistakeReviewAnswerRequest,
    ): Response<MistakeReviewAnswerResponse>

    @POST("api/v3/android/mistakes/review/complete")
    suspend fun mistakeReviewComplete(
        @Header("Authorization") authorization: String,
        @Body body: MistakeReviewCompleteRequest,
    ): Response<MistakeReviewCompleteResponse>

    @GET("api/v3/android/rating/leaderboard")
    suspend fun rating(
        @Header("Authorization") authorization: String,
        @Query("tz") timezoneOffsetMinutes: Int,
    ): Response<RatingResponse>

    @GET("api/v3/android/referral/overview")
    suspend fun referral(
        @Header("Authorization") authorization: String,
        @Query("tz") timezoneOffsetMinutes: Int,
    ): Response<ReferralOverviewResponse>

    @GET("api/v3/android/voice/status")
    suspend fun voiceStatus(
        @Header("Authorization") authorization: String,
    ): Response<VoiceStatusResponse>

    @POST("api/v3/android/voice/session/start")
    suspend fun voiceStart(
        @Header("Authorization") authorization: String,
        @Body body: VoiceStartRequest,
    ): Response<VoiceStartResponse>

    @POST("api/v3/android/voice/message")
    suspend fun voiceMessage(
        @Header("Authorization") authorization: String,
        @Body body: VoiceMessageRequest,
    ): Response<VoiceMessageResponse>

    @POST("api/v3/android/voice/session/end")
    suspend fun voiceEnd(
        @Header("Authorization") authorization: String,
        @Body body: VoiceEndRequest,
    ): Response<VoiceEndResponse>

    /**
     * The ads this distribution channel is allowed to show. The server, not
     * the client, decides which types the channel may receive.
     */
    @GET("api/v3/android/ad")
    suspend fun ads(
        @Header("Authorization") authorization: String,
        @Query("slot") slot: String,
        @Query("channel") channel: String,
    ): Response<AndroidAdListResponse>

    @POST("api/v3/android/ad/attempt")
    suspend fun adAttempt(
        @Header("Authorization") authorization: String,
        @Body body: AndroidAdAttemptRequest,
    ): Response<AndroidAdAttemptResponse>

    @POST("api/v3/android/ad/view")
    suspend fun adView(
        @Header("Authorization") authorization: String,
        @Body body: AndroidAdViewRequest,
    ): Response<AndroidAdViewResponse>
}
