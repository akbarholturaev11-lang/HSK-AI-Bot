package com.pomp.hskai.widget

import android.appwidget.AppWidgetManager
import android.content.Context
import android.content.res.Configuration
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.unit.DpSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.glance.GlanceId
import androidx.glance.GlanceModifier
import androidx.glance.Image
import androidx.glance.ImageProvider
import androidx.glance.LocalSize
import androidx.glance.action.clickable
import androidx.glance.appwidget.GlanceAppWidget
import androidx.glance.appwidget.GlanceAppWidgetReceiver
import androidx.glance.appwidget.SizeMode
import androidx.glance.appwidget.action.actionStartActivity
import androidx.glance.appwidget.appWidgetBackground
import androidx.glance.appwidget.cornerRadius
import androidx.glance.appwidget.provideContent
import androidx.glance.background
import androidx.glance.layout.*
import androidx.glance.text.FontWeight
import androidx.glance.text.Text
import androidx.glance.text.TextStyle
import androidx.glance.unit.ColorProvider
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.workDataOf
import com.pomp.hskai.HskAiApplication
import com.pomp.hskai.R
import com.pomp.hskai.core.design.PompColors
import com.pomp.hskai.core.i18n.AppLocale
import com.pomp.hskai.core.settings.AppThemeMode
import java.util.UUID
import kotlinx.coroutines.flow.first

class HskAiSmartWidget : GlanceAppWidget() {
    override val sizeMode = SizeMode.Responsive(setOf(DpSize(130.dp, 48.dp), DpSize(130.dp, 110.dp), DpSize(260.dp, 110.dp)))

    override suspend fun provideGlance(context: Context, id: GlanceId) {
        val app = context.applicationContext as HskAiApplication
        val initial = app.widgetStore.read()
        val initialTheme = app.appSettings.themeMode.first()
        provideContent {
            val session by app.widgetStore.state.collectAsState(initial)
            val theme by app.appSettings.themeMode.collectAsState(initialTheme)
            // Widget updates are explicit; the state flow is the only source of the snapshot.
            val now = remember(session.snapshot) { java.time.ZonedDateTime.now() }
            val dark = theme == AppThemeMode.DARK || (theme == AppThemeMode.SYSTEM &&
                context.resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK == Configuration.UI_MODE_NIGHT_YES)
            WidgetContent(AppLocale.wrap(context), session, WidgetStateResolver.resolve(session.linked, session.snapshot, now), dark)
        }
    }
}

/** No scheduling, network calls or access decisions in the view. */
@Composable
internal fun WidgetContent(context: Context, session: WidgetSession, mood: WidgetMood, dark: Boolean) {
    val size = LocalSize.current
    val compact = size.height < 110.dp
    val wide = size.width >= 260.dp
    val palette = PompColors.paletteFor(dark)
    val title = context.getString(when (mood) {
        WidgetMood.UNLINKED -> R.string.widget_unlinked
        WidgetMood.STALE -> R.string.widget_stale
        WidgetMood.FOUNDATION -> R.string.widget_foundation
        WidgetMood.COMPLETE -> R.string.widget_complete
        WidgetMood.STREAK -> R.string.widget_streak
        WidgetMood.CONTINUE -> R.string.widget_continue
    })
    val art = when (mood) {
        WidgetMood.COMPLETE -> R.drawable.widget_panda_celebrate
        WidgetMood.STREAK -> R.drawable.widget_panda_streak
        WidgetMood.CONTINUE, WidgetMood.FOUNDATION -> R.drawable.widget_panda_invite
        else -> R.drawable.widget_panda_calm
    }
    val fresh = mood != WidgetMood.UNLINKED && mood != WidgetMood.STALE
    val snapshot = session.snapshot
    val stats = if (fresh && snapshot != null) context.getString(R.string.widget_stats, snapshot.xp, snapshot.streak)
        else context.getString(R.string.widget_open)
    val lesson = if (fresh && snapshot?.lessonOrder != null)
        context.getString(R.string.widget_lesson, snapshot.level.uppercase(), snapshot.lessonOrder) else "HSK AI"
    // Every tap goes through CurrentLesson; MainActivity performs the fresh bearer/access check.
    val action = actionStartActivity(WidgetIntents.open(context, "widget"))
    Row(
        modifier = GlanceModifier.fillMaxSize().appWidgetBackground().background(palette.paper)
            .cornerRadius(20.dp).clickable(action).padding(if (wide) 12.dp else 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        if (compact || wide) {
            Image(ImageProvider(art), title, GlanceModifier.size(if (compact) 28.dp else 90.dp))
            Spacer(GlanceModifier.width(if (compact) 6.dp else 12.dp))
        }
        Column(GlanceModifier.defaultWeight(), verticalAlignment = Alignment.CenterVertically) {
            if (!compact) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    if (!wide) {
                        Image(ImageProvider(art), null, GlanceModifier.size(30.dp))
                        Spacer(GlanceModifier.width(4.dp))
                    }
                    Text(lesson, style = TextStyle(color = ColorProvider(palette.cinnabar), fontSize = 11.sp, fontWeight = FontWeight.Bold), maxLines = 2)
                }
                Spacer(GlanceModifier.height(4.dp))
            }
            val heading = if (compact && fresh && snapshot?.lessonOrder != null)
                context.getString(R.string.widget_lesson_short, snapshot.lessonOrder) else title
            Text(heading, style = TextStyle(color = ColorProvider(palette.ink), fontSize = (if (compact) 12 else 15).sp, fontWeight = FontWeight.Bold), maxLines = if (compact) 1 else 2)
            Text(stats, style = TextStyle(color = ColorProvider(palette.inkSecondary), fontSize = 11.sp), maxLines = 1)
        }
    }
}

class HskAiWidgetReceiver : GlanceAppWidgetReceiver() {
    override val glanceAppWidget = HskAiSmartWidget()

    override fun onUpdate(context: Context, appWidgetManager: AppWidgetManager, appWidgetIds: IntArray) {
        // Only actual provider IDs mean "pinned". Dispatching a pin request is not success.
        val prefs = context.getSharedPreferences("widget_installations", Context.MODE_PRIVATE)
        val actual = appWidgetManager.getAppWidgetIds(android.content.ComponentName(context, javaClass)).toSet()
        appWidgetIds.filter { it in actual && !prefs.contains(it.toString()) }.forEach { id ->
            val eventId = UUID.randomUUID().toString()
            prefs.edit().putBoolean(id.toString(), true).apply()
            WorkManager.getInstance(context).enqueueUniqueWork(
                "widget-pin-$eventId", ExistingWorkPolicy.KEEP,
                OneTimeWorkRequestBuilder<WidgetRefreshWorker>().setInputData(workDataOf("pin_event_id" to eventId)).build(),
            )
        }
        WidgetScheduler.schedule(context)
        super.onUpdate(context, appWidgetManager, appWidgetIds)
    }

    override fun onDeleted(context: Context, appWidgetIds: IntArray) {
        val edit = context.getSharedPreferences("widget_installations", Context.MODE_PRIVATE).edit()
        appWidgetIds.forEach { edit.remove(it.toString()) }
        edit.apply()
        super.onDeleted(context, appWidgetIds)
    }

    override fun onDisabled(context: Context) {
        WidgetScheduler.cancel(context)
        super.onDisabled(context)
    }
}
