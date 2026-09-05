package com.pomp.hskai.data.api

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST

/** Bearer-authenticated native onboarding transport only. */
interface AndroidOnboardingApi {
    @GET("api/v3/android/course/onboarding")
    suspend fun status(
        @Header("Authorization") authorization: String,
    ): Response<AndroidOnboardingStatusDto>

    @POST("api/v3/android/course/onboarding")
    suspend fun complete(
        @Header("Authorization") authorization: String,
        @Body body: AndroidOnboardingRequestDto,
    ): Response<AndroidOnboardingCompleteDto>
}
