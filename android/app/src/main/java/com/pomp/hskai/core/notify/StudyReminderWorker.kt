package com.pomp.hskai.core.notify

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import com.pomp.hskai.HskAiApplication
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.core.settings.DailyGoal
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.flow.first

/**
 * The daily reminder check.
 *
 * It gathers facts and hands them to [ReminderDecision]; the decision itself
 * lives outside Android so it can be tested on its own. Nothing is shown from
 * stale data: if the server cannot be reached the run is retried rather than
 * guessing at today's progress.
 */
class StudyReminderWorker(
    context: Context,
    params: WorkerParameters,
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        val app = applicationContext as? HskAiApplication ?: return Result.success()

        val snapshot = when (val result = app.courseRepository.courseMap()) {
            is ApiResult.Success -> result.value
            is ApiResult.Failure -> {
                // A dead session has nothing left to remind about.
                if (result.error is ApiError.SessionExpired) {
                    StudyReminderScheduler.cancel(applicationContext)
                    return Result.success()
                }
                return Result.retry()
            }
        }

        // A cached map may be hours old, and "XP earned today" is exactly the
        // number that goes wrong when it is. Wait for a fresh one instead.
        if (snapshot.isStale) return Result.retry()

        val map = snapshot.map
        if (!map.notificationsEnabled) {
            // The learner turned reminders off on another client.
            StudyReminderScheduler.cancel(applicationContext)
            StudyNotifications.cancelReminder(applicationContext)
            return Result.success()
        }

        val settings = app.appSettings
        val reminder = ReminderDecision.decide(
            ReminderFacts(
                notificationsEnabled = true,
                dailyXp = map.progress.dailyXp,
                dailyGoal = DailyGoal.sanitize(settings.dailyGoal.first()),
                streak = map.progress.streak,
                localDate = map.progress.localDate,
                lastNotified = settings.lastReminderDate.first(),
            )
        )
        if (reminder == Reminder.NONE) return Result.success()

        val posted = StudyNotifications.postReminder(applicationContext, reminder)
        if (posted) {
            // Only a delivered reminder consumes the day, so a revoked
            // permission does not silently burn today's single reminder.
            map.progress.localDate?.let { settings.setLastReminderDate(it) }
        }
        return Result.success()
    }
}

/** Enqueues and cancels the daily reminder check. */
object StudyReminderScheduler {

    private const val WORK_NAME = "study_reminder_daily"

    fun schedule(context: Context) {
        val request = PeriodicWorkRequestBuilder<StudyReminderWorker>(1, TimeUnit.DAYS)
            .setInitialDelay(ReminderSchedule.minutesUntilReminderHour(), TimeUnit.MINUTES)
            .build()
        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            WORK_NAME,
            // KEEP, so re-opening the app does not push the next run further
            // out every time and silently stop reminding anyone.
            ExistingPeriodicWorkPolicy.KEEP,
            request,
        )
    }

    fun cancel(context: Context) {
        WorkManager.getInstance(context).cancelUniqueWork(WORK_NAME)
    }
}
