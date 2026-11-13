package com.pomp.hskai.core.diagnostics

import java.util.UUID
import java.util.concurrent.Executor
import kotlin.coroutines.cancellation.CancellationException
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
 * device session ID, never an account ID; the server takes the account from
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
    fun report(
        feature: DiagFeature,
        failure: DiagFailure,
        site: DiagSite,
        category: String? = null,
        at: Long? = null,
        owner: String? = null,
    ) {
        try {
            val now = clock()
            if (now < state.pausedUntil) return
            val entry = QueuedDiagnostic(owner ?: state.owner.orEmpty(), now, event(feature, failure, site, category, at ?: now))
            executor.execute {
                runCatching {
                    queue.enqueue(entry, ::dropMarker)
                    onQueued()
                }
            }
        } catch (_: Throwable) {
            // Reporting must never affect the app.
        }
    }

    /** Sign-in: adopt pre-sign-in events, purge another account's. */
    fun bindOwner(owner: String) {
        if (owner.isBlank()) return
        state.owner = owner
        executor.execute {
            runCatching {
                queue.bind(owner)
                onQueued()
            }
        }
    }

    /** Logout, expiry or an account switch: the queue never outlives its session. */
    fun clearOwner() {
        state.owner = null
        executor.execute { runCatching { queue.purge() } }
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

    fun report(tag: DiagTag?, failure: DiagFailure) {
        if (tag != null) report(tag.feature, failure, tag.site)
    }

    fun report(feature: DiagFeature, failure: DiagFailure, site: DiagSite, category: String? = null) {
        reporter?.report(feature, failure, site, category)
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
    private val send: suspend (bearer: String, batch: DiagnosticBatchDto) -> Response<DiagnosticIntakeResponse>,
    private val clock: () -> Long = System::currentTimeMillis,
) {
    suspend fun flush(): FlushOutcome {
        val owner = state.owner ?: return FlushOutcome.DONE
        repeat(MAX_BATCHES) {
            val batch = queue.forOwner(owner, BATCH_SIZE)
            if (batch.isEmpty()) return FlushOutcome.DONE
            val bearer = token() ?: return FlushOutcome.DONE
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
                        state.pausedUntil = clock() + PAUSE_MILLIS
                        queue.purge()
                        return FlushOutcome.DONE
                    }
                }
                401, 403 -> {
                    queue.purge()
                    return FlushOutcome.DROPPED
                }
                in 500..599 -> return FlushOutcome.RETRY
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
