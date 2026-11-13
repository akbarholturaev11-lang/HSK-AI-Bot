package com.pomp.hskai.core.diagnostics

import java.util.Base64
import java.util.UUID
import java.util.concurrent.Executor
import kotlin.coroutines.cancellation.CancellationException
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import retrofit2.Response

/** Small persisted state; the app keeps it in SharedPreferences. */
interface DiagnosticState {
    /** The signed-in device session ID, or null when signed out. */
    var owner: String?
    /** The server answered `paused` (mode off): nothing is queued until then. */
    var pausedUntil: Long
    /** Newest process-exit timestamp already looked at (API ≥ 30). */
    var lastExitSeen: Long
    /** When the last crash record was written, to skip its duplicate exit reason. */
    var lastCrashAt: Long
}

/**
 * Turns a failure into a queued `diag.v1` event. Never throws and never blocks
 * the caller: disk work runs on [executor]. The owner stamp is the signed-in
 * bearer session ID, never an account ID; the server takes the account from
 * the bearer session.
 */
class DiagnosticReporter(
    private val queue: DiagnosticQueue,
    private val state: DiagnosticState,
    private val appVersion: String,
    private val build: Long,
    private val channel: String,
    private val executor: Executor,
    private val clock: () -> Long = System::currentTimeMillis,
    private val onQueued: () -> Unit = {},
) {
    internal data class Scope(val owner: String?, val generation: Long)

    // State is changed synchronously by auth; the generation also separates
    // signed-out periods (null → a session → null) for late call failures.
    private var generation = 0L

    internal fun scope(token: String? = null): Scope? = synchronized(state) {
        val owner = state.owner
        if (token != null && (owner == null || diagnosticSessionId(token) != owner)) null
        else Scope(owner, generation)
    }

    fun report(
        feature: DiagFeature,
        failure: DiagFailure,
        site: DiagSite,
        category: String? = null,
        at: Long? = null,
        owner: String? = null,
    ) = report(feature, failure, site, category, at, scope()?.takeIf { owner == null || it.owner.orEmpty() == owner })

    internal fun report(
        feature: DiagFeature,
        failure: DiagFailure,
        site: DiagSite,
        category: String?,
        at: Long?,
        scope: Scope?,
        token: String? = null,
    ) {
        if (scope == null) return
        try {
            synchronized(state) {
                val now = clock()
                if (scope != this.scope(token) || now < state.pausedUntil) return
                val entry = QueuedDiagnostic(scope.owner.orEmpty(), now, event(feature, failure, site, category, at ?: now))
                executor.execute {
                    runCatching {
                        if (now < state.pausedUntil) return@runCatching
                        queue.enqueue(entry, ::dropMarker)
                        onQueued()
                    }
                }
            }
        } catch (_: Throwable) {
            // Reporting must never affect the app.
        }
    }

    /** Sign-in: adopt pre-sign-in events, purge another session's. */
    fun bindOwner(owner: String?) = synchronized(state) {
        if (owner == null) {
            clearOwner()
            return@synchronized
        }
        if (state.owner != owner) {
            generation++
            state.owner = owner
        }
        // Also resume a queued flush when the same session has a fresh token.
        executor.execute {
            runCatching {
                queue.bind(owner)
                onQueued()
            }
        }
    }

    /** Logout, expiry or an account switch: the queue never outlives its session. */
    fun clearOwner(keepPreSignIn: Boolean = false) = synchronized(state) {
        val oldOwner = state.owner
        generation++
        state.owner = null
        executor.execute {
            runCatching {
                if (keepPreSignIn && oldOwner == null) queue.keepPreSignIn()
                else queue.purge()
            }
        }
    }

    private fun event(feature: DiagFeature, failure: DiagFailure, site: DiagSite, category: String?, at: Long) =
        DiagnosticEventDto(
            eventId = UUID.randomUUID().toString(),
            clientTime = at,
            appVersion = appVersion,
            build = build,
            channel = channel,
            featureCode = feature.code,
            failureCode = failure.code,
            siteCode = site.code,
            outcome = "failed",
            category = category,
        )

    private fun dropMarker(owner: String) = QueuedDiagnostic(
        owner, clock(), event(DiagFeature.MONITORING, DiagFailure.QUEUE_DROPPED, DiagSite.QUEUE, null, clock()),
    )
}

/** The process-wide entry point used by `apiCall` and `LiveVoiceSocket`. */
object Diagnostics {
    @Volatile
    var reporter: DiagnosticReporter? = null

    internal fun scope(token: String? = null): DiagnosticReporter.Scope? =
        runCatching { reporter?.scope(token) }.getOrNull()

    internal fun report(
        scope: DiagnosticReporter.Scope?,
        feature: DiagFeature,
        failure: DiagFailure,
        site: DiagSite,
        token: String? = null,
    ) {
        reporter?.report(feature, failure, site, category = null, at = null, scope = scope, token = token)
    }

}

/** The feature of the screen in front, for the crash record. */
object DiagnosticContext {
    @Volatile
    var feature: DiagFeature = DiagFeature.APP_SHELL
}

enum class FlushOutcome { DONE, RETRY, DROPPED }

/**
 * Sends the owner's queue in batches of [BATCH_SIZE]. A 2xx removes the batch
 * (a `paused` answer also pauses reporting for 24 hours and empties the
 * queue); 401/403 drops the whole queue; another 4xx drops the batch (it can
 * never succeed); a 5xx or a transport error is retried by WorkManager.
 */
class DiagnosticUploader(
    private val queue: DiagnosticQueue,
    private val state: DiagnosticState,
    private val token: suspend () -> String?,
    private val sessionId: (String) -> String? = ::diagnosticSessionId,
    private val send: suspend (bearer: String, batch: DiagnosticBatchDto) -> Response<DiagnosticIntakeResponse>,
    private val clock: () -> Long = System::currentTimeMillis,
) {
    suspend fun flush(): FlushOutcome {
        val owner = synchronized(state) { state.owner } ?: return FlushOutcome.DONE
        if (clock() < state.pausedUntil) return FlushOutcome.DONE
        repeat(MAX_BATCHES) {
            if (state.owner != owner) return FlushOutcome.DONE
            val batch = queue.forOwner(owner, BATCH_SIZE)
            if (batch.isEmpty()) return FlushOutcome.DONE
            val bearer = token() ?: return FlushOutcome.DONE
            // A device ID can be re-used for another account. Only the exact
            // server-issued session may carry these entries; no refresh here.
            if (sessionId(bearer) != owner || state.owner != owner) return FlushOutcome.DONE
            val response = try {
                send("Bearer $bearer", DiagnosticBatchDto(DIAG_SCHEMA, batch.map { it.event }))
            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (_: Exception) {
                return FlushOutcome.RETRY
            }
            response.errorBody()?.close()
            val ids = batch.mapTo(mutableSetOf()) { it.event.eventId }
            when (response.code()) {
                in 200..299 -> {
                    queue.remove(ids)
                    if (response.body()?.paused == true) {
                        synchronized(state) {
                            if (state.owner == owner) state.pausedUntil = clock() + PAUSE_MILLIS
                        }
                        queue.purgeOwner(owner)
                        return FlushOutcome.DONE
                    }
                }
                401, 403 -> {
                    queue.purgeOwner(owner)
                    return FlushOutcome.DROPPED
                }
                in 500..599 -> return if (state.owner == owner) FlushOutcome.RETRY else FlushOutcome.DONE
                else -> queue.remove(ids)
            }
        }
        return FlushOutcome.DONE
    }

    companion object {
        const val BATCH_SIZE = 20
        const val MAX_BATCHES = 3
        const val PAUSE_MILLIS = 24L * 60 * 60 * 1000
        const val MAX_ATTEMPTS = 3
    }
}

/** WorkManager mapping: at most [DiagnosticUploader.MAX_ATTEMPTS] attempts. */
fun shouldRetryFlush(outcome: FlushOutcome, runAttemptCount: Int): Boolean =
    outcome == FlushOutcome.RETRY && runAttemptCount + 1 < DiagnosticUploader.MAX_ATTEMPTS

/**
 * Read the opaque session ID from a token already returned by the auth API.
 * This is an additional local mismatch guard; only the server verifies or
 * authenticates the bearer. Do not keep the token or any other claim here.
 */
internal fun diagnosticSessionId(token: String): String? = runCatching {
    if (token.length > 4096) return null
    val parts = token.split('.', limit = 4)
    if (parts.size != 3) return null
    val payload = Base64.getUrlDecoder().decode(parts[1]).decodeToString()
    val sid = Json.parseToJsonElement(payload).jsonObject["sid"]?.jsonPrimitive?.content ?: return null
    UUID.fromString(sid).toString().takeIf { it == sid }
}.getOrNull()
