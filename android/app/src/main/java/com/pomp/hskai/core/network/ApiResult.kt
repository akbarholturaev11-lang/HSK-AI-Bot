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
    if (response.isSuccessful && body != null) {
        ApiResult.Success(body)
    } else if (response.isSuccessful) {
        @Suppress("UNCHECKED_CAST")
        ApiResult.Success(Unit as T)
    } else {
        ApiResult.Failure(ApiError.fromCode(response.errorCode()))
    }
} catch (timeout: SocketTimeoutException) {
    ApiResult.Failure(ApiError.Timeout)
} catch (io: IOException) {
    ApiResult.Failure(ApiError.Offline)
} catch (unexpected: Exception) {
    ApiResult.Failure(ApiError.Unknown)
}

private fun Response<*>.errorCode(): String? = runCatching {
    val raw = errorBody()?.string().orEmpty()
    if (raw.isBlank()) null else errorJson.decodeFromString<ApiErrorBody>(raw).error
}.getOrNull() ?: when (code()) {
    401 -> "desktop_access_invalid"
    429 -> "desktop_link_rate_limited"
    else -> null
}
