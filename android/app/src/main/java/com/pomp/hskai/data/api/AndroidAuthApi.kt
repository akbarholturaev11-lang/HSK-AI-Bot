package com.pomp.hskai.data.api

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Query

/**
 * Android device-link transport.
 *
 * Link start/status/refresh carry their secrets in the POST body, never in the
 * URL, so nothing sensitive can reach access logs or browser history. Only
 * revoke and bootstrap use `Authorization: Bearer`.
 */
interface AndroidAuthApi {

    @POST("api/v3/android-auth/link/start")
    suspend fun startLink(@Body body: LinkStartRequest): Response<LinkStartResponse>

    @POST("api/v3/android-auth/link/status")
    suspend fun linkStatus(@Body body: LinkStatusRequest): Response<LinkStatusResponse>

    @POST("api/v3/android-auth/refresh")
    suspend fun refresh(@Body body: RefreshRequest): Response<RefreshResponse>

    @POST("api/v3/android-auth/revoke")
    suspend fun revoke(
        @Header("Authorization") authorization: String,
        @Body body: RevokeRequest,
    ): Response<Unit>

    @GET("api/v3/android/bootstrap")
    suspend fun bootstrap(
        @Header("Authorization") authorization: String,
        @Query("app_version") appVersion: String,
    ): Response<BootstrapResponse>
}
