package com.pomp.hskai.widget

import android.appwidget.AppWidgetManager
import android.content.Context
import android.content.res.Configuration
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.graphics.Color
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
            WidgetContent(
                context = AppLocale.wrap(context),
                session = session,
                access = WidgetStateResolver.resolve(session.linked, session.snapshot, now),
                dark = dark,
                visual = WidgetVisualResolver.resolve(session.snapshot, session.epoch, now),
            )
        }
    }
}

/** No scheduling, network calls or access decisions in the view. */
@Composable
internal fun WidgetContent(
    context: Context,
    session: WidgetSession,
    access: WidgetAccess,
    dark: Boolean,
    visual: WidgetVisual = WidgetVisualResolver.resolve(session.snapshot, session.epoch),
) {
    val size = LocalSize.current
    val compact = size.height < 110.dp
    val wide = size.width >= 260.dp
    val palette = PompColors.paletteFor(dark)

    // One engine chose the state, one table chose the drawing and the line.
    // The artwork fills the widget; copy is a readable overlay on top of it.
    val asset = WidgetArt.assetFor(access, visual)
    val milestone = visual.special
        ?.takeIf { access == WidgetAccess.ACTIVE && it.kind == WidgetSpecialKind.MILESTONE }
    val message = if (milestone != null) context.getString(asset.text, milestone.days)
        else context.getString(asset.text)
    val fresh = access == WidgetAccess.FOUNDATION || access == WidgetAccess.ACTIVE
    val snapshot = session.snapshot

    // Today against today's goal is what decides whether to open the app;
    // the lifetime total is kept only while the goal is still unknown.
    val stats = when {
        !fresh || snapshot == null -> context.getString(R.string.widget_open)
        snapshot.goalXp > 0 ->
            context.getString(R.string.widget_stats_goal, snapshot.dailyXp, snapshot.goalXp, snapshot.streak)
        else -> context.getString(R.string.widget_stats, snapshot.xp, snapshot.streak)
    }
    val lesson = if (fresh && snapshot?.lessonOrder != null)
        context.getString(R.string.widget_lesson, snapshot.level.uppercase(), snapshot.lessonOrder) else "HSK AI"

    // Every tap goes through CurrentLesson; MainActivity performs the fresh bearer/access check.
    val action = actionStartActivity(WidgetIntents.open(context, "widget"))
    val frame = GlanceModifier
        .fillMaxSize()
        .appWidgetBackground()
        .background(palette.paper)
        .cornerRadius(20.dp)
        .clickable(action)

    val overlay = GlanceModifier
        .fillMaxWidth()
        .padding(if (compact) 4.dp else 8.dp)
        .background(ColorProvider(Color.Black.copy(alpha = if (dark) 0.68f else 0.58f)))
        .cornerRadius(if (compact) 10.dp else 14.dp)
        .padding(
            horizontal = if (compact) 7.dp else 10.dp,
            vertical = if (compact) 4.dp else 7.dp,
        )

    val primary = ColorProvider(Color.White)
    val secondary = ColorProvider(Color.White.copy(alpha = 0.84f))

    Box(modifier = frame, contentAlignment = Alignment.BottomStart) {
        Image(
            provider = ImageProvider(asset.drawable()),
            contentDescription = message,
            modifier = GlanceModifier.fillMaxSize().cornerRadius(20.dp),
            contentScale = ContentScale.Crop,
        )

        Column(modifier = overlay) {
            if (wide) {
                Text(
                    lesson,
                    style = TextStyle(
                        color = secondary,
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                    ),
                    maxLines = 1,
                )
                Spacer(GlanceModifier.height(2.dp))
            }
            Text(
                message,
                style = TextStyle(
                    color = primary,
                    fontSize = when {
                        wide -> 15.sp
                        compact -> 11.sp
                        else -> 13.sp
                    },
                    fontWeight = FontWeight.Bold,
                ),
                maxLines = if (compact) 1 else 2,
            )
            Text(
                stats,
                style = TextStyle(
                    color = secondary,
                    fontSize = if (compact) 9.sp else 10.sp,
                ),
                maxLines = 1,
            )
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
