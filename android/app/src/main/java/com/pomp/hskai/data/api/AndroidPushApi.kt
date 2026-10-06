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
data class PushPreferencesRequest(
    @SerialName("study_reminders_enabled") val studyRemindersEnabled: Boolean,
    @SerialName("timezone_name") val timezoneName: String,
    @SerialName("notifications_allowed") val notificationsAllowed: Boolean,
)

@Serializable
data class PushOkResponse(@SerialName("ok") val ok: Boolean = false)

@Serializable
data class PaymentDecisionStatusResponse(
    @SerialName("ok") val ok: Boolean = false,
    @SerialName("payment_id") val paymentId: Int = 0,
    @SerialName("status") val status: String = "",
    @SerialName("plan_type") val planType: String = "",
)

/** A subscription or limit notice; `show = false` means Telegram already has it. */
@Serializable
data class AccountNoticeDto(
    @SerialName("id") val id: Int = 0,
    @SerialName("show") val show: Boolean = false,
    @SerialName("key") val key: String = "",
    @SerialName("title") val title: String = "",
    @SerialName("body") val body: String = "",
    @SerialName("action") val action: String = "subscription",
)

@Serializable
data class AccountNoticeResponse(
    @SerialName("ok") val ok: Boolean = false,
    @SerialName("notice") val notice: AccountNoticeDto? = null,
)

@Serializable
data class AccountNoticeAckRequest(@SerialName("shown") val shown: Boolean)

interface AndroidPushApi {
    @POST("api/v3/android/push/register")
    suspend fun register(
        @Header("Authorization") authorization: String,
        @Body body: PushTokenRequest,
    ): Response<PushOkResponse>

    @POST("api/v3/android/push/preferences")
    suspend fun preferences(
        @Header("Authorization") authorization: String,
        @Body body: PushPreferencesRequest,
    ): Response<PushOkResponse>

    @POST("api/v3/android/push/unregister")
    suspend fun unregister(
        @Header("Authorization") authorization: String,
    ): Response<PushOkResponse>

    @GET("api/v3/android/notices/{notice_id}")
    suspend fun notice(
        @Header("Authorization") authorization: String,
        @Path("notice_id") noticeId: Int,
    ): Response<AccountNoticeResponse>

    @POST("api/v3/android/notices/{notice_id}/ack")
    suspend fun acknowledgeNotice(
        @Header("Authorization") authorization: String,
        @Path("notice_id") noticeId: Int,
        @Body body: AccountNoticeAckRequest,
    ): Response<PushOkResponse>

    @GET("api/v3/android/subscription/payments/{payment_id}/status")
    suspend fun paymentStatus(
        @Header("Authorization") authorization: String,
        @Path("payment_id") paymentId: Int,
    ): Response<PaymentDecisionStatusResponse>
}
