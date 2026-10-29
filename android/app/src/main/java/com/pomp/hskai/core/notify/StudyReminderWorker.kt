package com.pomp.hskai.core.notify

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import androidx.work.Data
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.Constraints
import androidx.work.NetworkType
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
        val hintedJob = inputData.getString("smart_job_id")
        val outcome = if (hintedJob == null) app.studyReminderCoordinator.run() else {
            val hint = SmartStudyHint.parse(mapOf("version" to "1", "job_id" to hintedJob,
                "local_day" to inputData.getString("smart_local_day").orEmpty())) ?: return Result.success()
            app.studyReminderCoordinator.receive(hint)
        }
        return when (outcome) {
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
    private const val HINT_TAG = "smart_study_hints"

    /** FCM only wakes durable work; the payload cannot authorize a notification. */
    internal fun hint(context: Context, hint: SmartStudyHint) {
        val request = OneTimeWorkRequestBuilder<StudyReminderWorker>()
            .setInputData(Data.Builder().putString("smart_job_id", hint.jobId)
                .putString("smart_local_day", hint.localDay).build())
            .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
            .addTag(HINT_TAG).build()
        WorkManager.getInstance(context).enqueueUniqueWork("smart-study:${hint.jobId}", ExistingWorkPolicy.KEEP, request)
    }

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
        WorkManager.getInstance(context).cancelAllWorkByTag(HINT_TAG)
    }
}
