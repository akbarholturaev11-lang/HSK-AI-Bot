package com.pomp.hskai.core.notify

import com.pomp.hskai.HskAiApplication
import com.pomp.hskai.core.network.ApiError
import com.pomp.hskai.core.network.ApiResult
import com.pomp.hskai.core.network.apiCall
import com.pomp.hskai.data.api.AndroidSmartReminderApi
import android.os.SystemClock
import com.pomp.hskai.core.settings.DailyGoal
import com.pomp.hskai.widget.WidgetPolicy
import java.time.ZonedDateTime
import kotlinx.coroutines.flow.first

/**
 * One source of truth for deciding and posting an Android study reminder.
 *
 * FCM wakes the same worker used by periodic checks. Migrated links require
 * server claims and a durable journal; fresh non-migrated links retain the
 * existing local policy. WidgetStore guards both paths across account changes.
 */
class StudyReminderCoordinator(private val app: HskAiApplication, api: AndroidSmartReminderApi) {
    private val smart = SmartStudyBridge(app.widgetStore, app.authRepository::authenticatedSession,
        app.authRepository::withCurrentSession,
        mode = { apiCall { api.mode(it) } }, capability = { apiCall { api.capability(it) } },
        observe = { bearer, body -> apiCall { api.observe(bearer, body) } },
        due = { apiCall { api.due(it) } },
        claim = { bearer, job, body -> apiCall { api.claim(bearer, job, body) } },
        receipt = { bearer, job, body -> apiCall { api.receipt(bearer, job, body) } },
        permission = { StudyNotifications.canPost(app) },
        post = { day -> StudyNotifications.postReminderOutcome(app, Reminder.DAILY_GOAL, ReminderDecision.variant(day)) },
        elapsed = SystemClock::elapsedRealtime)

    internal suspend fun receive(hint: SmartStudyHint): Outcome = when (smart.run(hint)) {
        SmartStudyBridge.Result.RETRY -> Outcome.RETRY
        else -> Outcome.DONE
    }


    enum class Outcome {
        DONE,
        RETRY,
        SESSION_EXPIRED,
    }

    suspend fun run(expectedLocalDay: String? = null): Outcome {
        val triggerEpoch = app.widgetStore.read().epoch
        when (smart.run(legacyHint = expectedLocalDay != null)) {
            SmartStudyBridge.Result.DONE -> return Outcome.DONE
            SmartStudyBridge.Result.RETRY -> return Outcome.RETRY
            SmartStudyBridge.Result.LEGACY -> Unit
        }
        val session = app.widgetStore.read()
        if (!session.linked || !session.reminderEnabled || session.epoch != triggerEpoch) return Outcome.DONE

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
