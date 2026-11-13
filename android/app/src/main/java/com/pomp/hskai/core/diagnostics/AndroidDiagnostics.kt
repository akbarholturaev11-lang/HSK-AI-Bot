package com.pomp.hskai.core.diagnostics

import android.app.ActivityManager
import android.content.Context
import android.content.SharedPreferences
import android.os.Build
import androidx.annotation.RequiresApi
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import com.pomp.hskai.BuildConfig
import com.pomp.hskai.HskAiApplication
import java.io.File
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import kotlinx.serialization.json.Json

/**
 * Android wiring of the reporter (design D5), the same for both flavours:
 * crash handler, exit reasons, the owner-bound queue in `noBackupFilesDir` and
 * the unique WorkManager flush. `channel` tells Play and Direct receipts apart.
 */
class AndroidDiagnostics(
    private val context: Context,
    api: () -> AndroidDiagnosticsApi,
    token: suspend () -> String?,
) {
    private val json = Json { ignoreUnknownKeys = true; explicitNulls = false }
    private val dir = File(context.noBackupFilesDir, "diagnostics")
    private val started = AtomicBoolean(false)
    private val collected = AtomicBoolean(false)
    private val executor = Executors.newSingleThreadExecutor { task ->
        Thread(task, "hsk-diagnostics").apply { isDaemon = true }
    }

    val state: DiagnosticState = PrefsDiagnosticState(context.getSharedPreferences(PREFS, Context.MODE_PRIVATE))
    private val previousProcessOwner = state.owner
    private val queue = DiagnosticQueue(AtomicDiagnosticFile(File(dir, "queue.json")), json)
    private val crashes = CrashRecorder(AtomicDiagnosticFile(File(dir, "crash.json")), json, state)
    val reporter = DiagnosticReporter(
        queue = queue,
        state = state,
        appVersion = BuildConfig.VERSION_NAME,
        build = BuildConfig.VERSION_CODE.toLong(),
        channel = BuildConfig.DISTRIBUTION_CHANNEL,
        executor = executor,
        onQueued = ::scheduleFlush,
    )
    private val diagnosticsApi by lazy(api)
    val uploader = DiagnosticUploader(
        queue, state, token, send = { bearer, batch -> diagnosticsApi.send(bearer, batch) },
    )

    /** First thing in `Application.onCreate`: the crash handler and the reporter. */
    fun start() {
        if (!started.compareAndSet(false, true)) return
        crashes.install()
        Diagnostics.reporter = reporter
    }

    /** After the first frame: last crash record, exit reasons, then a flush. */
    fun afterFirstFrame() {
        if (!collected.compareAndSet(false, true)) return
        executor.execute {
            runCatching { crashes.collect(reporter) }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) runCatching { reportExitReasons() }
            scheduleFlush()
        }
    }

    fun bindToken(token: String) = reporter.bindOwner(diagnosticSessionId(token))

    fun clearOwner(keepPreSignIn: Boolean = false) = reporter.clearOwner(keepPreSignIn)

    @RequiresApi(Build.VERSION_CODES.R)
    private fun reportExitReasons() {
        val manager = context.getSystemService(ActivityManager::class.java) ?: return
        val exits = manager.getHistoricalProcessExitReasons(context.packageName, 0, MAX_EXITS)
            .map { ExitRecord(it.reason, it.timestamp) }
        ExitReasons.report(exits, state, reporter, System.currentTimeMillis(), previousProcessOwner)
    }

    private fun scheduleFlush() {
        if (state.owner == null) return
        runCatching {
            WorkManager.getInstance(context).enqueueUniqueWork(
                WORK_NAME,
                ExistingWorkPolicy.KEEP,
                OneTimeWorkRequestBuilder<DiagnosticFlushWorker>()
                    .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
                    .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, BACKOFF_SECONDS, TimeUnit.SECONDS)
                    .build(),
            )
        }
    }

    companion object {
        const val WORK_NAME = "diagnostics_flush"
        private const val PREFS = "diagnostics"
        private const val MAX_EXITS = 10
        private const val BACKOFF_SECONDS = 30L
    }
}

class DiagnosticFlushWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        val app = applicationContext as HskAiApplication
        val outcome = try {
            app.diagnostics.uploader.flush()
        } catch (cancelled: kotlin.coroutines.cancellation.CancellationException) {
            throw cancelled
        } catch (_: Exception) {
            FlushOutcome.RETRY
        }
        return if (shouldRetryFlush(outcome, runAttemptCount)) Result.retry() else Result.success()
    }
}

private class PrefsDiagnosticState(private val prefs: SharedPreferences) : DiagnosticState {
    override var owner: String?
        get() = prefs.getString(OWNER, null)
        set(value) = prefs.edit().apply { if (value == null) remove(OWNER) else putString(OWNER, value) }.apply()
    override var pausedUntil: Long
        get() = prefs.getLong(PAUSED_UNTIL, 0L)
        set(value) = prefs.edit().putLong(PAUSED_UNTIL, value).apply()
    override var lastExitSeen: Long
        get() = prefs.getLong(LAST_EXIT_SEEN, 0L)
        set(value) = prefs.edit().putLong(LAST_EXIT_SEEN, value).apply()
    override var lastCrashAt: Long
        get() = prefs.getLong(LAST_CRASH_AT, 0L)
        set(value) = prefs.edit().putLong(LAST_CRASH_AT, value).apply()

    private companion object {
        const val OWNER = "owner"
        const val PAUSED_UNTIL = "paused_until"
        const val LAST_EXIT_SEEN = "last_exit_seen"
        const val LAST_CRASH_AT = "last_crash_at"
    }
}
