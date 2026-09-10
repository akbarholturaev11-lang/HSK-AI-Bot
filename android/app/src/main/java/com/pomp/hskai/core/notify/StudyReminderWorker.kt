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
import com.pomp.hskai.widget.WidgetPolicy
import java.time.ZonedDateTime

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
        val session = app.widgetStore.read()
        if (!session.linked || !session.reminderEnabled) return Result.success()
        if (ZonedDateTime.now().hour < WidgetPolicy.REMINDER_HOUR) return Result.success()
        if (!StudyNotifications.canPost(applicationContext)) return Result.success()

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
        val now = ZonedDateTime.now()
        val day = map.today?.localDay ?: map.progress.localDate
        if (now.hour < WidgetPolicy.REMINDER_HOUR || day != now.toLocalDate().toString() ||
            map.today?.complete == true
        ) return Result.success()
        app.widgetCoordinator.publish(snapshot, session.epoch)

        val settings = app.appSettings
        val reminder = ReminderDecision.decide(
            ReminderFacts(
                notificationsEnabled = true,
                dailyXp = map.progress.dailyXp,
                dailyGoal = map.today?.goalXp ?: DailyGoal.sanitize(settings.dailyGoal.first()),
                streak = map.progress.streak,
                localDate = day,
                lastNotified = session.lastReminderDay,
            )
        )
        if (reminder == Reminder.NONE) return Result.success()

        app.widgetStore.remindOnce(session.epoch, day ?: return Result.success()) {
            StudyNotifications.postReminder(applicationContext, reminder)
        }
        return Result.success()
    }
}

/** Enqueues and cancels the daily reminder check. */
object StudyReminderScheduler {

    private const val WORK_NAME = "study_reminder_daily"

    fun schedule(context: Context) {
        // Hourly checks avoid a 24-hour interval drifting across DST. No post before 20:00.
        val request = PeriodicWorkRequestBuilder<StudyReminderWorker>(WidgetPolicy.REFRESH_MINUTES, TimeUnit.MINUTES)
            .addTag("widget-policy:${WidgetPolicy.SCHEDULE_VERSION}")
            .build()
        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            WORK_NAME,
            // UPDATE preserves the cadence, updates policy versions and never adds a second worker.
            ExistingPeriodicWorkPolicy.UPDATE,
            request,
        )
    }

    fun cancel(context: Context) {
        WorkManager.getInstance(context).cancelUniqueWork(WORK_NAME)
    }
}
