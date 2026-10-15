package com.pomp.hskai.data.api

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonObject
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.Header
import retrofit2.http.POST

/** Ownership comes from the current native session, regardless of its provider. */
interface AccountDeletionApi {
    @POST("api/account-deletion/prepare")
    suspend fun prepare(
        @Header("Authorization") authorization: String,
        @Body body: JsonObject,
    ): Response<AccountDeletionPrepared>

    // The short-lived challenge is carried only in the body, never in a URL.
    @POST("api/account-deletion/confirm")
    suspend fun confirm(@Body body: AccountDeletionConfirmation): Response<AccountDeletionReceipt>
}

@Serializable
data class AccountDeletionPrepared(
    val ok: Boolean = false,
    @SerialName("request_id") val requestId: String = "",
    val secret: String = "",
    val status: String = "",
    @SerialName("account_label") val accountLabel: String = "",
)

@Serializable
data class AccountDeletionConfirmation(
    @SerialName("request_id") val requestId: String,
    val secret: String,
    val confirmation: String,
)

@Serializable
data class AccountDeletionReceipt(
    val ok: Boolean = false,
    val status: String = "",
    @SerialName("request_id") val requestId: String = "",
    @SerialName("requested_at") val requestedAt: String = "",
    @SerialName("due_at") val dueAt: String = "",
)
