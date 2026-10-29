package com.pomp.hskai.widget

import android.appwidget.AppWidgetManager
import android.content.Context
import android.content.res.Configuration
import android.os.Bundle
import android.util.TypedValue
import android.widget.RemoteViews
import androidx.glance.appwidget.AndroidRemoteViews
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
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
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.update

class HskAiSmartWidget : GlanceAppWidget() {
    companion object {
        // A running Glance session can ignore an update with unchanged Preferences.
        // Explicit redraws must still re-evaluate expiry, local day and device zone.
        internal val renderClock = MutableStateFlow(java.time.ZonedDateTime.now())
        internal fun advanceClock() { renderClock.value = java.time.ZonedDateTime.now() }
    }

    override val sizeMode = SizeMode.Responsive(setOf(DpSize(130.dp, 48.dp), DpSize(130.dp, 110.dp), DpSize(260.dp, 110.dp)))

    override suspend fun provideGlance(context: Context, id: GlanceId) {
        val app = context.applicationContext as HskAiApplication
        val initial = app.widgetStore.read()
        val initialTheme = app.appSettings.themeMode.first()
        advanceClock()
        provideContent {
            val session by app.widgetStore.state.collectAsState(initial)
            val theme by app.appSettings.themeMode.collectAsState(initialTheme)
            val now by renderClock.collectAsState()
            val dark = theme == AppThemeMode.DARK || (theme == AppThemeMode.SYSTEM &&
                context.resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK == Configuration.UI_MODE_NIGHT_YES)
            WidgetContent(
                context = AppLocale.wrap(context),
                session = session,
                access = WidgetStateResolver.resolve(session, now),
                dark = dark,
                visual = WidgetVisualResolver.resolve(session, now),
            )
        }
    }
}

internal data class WidgetCopy(val message: String, val counter: String, val streakDescription: String)

/** Both launcher and install preview use the same truthful counter and copy. */
internal fun widgetCopy(
    context: Context,
    session: WidgetSession,
    access: WidgetAccess,
    visual: WidgetVisual,
): WidgetCopy {
    val asset = WidgetArt.assetFor(access, visual)
    val milestone = visual.special
        ?.takeIf { access == WidgetAccess.ACTIVE && it.kind == WidgetSpecialKind.MILESTONE }
    val message = if (milestone != null) context.getString(asset.text, milestone.days)
        else context.getString(asset.text)
    val permitted = access == WidgetAccess.FOUNDATION || access == WidgetAccess.ACTIVE
    val streak = session.snapshot?.streak?.takeIf { permitted && it >= 0 }
    return WidgetCopy(message, streak?.toString() ?: "HSK AI",
        streak?.let { context.resources.getQuantityString(R.plurals.widget_personal_streak_days,it,it) } ?: "HSK AI")
}

/** The launcher and Compose preview share the same rounded native typography. */
internal fun widgetHeaderViews(context: Context,copy: WidgetCopy,compact: Boolean,wide: Boolean,
                               palette: WidgetPandaArt.Palette): RemoteViews {
    val outlineIds=listOf(R.id.widget_streak_outline_n,R.id.widget_streak_outline_ne,
        R.id.widget_streak_outline_e,R.id.widget_streak_outline_se,R.id.widget_streak_outline_s,
        R.id.widget_streak_outline_sw,R.id.widget_streak_outline_w,R.id.widget_streak_outline_nw)
    return RemoteViews(context.packageName,R.layout.widget_streak_header).apply {
        setViewVisibility(R.id.widget_streak_flame,if(copy.counter=="HSK AI") android.view.View.GONE else android.view.View.VISIBLE)
        setImageViewResource(R.id.widget_streak_flame,if(palette.outlined) R.drawable.widget_streak_flame else R.drawable.widget_streak_flame_calm)
        for(id in outlineIds+R.id.widget_streak_count) {
            setTextViewText(id,copy.counter)
            setTextViewTextSize(id,TypedValue.COMPLEX_UNIT_SP,if(compact) 15f else if(wide) 28f else 20f)
        }
        outlineIds.forEach { setViewVisibility(it,if(palette.outlined) android.view.View.VISIBLE else android.view.View.GONE) }
        setTextColor(R.id.widget_streak_count,palette.counter.toArgb())
        setContentDescription(R.id.widget_streak_count,copy.streakDescription)
        setTextViewText(R.id.widget_streak_message,copy.message)
        setTextColor(R.id.widget_streak_message,palette.caption.toArgb())
        setTextViewTextSize(R.id.widget_streak_message,TypedValue.COMPLEX_UNIT_SP,if(wide) 12f else 9f)
    }
}

/** No scheduling, network calls or access decisions in the view. */
@Composable
internal fun WidgetContent(
    context: Context,
    session: WidgetSession,
    access: WidgetAccess,
    dark: Boolean,
    visual: WidgetVisual = WidgetVisualResolver.resolve(session),
) {
    val size = LocalSize.current
    val compact = size.height < 110.dp
    val wide = size.width >= 260.dp
    val palette = WidgetPandaArt.palette(dark,visual)

    val copy = widgetCopy(context, session, access, visual)

    // Every tap goes through CurrentLesson; MainActivity performs the fresh bearer/access check.
    val action = actionStartActivity(WidgetIntents.open(context, "widget"))
    val frame = GlanceModifier
        .fillMaxSize()
        .appWidgetBackground()
        .background(ColorProvider(palette.background))
        .cornerRadius(20.dp)
        .clickable(action)

    // Text and character occupy different cells, never overlapping layers.
    val header = widgetHeaderViews(context,copy,compact,wide,palette)
    val panda=WidgetPandaArt.bitmap(context,access,visual)
    if(compact || wide) {
        Row(modifier=frame,verticalAlignment=Alignment.CenterVertically) {
            AndroidRemoteViews(header,modifier=GlanceModifier.width(size.width*0.60f).fillMaxHeight())
            Image(provider=ImageProvider(panda),contentDescription=copy.message,
                modifier=GlanceModifier.defaultWeight().fillMaxHeight().padding(2.dp),contentScale=ContentScale.Fit)
        }
    } else {
        Column(modifier=frame,horizontalAlignment=Alignment.CenterHorizontally) {
            AndroidRemoteViews(header,modifier=GlanceModifier.fillMaxWidth().height(54.dp))
            Image(provider=ImageProvider(panda),contentDescription=copy.message,
                modifier=GlanceModifier.fillMaxWidth().defaultWeight(),contentScale=ContentScale.Fit)
        }
    }

}

class HskAiWidgetReceiver : GlanceAppWidgetReceiver() {
    override val glanceAppWidget = HskAiSmartWidget()

    companion object {
        /**
         * Counts widgets that newly landed on a home screen while this process
         * is alive. The install prompt watches it, because some launchers
         * confirm a pin without ever pausing the app.
         */
        internal val placements = MutableStateFlow(0)
    }

    override fun onUpdate(context: Context, appWidgetManager: AppWidgetManager, appWidgetIds: IntArray) {
        HskAiSmartWidget.advanceClock()
        // Only actual provider IDs mean "pinned". Dispatching a pin request is not success.
        val prefs = context.getSharedPreferences("widget_installations", Context.MODE_PRIVATE)
        val actual = appWidgetManager.getAppWidgetIds(android.content.ComponentName(context, javaClass)).toSet()
        val added = appWidgetIds.filter { it in actual && !prefs.contains(it.toString()) }
        if (added.isNotEmpty()) placements.update { it + 1 }
        added.forEach { id ->
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

    override fun onAppWidgetOptionsChanged(context: Context, appWidgetManager: AppWidgetManager,
                                           appWidgetId: Int, newOptions: Bundle) {
        HskAiSmartWidget.advanceClock()
        super.onAppWidgetOptionsChanged(context, appWidgetManager, appWidgetId, newOptions)
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
