package com.pomp.hskai.feature.subscription

import com.pomp.hskai.HskAiApplication
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.core.network.apiCall
import com.pomp.hskai.core.diagnostics.DiagTags
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.launch
import kotlinx.coroutines.withTimeoutOrNull
import kotlinx.serialization.Serializable
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.Header
import retrofit2.http.Headers
import retrofit2.http.POST
import java.util.UUID

/** UI stages only. Invoice creation and paid are written by the server. */
interface ProCheckoutTelemetry {
    val attemptId: String
    val source: String
    fun record(event: String, plan: String? = null, method: String? = null)
    /** A late model must never attach the previous account's attempt to a new bearer. */
    fun ownsSession(token: String): Boolean = false
}

@Serializable
internal data class ProUiEvent(val event: String, val source: String, val attempt_id: String,
    val event_id: String, val plan_type: String? = null, val method: String? = null)
@Serializable
internal data class ProUiAck(val ok: Boolean = false, val recorded: Boolean = false)

internal interface AndroidProAnalyticsApi {
    @Headers("X-HSK-Android-Channel: direct", "X-HSK-Lava-Capability: 1")
    @POST("api/v3/android/subscription/inline-event")
    suspend fun event(@Header("Authorization") auth: String, @Body body: ProUiEvent): Response<ProUiAck>
}

internal data class ProEventSession(val token: String, val generation: Long)

/** Best effort, bounded, nonblocking and confined to the opening account.
 * Closing drains queued events in application scope; account replacement drops
 * them. There is no disk queue, raw content, automatic retry or flow dependency.
 */
internal class ProCheckoutReporter(
    override val attemptId: String, override val source: String, scope: CoroutineScope,
    private val initialSession: suspend () -> ProEventSession?,
    private val session: suspend () -> ProEventSession?,
    private val current: suspend (Long) -> Boolean,
    private val send: suspend (String, ProUiEvent) -> Unit,
) : ProCheckoutTelemetry {
    private val queue = Channel<ProUiEvent>(32)
    @Volatile private var ownerToken: String? = null
    init {
        scope.launch {
            try {
                val owner = withTimeoutOrNull(8_000) { initialSession() }
                if (owner == null) { queue.close(); return@launch }
                ownerToken = owner.token
                for (event in queue) {
                    withTimeoutOrNull(8_000) {
                        val proof = session() ?: return@withTimeoutOrNull
                        if (proof.generation == owner.generation && current(owner.generation)) {
                            ownerToken = proof.token
                            try { send(proof.token, event) }
                            catch (cancelled: CancellationException) { throw cancelled }
                            catch (_: Exception) { /* optional; never retry or block checkout */ }
                        }
                    }
                }
            } catch (cancelled: CancellationException) { throw cancelled }
            catch (_: Exception) { /* Observation failure has no checkout effect. */ }
            finally { queue.close() }
        }
    }
    override fun ownsSession(token: String): Boolean = ownerToken == token
    override fun record(event: String, plan: String?, method: String?) {
        if (event !in EVENTS) return
        val suffix = if (event in setOf("opened", "dismissed")) event else UUID.randomUUID().toString()
        queue.trySend(ProUiEvent("android_pro_$event", source, attemptId, "$attemptId:$suffix", plan, method))
    }
    fun close() { queue.close() }
    companion object {
        private val EVENTS = setOf("opened", "plan_selected", "more_opened", "method_selected",
            "exit_offered", "exit_claimed", "exit_declined", "dismissed", "checkout_failed")
    }
}

internal fun nativeProReporter(app: HskAiApplication, attemptId: String, source: String): ProCheckoutReporter {
    val auth = app.authRepository
    val openingState = auth.state.value
    val api = app.nativeApi(AndroidProAnalyticsApi::class.java)
    suspend fun proof(): ProEventSession? = (auth.authenticatedSession() as? ApiResult.Success)?.value
        ?.let { ProEventSession(it.token, it.generation) }
    return ProCheckoutReporter(attemptId, source, app.applicationScope,
        initialSession = { if (auth.state.value !== openingState) null else proof().takeIf { auth.state.value === openingState } },
        session = { proof() }, current = auth::sessionIsCurrent,
        send = { token, event -> apiCall(DiagTags.PAYMENT, token) { api.event("Bearer $token", event) } })
}
