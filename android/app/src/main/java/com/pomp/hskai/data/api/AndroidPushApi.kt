package com.pomp.hskai.data.api

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Path

@Serializable
data class PushTokenRequest(@SerialName("token") val token: String)

@Serializable
data class PushOkResponse(@SerialName("ok") val ok: Boolean = false)

@Serializable
data class PaymentDecisionStatusResponse(
    @SerialName("ok") val ok: Boolean = false,
    @SerialName("payment_id") val paymentId: Int = 0,
    @SerialName("status") val status: String = "",
)

interface AndroidPushApi {
    @POST("api/v3/android/push/register")
    suspend fun register(
        @Header("Authorization") authorization: String,
        @Body body: PushTokenRequest,
    ): Response<PushOkResponse>

    @POST("api/v3/android/push/unregister")
    suspend fun unregister(
        @Header("Authorization") authorization: String,
    ): Response<PushOkResponse>

    @GET("api/v3/android/subscription/payments/{payment_id}/status")
    suspend fun paymentStatus(
        @Header("Authorization") authorization: String,
        @Path("payment_id") paymentId: Int,
    ): Response<PaymentDecisionStatusResponse>
}
