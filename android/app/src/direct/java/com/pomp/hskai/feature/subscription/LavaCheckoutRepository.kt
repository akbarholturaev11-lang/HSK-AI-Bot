package com.pomp.hskai.feature.subscription

import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.core.network.apiCall
import kotlinx.coroutines.withTimeoutOrNull
import kotlinx.serialization.Serializable
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.Headers
import retrofit2.http.POST

@Serializable
data class LavaContext(val mode: String = "subscription", val origin: String = "")
@Serializable
data class LavaStart(val plan_type: String, val email: String, val mode: String, val language: String)
@Serializable
data class LavaId(val checkout_id: Int)
@Serializable
data class ExitAction(val action: String)
@Serializable
data class LavaPlan(val plan_type: String = "", val months: Int = 0, val days: Int = 0,
    val amount: String? = null, val currency: String = "", val base_amount: String? = null, val discount_percent: Int? = null)
@Serializable
data class LavaSubscription(val status: String = "", val auto_renew: Boolean = false, val pro_until: String? = null)
@Serializable
data class LavaBlock(val mode: String = "manual_only", val plans: List<LavaPlan> = emptyList(),
    val blocked_reason: String? = null, val subscription: LavaSubscription? = null, val email: String? = null,
    val pending_checkout_id: Int? = null)
@Serializable
data class LavaOverview(val ok: Boolean = false, val lava: LavaBlock? = null)
@Serializable
data class LavaReply(val ok: Boolean = false, val checkout_id: Int = 0, val payment_url: String? = null,
    val status: String = "", val pro_until: String? = null, val error: String? = null)
@Serializable
data class ExitReply(val ok: Boolean = false, val available: Boolean = false, val accepted: Boolean = false,
    val percent: Int = 0, val expires_at: String? = null)

/** This transport and its consumers are compiled only into Direct. Headers are capability declarations, not identity. */
interface AndroidLavaApi {
    @Headers("X-HSK-Android-Channel: direct", "X-HSK-Lava-Capability: 1")
    @POST("api/v3/android/subscription/lava/overview")
    suspend fun providerOverview(@retrofit2.http.Header("Authorization") auth: String, @Body body: LavaContext): Response<LavaOverview>
    @Headers("X-HSK-Android-Channel: direct", "X-HSK-Lava-Capability: 1")
    @POST("api/v3/android/subscription/lava/start")
    suspend fun start(@retrofit2.http.Header("Authorization") auth: String, @Body body: LavaStart): Response<LavaReply>
    @Headers("X-HSK-Android-Channel: direct", "X-HSK-Lava-Capability: 1")
    @POST("api/v3/android/subscription/lava/status")
    suspend fun status(@retrofit2.http.Header("Authorization") auth: String, @Body body: LavaId): Response<LavaReply>
    @Headers("X-HSK-Android-Channel: direct", "X-HSK-Lava-Capability: 1")
    @POST("api/v3/android/subscription/lava/cancel")
    suspend fun cancel(@retrofit2.http.Header("Authorization") auth: String, @Body body: Map<String, String>): Response<LavaReply>
    @Headers("X-HSK-Android-Channel: direct", "X-HSK-Lava-Capability: 1")
    @POST("api/v3/android/subscription/lava/exit-offer")
    suspend fun exitOffer(@retrofit2.http.Header("Authorization") auth: String, @Body body: ExitAction): Response<ExitReply>
}

class LavaCheckoutRepository(private val api: AndroidLavaApi,
    private val token: suspend () -> ApiResult<String>, private val expired: suspend () -> Unit = {}, private val origin: String = "") {
    private suspend fun <T : Any> call(block: suspend (String) -> Response<T>): ApiResult<T> {
        val auth = when (val value = token()) {
            is ApiResult.Failure -> return value
            is ApiResult.Success -> "Bearer ${value.value}"
        }
        val result = withTimeoutOrNull(20_000) { apiCall { block(auth) } } ?: ApiResult.Failure(ApiError.Timeout)
        if (result is ApiResult.Failure && result.error is ApiError.SessionExpired) expired()
        return result
    }
    suspend fun providerOverview(mode: String) = call { api.providerOverview(it, LavaContext(mode, origin)) }
    suspend fun start(plan: String, email: String, mode: String, language: String) = call { api.start(it, LavaStart(plan, email, mode, language)) }
    suspend fun status(id: Int) = call { api.status(it, LavaId(id)) }
    suspend fun cancel() = call { api.cancel(it, emptyMap()) }
    suspend fun exitOffer(action: String) = call { api.exitOffer(it, ExitAction(action)) }
}
