package com.pomp.hskai.data.api

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Query

/**
 * Google / Apple sign-in and identity management transport.
 *
 * None of these endpoints returns a session token. A sign-in flow only marks
 * the shared link request approved; the tokens still arrive through the
 * existing [AndroidAuthApi.linkStatus] call, so the app keeps exactly one
 * place where a session is created.
 */
interface NativeOAuthApi {

    @GET("api/v3/native-auth/providers")
    suspend fun providers(@Query("platform") platform: String = "android"): Response<ProvidersResponse>

    @POST("api/v3/native-auth/oauth/start")
    suspend fun oauthStart(@Body body: OAuthStartRequest): Response<OAuthStartResponse>

    @POST("api/v3/native-auth/oauth/assert")
    suspend fun oauthAssert(@Body body: OAuthAssertRequest): Response<OAuthAssertResponse>

    @GET("api/v3/native-auth/identities")
    suspend fun identities(
        @Header("Authorization") authorization: String,
    ): Response<IdentitiesResponse>

    @POST("api/v3/native-auth/identities/link/start")
    suspend fun identityLinkStart(
        @Header("Authorization") authorization: String,
        @Body body: OAuthStartRequest,
    ): Response<OAuthStartResponse>

    @POST("api/v3/native-auth/identities/link/status")
    suspend fun identityLinkStatus(
        @Header("Authorization") authorization: String,
        @Body body: IdentityLinkStatusRequest,
    ): Response<IdentityLinkStatusResponse>

    @POST("api/v3/native-auth/identities/unlink")
    suspend fun identityUnlink(
        @Header("Authorization") authorization: String,
        @Body body: IdentityUnlinkRequest,
    ): Response<IdentityUnlinkResponse>
}
