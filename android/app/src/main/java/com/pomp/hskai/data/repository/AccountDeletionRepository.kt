package com.pomp.hskai.data.repository

import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.core.network.apiCall
import com.pomp.hskai.data.api.AccountDeletionApi
import com.pomp.hskai.data.api.AccountDeletionConfirmation
import com.pomp.hskai.data.api.AccountDeletionPrepared
import com.pomp.hskai.data.api.AccountDeletionReceipt
import kotlinx.serialization.json.JsonObject
import java.time.Instant
import java.time.OffsetDateTime
import java.util.UUID

class AccountDeletionRepository(
    private val api: AccountDeletionApi,
    private val accessToken: suspend () -> ApiResult<String>,
    private val onSessionExpired: suspend () -> Unit = {},
) {
    suspend fun prepare(): ApiResult<AccountDeletionPrepared> {
        val token = when (val result = accessToken()) {
            is ApiResult.Failure -> return result
            is ApiResult.Success -> result.value
        }
        val result = apiCall { api.prepare("Bearer $token", JsonObject(emptyMap())) }
        if (result is ApiResult.Failure && result.error is ApiError.SessionExpired) onSessionExpired()
        return when (result) {
            is ApiResult.Failure -> result
            is ApiResult.Success -> if (result.value.isValid()) result else ApiResult.Failure(ApiError.Unknown)
        }
    }

    suspend fun confirm(prepared: AccountDeletionPrepared): ApiResult<AccountDeletionReceipt> {
        if (!prepared.isValid()) return ApiResult.Failure(ApiError.Unknown)
        val result = apiCall {
            api.confirm(AccountDeletionConfirmation(prepared.requestId, prepared.secret, "DELETE"))
        }
        return when (result) {
            is ApiResult.Failure -> result
            is ApiResult.Success -> {
                val receipt = result.value
                val requested = parseInstant(receipt.requestedAt)
                val due = parseInstant(receipt.dueAt)
                if (receipt.ok && receipt.status == "submitted" && receipt.requestId == prepared.requestId &&
                    requested != null && due != null && !due.isBefore(requested)
                ) result else ApiResult.Failure(ApiError.Unknown)
            }
        }
    }

    private fun AccountDeletionPrepared.isValid(): Boolean =
        ok && status == "verified" && secret.length >= 32 && accountLabel.isNotBlank() &&
            runCatching { UUID.fromString(requestId) }.isSuccess

    private fun parseInstant(raw: String): Instant? = runCatching { Instant.parse(raw) }
        .recoverCatching { OffsetDateTime.parse(raw).toInstant() }.getOrNull()
}
