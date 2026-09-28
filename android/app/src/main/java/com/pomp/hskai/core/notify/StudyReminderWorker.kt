package com.pomp.hskai.core.notify

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import com.pomp.hskai.HskAiApplication
import com.pomp.hskai.widget.WidgetPolicy
import java.util.concurrent.TimeUnit

/** WorkManager fallback for study reminders. FCM is the fast path. */
class StudyReminderWorker(
    context: Context,
    params: WorkerParameters,
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        val app = applicationContext as? HskAiApplication ?: return Result.success()
        return when (app.studyReminderCoordinator.run()) {
            StudyReminderCoordinator.Outcome.DONE -> Result.success()
            StudyReminderCoordinator.Outcome.RETRY -> Result.retry()
            StudyReminderCoordinator.Outcome.SESSION_EXPIRED -> {
                StudyReminderScheduler.cancel(applicationContext)
                Result.success()
            }
        }
    }
}

/** Enqueues and cancels the periodic fallback check. */
object StudyReminderScheduler {

    private const val WORK_NAME = "study_reminder_daily"

    fun schedule(context: Context) {
        val request = PeriodicWorkRequestBuilder<StudyReminderWorker>(
            WidgetPolicy.REFRESH_MINUTES,
            TimeUnit.MINUTES,
        )
            .addTag("widget-policy:${WidgetPolicy.SCHEDULE_VERSION}")
            .build()
        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            WORK_NAME,
            ExistingPeriodicWorkPolicy.UPDATE,
            request,
        )
    }

    fun cancel(context: Context) {
        WorkManager.getInstance(context).cancelUniqueWork(WORK_NAME)
    }
}
