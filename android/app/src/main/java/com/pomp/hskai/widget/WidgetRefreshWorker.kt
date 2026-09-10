package com.pomp.hskai.widget

import android.appwidget.AppWidgetManager
import android.content.BroadcastReceiver
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import com.pomp.hskai.HskAiApplication
import com.pomp.hskai.core.notify.StudyReminderScheduler
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.launch

class WidgetRefreshWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        val app = applicationContext as HskAiApplication
        inputData.getString("pin_event_id")?.let {
            app.widgetStore.enqueue(AndroidWidgetEvent("android_widget_pinned", it))
        }
        if (WidgetScheduler.hasWidgets(app) && app.widgetStore.read().linked) app.widgetCoordinator.refresh()
        else WidgetScheduler.cancel(app)
        // A failed refresh still re-renders, so stale or a new local day is never shown as current.
        return Result.success()
    }
}

object WidgetScheduler {
    const val WORK_NAME = "smart_widget_refresh"
    private const val PREFS = "smart_widget_schedule"
    private const val VERSION = "version"
    fun hasWidgets(context: Context): Boolean = AppWidgetManager.getInstance(context)
        .getAppWidgetIds(ComponentName(context, HskAiWidgetReceiver::class.java)).isNotEmpty()

    fun schedule(context: Context) {
        if (!hasWidgets(context)) return
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        if (prefs.getInt(VERSION, -1) == WidgetPolicy.SCHEDULE_VERSION) return
        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            WORK_NAME,
            ExistingPeriodicWorkPolicy.UPDATE,
            PeriodicWorkRequestBuilder<WidgetRefreshWorker>(WidgetPolicy.REFRESH_MINUTES, TimeUnit.MINUTES)
                .addTag("widget-policy:${WidgetPolicy.SCHEDULE_VERSION}")
                .build(),
        )
        prefs.edit().putInt(VERSION, WidgetPolicy.SCHEDULE_VERSION).apply()
    }

    fun cancel(context: Context) {
        WorkManager.getInstance(context).cancelUniqueWork(WORK_NAME)
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().remove(VERSION).apply()
    }
}

/** Re-evaluate wall clock boundaries after time zone/clock changes or an APK update. */
class WidgetClockReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action !in setOf(Intent.ACTION_TIME_CHANGED, Intent.ACTION_TIMEZONE_CHANGED, Intent.ACTION_MY_PACKAGE_REPLACED)) return
        val pending = goAsync()
        val app = context.applicationContext as HskAiApplication
        app.applicationScope.launch {
            try {
                app.widgetCoordinator.render()
                WidgetScheduler.schedule(app)
                if (app.widgetStore.read().reminderEnabled) StudyReminderScheduler.schedule(app)
            } finally { pending.finish() }
        }
    }
}
