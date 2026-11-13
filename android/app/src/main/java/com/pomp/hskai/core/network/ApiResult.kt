package com.pomp.hskai.core.network

import com.pomp.hskai.core.diagnostics.DiagFailure
import com.pomp.hskai.core.diagnostics.DiagTag
import com.pomp.hskai.core.diagnostics.Diagnostics
import com.pomp.hskai.data.api.ApiErrorBody
import java.io.IOException
import java.net.SocketTimeoutException
import kotlin.coroutines.cancellation.CancellationException
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
suspend fun <T : Any> apiCall(
    diag: DiagTag? = null,
    diagnosticToken: String? = null,
    block: suspend () -> Response<T>,
): ApiResult<T> {
    val scope = if (diag != null) Diagnostics.scope() else null
    fun report(failure: DiagFailure) {
        if (diag != null) Diagnostics.report(scope, diag.feature, failure, diag.site, diagnosticToken)
    }

    return try {
        val response = block()
        val body = response.body()
        when {
            response.isSuccessful && body != null -> ApiResult.Success(body)
            // A 2xx with no parsable body is not something the caller can use, and
            // silently inventing one would hide a contract change.
            response.isSuccessful -> {
                report(DiagFailure.API_DECODE)
                ApiResult.Failure(ApiError.Unknown)
            }
            else -> {
                // The error body is read once, by toApiError(); the report only
                // needs the HTTP status it already has.
                val error = response.toApiError()
                if (response.code().isReportedServerFailure()) report(DiagFailure.API_5XX)
                ApiResult.Failure(error)
            }
        }
    } catch (timeout: SocketTimeoutException) {
        ApiResult.Failure(ApiError.Timeout)
    } catch (io: IOException) {
        ApiResult.Failure(ApiError.Offline)
    } catch (unexpected: Exception) {
        // A non-IO failure while reading a 2xx is a decode failure (it also catches
        // a model R8 stripped). A cancelled call is not a failure.
        if (unexpected !is CancellationException) report(DiagFailure.API_DECODE)
        ApiResult.Failure(ApiError.Unknown)
    }
}

/**
 * 503 is the backend's "switched off / temporarily unavailable" answer, an
 * expected outcome, as on the server side. Every other 5xx is reported.
 */
private fun Int.isReportedServerFailure() = this >= 500 && this != 503

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
        ApiError.LimitReached(limitText = envelope?.limitText, resetAt = envelope?.resetAt, messageRes = mapped.messageRes)
    } else {
        mapped
    }
}

private const val FREE_LIMIT_CODE = "free_feature_limit_reached"
