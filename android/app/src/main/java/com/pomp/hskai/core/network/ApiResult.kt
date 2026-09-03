package com.pomp.hskai.core.network

import com.pomp.hskai.data.api.ApiErrorBody
import java.io.IOException
import java.net.SocketTimeoutException
import kotlinx.serialization.json.Json
import retrofit2.Response

sealed interface ApiResult<out T> {
    data class Success<T>(val value: T) : ApiResult<T>
    data class Failure(val error: ApiError) : ApiResult<Nothing>
}

private val errorJson = Json { ignoreUnknownKeys = true }

/**
 * Runs a Retrofit call and converts both transport failures and the server's
 * stable `{"ok": false, "error": "..."}` envelope into [ApiError].
 *
 * Raw throwables never escape: the UI must show mapped, localized copy, not
 * an exception message.
 */
suspend fun <T : Any> apiCall(block: suspend () -> Response<T>): ApiResult<T> = try {
    val response = block()
    val body = response.body()
    when {
        response.isSuccessful && body != null -> ApiResult.Success(body)
        // A 2xx with no parsable body is not something the caller can use, and
        // silently inventing one would hide a contract change.
        response.isSuccessful -> ApiResult.Failure(ApiError.Unknown)
        else -> ApiResult.Failure(response.toApiError())
    }
} catch (timeout: SocketTimeoutException) {
    ApiResult.Failure(ApiError.Timeout)
} catch (io: IOException) {
    ApiResult.Failure(ApiError.Offline)
} catch (unexpected: Exception) {
    ApiResult.Failure(ApiError.Unknown)
}

/**
 * Maps a failed response to an [ApiError]. Shared so every caller classifies a
 * failure the same way — a second, weaker parser would read the same response
 * differently. The error body can only be read once, which is another reason
 * there is exactly one of these.
 */
internal fun Response<*>.toApiError(): ApiError {
    val envelope = runCatching {
        val raw = errorBody()?.string().orEmpty()
        if (raw.isBlank()) null else errorJson.decodeFromString<ApiErrorBody>(raw)
    }.getOrNull()
    // Named so it cannot be confused with Response.code(), the HTTP status.
    val errorCode = envelope?.error?.takeIf { it.isNotBlank() } ?: when (code()) {
        401 -> "desktop_access_invalid"
        429 -> "desktop_link_rate_limited"
        else -> null
    }
    val mapped = ApiError.fromCode(errorCode)
    // A spent daily allowance is the one failure that has a future: the block
    // can tell the learner when it comes back, so the instant is kept.
    return if (errorCode == FREE_LIMIT_CODE) {
        ApiError.LimitReached(resetAt = envelope?.resetAt, messageRes = mapped.messageRes)
    } else {
        mapped
    }
}

private const val FREE_LIMIT_CODE = "free_feature_limit_reached"
