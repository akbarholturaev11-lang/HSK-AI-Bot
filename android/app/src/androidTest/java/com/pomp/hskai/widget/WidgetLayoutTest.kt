package com.pomp.hskai.widget

import android.content.res.Configuration
import android.graphics.Bitmap
import android.graphics.Canvas
import android.view.View
import android.view.ViewGroup
import android.widget.FrameLayout
import android.widget.TextView
import androidx.compose.ui.unit.DpSize
import androidx.compose.ui.unit.dp
import androidx.glance.appwidget.ExperimentalGlanceRemoteViewsApi
import androidx.glance.appwidget.GlanceRemoteViews
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.pomp.hskai.HskAiApplication
import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.core.i18n.AppLocale
import com.pomp.hskai.core.settings.AppThemeMode
import java.io.File
import java.time.ZonedDateTime
import java.util.Locale
import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith

@OptIn(ExperimentalGlanceRemoteViewsApi::class)
@RunWith(AndroidJUnit4::class)
class WidgetLayoutTest {
    private val instrumentation = InstrumentationRegistry.getInstrumentation()
    private val context = instrumentation.targetContext
    private fun snapshot(): WidgetSnapshot {
        val now = ZonedDateTime.now()
        return WidgetSnapshot(now.toInstant().toEpochMilli(), now.toLocalDate().toString(), now.zone.id, "hsk1", 12, 840, 7, false, false)
    }

    @Test fun rendersEverySizeLanguageThemeAndState() = runBlocking {
        val sizes = listOf(DpSize(130.dp, 48.dp), DpSize(130.dp, 110.dp), DpSize(260.dp, 110.dp))
        val renderer = GlanceRemoteViews()
        val visual = WidgetVisual(WidgetVisualState.DAY, 0)
        for (language in listOf("uz", "ru", "tg")) for (dark in listOf(false, true)) {
            val config = Configuration(context.resources.configuration).apply { setLocale(Locale.forLanguageTag(language)) }
            val localized = context.createConfigurationContext(config)
            for (size in sizes) for (access in WidgetAccess.entries) {
                val session = WidgetSession(linked = access != WidgetAccess.UNLINKED, snapshot = snapshot())
                val views = renderer.compose(localized, size) { WidgetContent(localized, session, access, dark, visual) }.remoteViews
                instrumentation.runOnMainSync {
                    val parent = FrameLayout(localized)
                    val view = views.apply(localized, parent)
                    val density = context.resources.displayMetrics.density
                    val width = (size.width.value * density).toInt()
                    val height = (size.height.value * density).toInt()
                    view.measure(View.MeasureSpec.makeMeasureSpec(width, View.MeasureSpec.EXACTLY), View.MeasureSpec.makeMeasureSpec(height, View.MeasureSpec.EXACTLY))
                    view.layout(0, 0, width, height)
                    val texts = textViews(view)
                    assertTrue("Missing widget copy: $language $size $access", texts.isNotEmpty())
                    if (access == WidgetAccess.STALE || access == WidgetAccess.UNLINKED) {
                        assertFalse(texts.any { it.text.contains("840") })
                    } else assertTrue(texts.any { it.text.contains("840") })
                    // All labels remain inside the host at the provider's minimum dimensions.
                    texts.forEach { text ->
                        assertTrue("Clipped vertically: $language $size $access ${text.text}", text.height >= (text.layout?.height ?: 0))
                    }
                    if (access == WidgetAccess.ACTIVE || (language == "uz" && !dark && size == sizes.last())) {
                        val image = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
                        view.draw(Canvas(image))
                        val folder = File(context.getExternalFilesDir(null), "widget-qa").apply { mkdirs() }
                        File(folder, "$language-${if (dark) "dark" else "light"}-${size.width.value.toInt()}x${size.height.value.toInt()}-$access.png")
                            .outputStream().use { image.compress(Bitmap.CompressFormat.PNG, 100, it) }
                        image.recycle()
                    }
                }
            }
        }
    }

    /** All 28 drawings and all 28 lines have to fit the same layout. */
    @Test fun rendersEveryStateAndVariant() = runBlocking {
        val renderer = GlanceRemoteViews()
        val sizes = listOf(DpSize(130.dp, 48.dp), DpSize(130.dp, 110.dp), DpSize(260.dp, 110.dp))
        val session = WidgetSession(linked = true, snapshot = snapshot().copy(dailyXp = 20, goalXp = 50))
        for (language in listOf("uz", "ru", "tg")) {
            val config = Configuration(context.resources.configuration).apply { setLocale(Locale.forLanguageTag(language)) }
            val localized = context.createConfigurationContext(config)
            for (state in WidgetVisualState.entries) for (variant in 0 until state.variants) for (size in sizes) {
                // A milestone is the only special state with a producer, and it
                // is the one line that takes a number.
                val special = if (state == WidgetVisualState.COMPLETED && variant == 0)
                    WidgetSpecialState(WidgetSpecialKind.MILESTONE, 30) else null
                val visual = WidgetVisual(state, variant, special)
                val views = renderer.compose(localized, size) {
                    WidgetContent(localized, session, WidgetAccess.ACTIVE, false, visual)
                }.remoteViews
                instrumentation.runOnMainSync {
                    val parent = FrameLayout(localized)
                    val view = views.apply(localized, parent)
                    val density = context.resources.displayMetrics.density
                    val width = (size.width.value * density).toInt()
                    val height = (size.height.value * density).toInt()
                    view.measure(View.MeasureSpec.makeMeasureSpec(width, View.MeasureSpec.EXACTLY), View.MeasureSpec.makeMeasureSpec(height, View.MeasureSpec.EXACTLY))
                    view.layout(0, 0, width, height)
                    val texts = textViews(view)
                    assertTrue("Missing widget copy: $language $state/$variant $size", texts.isNotEmpty())
                    // Today against today's goal, never the lifetime total.
                    assertTrue("Missing goal progress: $language $state/$variant", texts.any { it.text.contains("20") && it.text.contains("50") })
                    texts.forEach { text ->
                        assertTrue("Clipped vertically: $language $state/$variant ${text.text}", text.height >= (text.layout?.height ?: 0))
                    }
                }
            }
        }
    }

    /** Opt-in fixture for launcher inspection. Only exists in the instrumentation APK. */
    @Test fun launcherFixture() = runBlocking {
        val args = InstrumentationRegistry.getArguments()
        assumeTrue(args.getString("widgetFixture") == "true")
        val app = context.applicationContext as HskAiApplication
        androidx.work.WorkManager.getInstance(context).cancelAllWork().result.get()
        app.widgetStore.linked(newSession = true)
        val session = app.widgetStore.read()
        val mood = args.getString("mood") ?: "active"
        val fixture = snapshot().copy(
            dayComplete = mood == "complete", foundationRequired = mood == "foundation",
            fetchedAtMillis = if (mood == "stale") 1 else System.currentTimeMillis(),
            // Drive the asking line and the panda face from the command line:
            // "-e dailyXp 0" at night is the streak-at-risk face.
            dailyXp = args.getString("dailyXp")?.toIntOrNull() ?: 20,
            goalXp = args.getString("goalXp")?.toIntOrNull() ?: 50,
        )
        app.widgetStore.save(fixture, session.epoch)
        if (mood == "unlinked") app.widgetStore.clear()
        AppLocale.sync(context, AppLanguage.fromBackendCode(args.getString("language") ?: "uz"))
        app.appSettings.setThemeMode(if (args.getString("theme") == "dark") AppThemeMode.DARK else AppThemeMode.LIGHT)
        app.widgetCoordinator.render()
    }

    private fun textViews(view: View): List<TextView> = when (view) {
        is TextView -> listOf(view)
        is ViewGroup -> (0 until view.childCount).flatMap { textViews(view.getChildAt(it)) }
        else -> emptyList()
    }
}
