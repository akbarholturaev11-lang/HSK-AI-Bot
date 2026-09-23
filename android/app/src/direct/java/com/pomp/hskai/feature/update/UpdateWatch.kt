package com.pomp.hskai.feature.update

import android.content.Context
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Asking the server whether a newer build exists, away from any screen.
 *
 * Until this, an installed app only ever learned about a release when someone
 * happened to open the profile. Two checks now cover the rest: one when the
 * app starts, and one a day in the background, so the notification arrives
 * even from a phone that has not been opened this week.
 *
 * Nothing here downloads or installs anything — the check ends at a
 * notification, and the install is still a tap the learner makes.
 */
object UpdateWatch {

    private const val DAILY_WORK = "app_update_check_daily"
    private const val STARTUP_WORK = "app_update_check_now"

    fun schedule(context: Context) {
        val manager = WorkManager.getInstance(context)
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()

        manager.enqueueUniquePeriodicWork(
            DAILY_WORK,
            // UPDATE keeps the cadence and never adds a second worker.
            ExistingPeriodicWorkPolicy.UPDATE,
            PeriodicWorkRequestBuilder<UpdateCheckWorker>(1, TimeUnit.DAYS)
                .setConstraints(constraints)
                .build(),
        )

        // KEEP only protects work that is still pending or running, so each
        // launch after the last check finished queues a fresh one — and a
        // launch during one does not pile a second check on top of it.
        manager.enqueueUniqueWork(
            STARTUP_WORK,
            ExistingWorkPolicy.KEEP,
            OneTimeWorkRequestBuilder<UpdateCheckWorker>()
                .setConstraints(constraints)
                .build(),
        )
    }

    fun cancel(context: Context) {
        val manager = WorkManager.getInstance(context)
        manager.cancelUniqueWork(DAILY_WORK)
        manager.cancelUniqueWork(STARTUP_WORK)
    }
}

/**
 * One check: what the server says, handed to [UpdateNotices].
 *
 * A failure is a plain success here rather than a retry. The next launch and
 * the next day both check again, and a phone that retries a release check on a
 * flaky connection spends battery on news that keeps until tomorrow.
 */
class UpdateCheckWorker(
    context: Context,
    params: WorkerParameters,
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        val release = withContext(Dispatchers.IO) { fetchRelease(applicationContext) } ?: return Result.success()
        UpdateNotices.announce(context = applicationContext, release = release)
        return Result.success()
    }
}
