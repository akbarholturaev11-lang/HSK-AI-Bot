package com.pomp.hskai.core.notify

import com.pomp.hskai.HskAiApplication
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.core.settings.DailyGoal
import com.pomp.hskai.widget.WidgetPolicy
import java.time.ZonedDateTime
import kotlinx.coroutines.flow.first

/**
 * One source of truth for deciding and posting an Android study reminder.
 *
 * FCM and WorkManager both call this class. FCM is the fast trigger; the
 * periodic worker is the fallback. Durable [WidgetStore.remindOnce] dedupe
 * means both can run without producing two notifications for the same day.
 */
class StudyReminderCoordinator(private val app: HskAiApplication) {

    enum class Outcome {
        DONE,
        RETRY,
        SESSION_EXPIRED,
    }

    suspend fun run(expectedLocalDay: String? = null): Outcome {
        val session = app.widgetStore.read()
        if (!session.linked || !session.reminderEnabled) return Outcome.DONE

        val now = ZonedDateTime.now()
        if (now.hour < WidgetPolicy.REMINDER_HOUR) return Outcome.DONE
        if (!StudyNotifications.canPost(app)) return Outcome.DONE

        val snapshot = when (val result = app.courseRepository.courseMap()) {
            is ApiResult.Success -> result.value
            is ApiResult.Failure -> {
                return if (result.error is ApiError.SessionExpired) {
                    Outcome.SESSION_EXPIRED
                } else {
                    Outcome.RETRY
                }
            }
        }

        if (snapshot.isStale) return Outcome.RETRY

        val map = snapshot.map
        val day = map.today?.localDay ?: map.progress.localDate
        if (
            day == null ||
            day != now.toLocalDate().toString() ||
            (expectedLocalDay != null && expectedLocalDay != day) ||
            map.today?.complete == true
        ) {
            return Outcome.DONE
        }

        app.widgetCoordinator.publish(snapshot, session.epoch)

        val reminder = ReminderDecision.decide(
            ReminderFacts(
                notificationsEnabled = true,
                dailyXp = map.progress.dailyXp,
                dailyGoal = map.today?.goalXp
                    ?: DailyGoal.sanitize(app.appSettings.dailyGoal.first()),
                streak = map.progress.streak,
                localDate = day,
                lastNotified = session.lastReminderDay,
            )
        )
        if (reminder == Reminder.NONE) return Outcome.DONE

        app.widgetStore.remindOnce(session.epoch, day) {
            StudyNotifications.postReminder(
                app,
                reminder,
                ReminderDecision.variant(day),
            )
        }
        return Outcome.DONE
    }
}
