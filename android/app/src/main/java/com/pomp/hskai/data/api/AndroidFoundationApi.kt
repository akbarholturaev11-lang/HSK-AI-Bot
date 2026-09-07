package com.pomp.hskai.data.api

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST

/** Bearer-authenticated Starter 0 transport, isolated from the main course API. */
interface AndroidFoundationApi {
    @GET("api/v3/android/course/foundation")
    suspend fun foundation(
        @Header("Authorization") authorization: String,
    ): Response<FoundationResponseDto>

    @POST("api/v3/android/course/foundation/complete")
    suspend fun completeFoundation(
        @Header("Authorization") authorization: String,
        @Body body: FoundationCompleteRequest,
    ): Response<FoundationCompleteResponse>
}
