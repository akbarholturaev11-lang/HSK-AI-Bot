package com.pomp.hskai.feature.update

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkInfo
import androidx.work.WorkManager
import androidx.work.Worker
import androidx.work.WorkerParameters
import com.pomp.hskai.BuildConfig
import java.util.concurrent.TimeUnit
import org.junit.Assert.assertEquals
import org.junit.Assume.assumeFalse
import org.junit.Test
import org.junit.runner.RunWith

/** Persisted Direct jobs must not survive a same-package Play update. */
@RunWith(AndroidJUnit4::class)
class PlayUpdateMigrationTest {
    @Test
    fun cancelsDirectChecksAndPerVersionDownloads() {
        assumeFalse(BuildConfig.EXTERNAL_CHECKOUT_ENABLED)
        val context = ApplicationProvider.getApplicationContext<Context>()
        val manager = WorkManager.getInstance(context)
        val check = PeriodicWorkRequestBuilder<LegacyUpdateFixtureWorker>(1, TimeUnit.DAYS)
            .setInitialDelay(1, TimeUnit.DAYS)
            .addTag("com.pomp.hskai.feature.update.UpdateCheckWorker")
            .build()
        val startup = OneTimeWorkRequestBuilder<LegacyUpdateFixtureWorker>()
            .setInitialDelay(1, TimeUnit.DAYS)
            .addTag("com.pomp.hskai.feature.update.UpdateCheckWorker")
            .build()
        val download = OneTimeWorkRequestBuilder<LegacyUpdateFixtureWorker>()
            .setInitialDelay(1, TimeUnit.DAYS)
            .addTag("com.pomp.hskai.feature.update.UpdateDownloadWorker")
            .build()
        val unrelated = OneTimeWorkRequestBuilder<LegacyUpdateFixtureWorker>()
            .setInitialDelay(1, TimeUnit.DAYS)
            .build()
        val requests = listOf(check.id, startup.id, download.id)
        try {
            manager.enqueueUniquePeriodicWork("app_update_check_daily", ExistingPeriodicWorkPolicy.REPLACE, check)
                .result.get(10, TimeUnit.SECONDS)
            manager.enqueueUniqueWork("app_update_check_now", ExistingWorkPolicy.REPLACE, startup)
                .result.get(10, TimeUnit.SECONDS)
            manager.enqueueUniqueWork("android_update_download_123456789", ExistingWorkPolicy.REPLACE, download)
                .result.get(10, TimeUnit.SECONDS)
            manager.enqueue(unrelated).result.get(10, TimeUnit.SECONDS)

            UpdateWatch.schedule(context)

            requests.forEach { id ->
                assertEquals(WorkInfo.State.CANCELLED, manager.getWorkInfoById(id).get(10, TimeUnit.SECONDS)?.state)
            }
            assertEquals(
                "Study and account work must survive the channel migration",
                WorkInfo.State.ENQUEUED,
                manager.getWorkInfoById(unrelated.id).get(10, TimeUnit.SECONDS)?.state,
            )
        } finally {
            (requests + unrelated.id).forEach { manager.cancelWorkById(it).result.get(10, TimeUnit.SECONDS) }
        }
    }
}

/** The initial delay prevents execution; the test inspects actual WorkManager persistence. */
class LegacyUpdateFixtureWorker(context: Context, parameters: WorkerParameters) : Worker(context, parameters) {
    override fun doWork(): Result = Result.success()
}
