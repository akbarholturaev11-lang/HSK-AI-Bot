package com.pomp.hskai.core.diagnostics

import kotlin.math.abs
import kotlinx.serialization.json.Json

/**
 * Wraps the default uncaught-exception handler (design D5). On a crash it
 * synchronously writes one ≤ 1 KB record — feature, crash bucket, owner and
 * time, never the message or stack — then delegates to the previous handler.
 * It makes no network call. The next start turns the record into an event.
 */
class CrashRecorder(
    private val store: DiagnosticFileStore,
    private val json: Json,
    private val state: DiagnosticState,
    private val feature: () -> DiagFeature = { DiagnosticContext.feature },
    private val clock: () -> Long = System::currentTimeMillis,
) {
    fun install() {
        val previous = Thread.getDefaultUncaughtExceptionHandler()
        if (previous is Handler) return
        Thread.setDefaultUncaughtExceptionHandler(Handler(previous))
    }

    inner class Handler(private val previous: Thread.UncaughtExceptionHandler?) : Thread.UncaughtExceptionHandler {
        override fun uncaughtException(thread: Thread, error: Throwable) {
            try {
                record(error)
            } catch (_: Throwable) {
                // The previous handler must run whatever happens here.
            }
            previous?.uncaughtException(thread, error)
        }
    }

    internal fun record(error: Throwable) {
        if (clock() < state.pausedUntil) return
        val (site, category) = crashBucket(error)
        val record = CrashRecordDto(state.owner.orEmpty(), clock(), feature().code, site.code, category)
        val bytes = json.encodeToString(CrashRecordDto.serializer(), record).encodeToByteArray()
        if (bytes.size <= MAX_RECORD_BYTES) store.write(bytes)
    }

    /** Next start: one `crash_uncaught` event for the same owner; another owner's record is dropped. */
    fun collect(reporter: DiagnosticReporter) {
        val bytes = runCatching { store.read() }.getOrNull() ?: return
        runCatching { store.delete() }
        val record = runCatching { json.decodeFromString(CrashRecordDto.serializer(), bytes.decodeToString()) }
            .getOrNull() ?: return
        state.lastCrashAt = record.at
        if (record.owner != state.owner.orEmpty() || clock() - record.at !in 0 until DiagnosticQueue.TTL_MILLIS) return
        val feature = DiagFeature.entries.firstOrNull { it.code == record.feature } ?: DiagFeature.APP_SHELL
        val site = DiagSite.entries.firstOrNull { it.code == record.site } ?: DiagSite.EXC_OTHER
        reporter.report(feature, DiagFailure.CRASH_UNCAUGHT, site, record.category, at = record.at, owner = record.owner)
    }

    companion object {
        const val MAX_RECORD_BYTES = 1024
    }
}

/** A process exit as `ActivityManager.getHistoricalProcessExitReasons` reports it (API ≥ 30). */
data class ExitRecord(val reason: Int, val timestamp: Long)

object ExitReasons {
    // android.app.ApplicationExitInfo constants (API 30), copied so older
    // devices and JVM tests never touch the class.
    const val REASON_CRASH = 4
    const val REASON_CRASH_NATIVE = 5
    const val REASON_ANR = 6

    /** A JVM crash the crash handler already recorded is not reported twice. */
    private const val SAME_CRASH_WINDOW_MILLIS = 60_000L

    /** Exits newer than [lastSeen] mapped to failures, each reported once. */
    fun select(exits: List<ExitRecord>, lastSeen: Long, lastCrashAt: Long): List<Pair<DiagFailure, Long>> =
        exits.filter { it.timestamp > lastSeen }.sortedBy { it.timestamp }.mapNotNull { exit ->
            val failure = when (exit.reason) {
                REASON_CRASH -> DiagFailure.CRASH_UNCAUGHT.takeUnless {
                    lastCrashAt > 0 && abs(exit.timestamp - lastCrashAt) <= SAME_CRASH_WINDOW_MILLIS
                }
                REASON_CRASH_NATIVE -> DiagFailure.CRASH_NATIVE
                REASON_ANR -> DiagFailure.ANR
                else -> null
            }
            failure?.let { it to exit.timestamp }
        }

    /**
     * Reports new exits and advances the last-seen mark. The first run only
     * sets the mark, so exits from before this reporter existed are not sent.
     */
    fun report(
        exits: List<ExitRecord>,
        state: DiagnosticState,
        reporter: DiagnosticReporter,
        now: Long,
        previousProcessOwner: String? = state.owner,
    ) {
        val lastSeen = state.lastExitSeen
        val newest = exits.maxOfOrNull { it.timestamp } ?: now
        if (lastSeen <= 0L) {
            state.lastExitSeen = newest
            return
        }
        // OS exit records are package-wide. Never assign them to an account
        // that signed in after this process started.
        if (previousProcessOwner != null && previousProcessOwner == state.owner) {
            select(exits, maxOf(lastSeen, now - DiagnosticQueue.TTL_MILLIS), state.lastCrashAt)
                .filter { (_, at) -> at <= now }
                .forEach { (failure, at) ->
                    reporter.report(DiagFeature.APP_SHELL, failure, DiagSite.PROCESS, at = at, owner = previousProcessOwner)
                }
        }
        if (newest > lastSeen) state.lastExitSeen = newest
    }
}
