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
        for (language in listOf("uz", "ru", "tg")) for (dark in listOf(false, true)) {
            val config = Configuration(context.resources.configuration).apply { setLocale(Locale.forLanguageTag(language)) }
            val localized = context.createConfigurationContext(config)
            for (size in sizes) for (mood in WidgetMood.entries) {
                val session = WidgetSession(linked = mood != WidgetMood.UNLINKED, snapshot = snapshot())
                val views = renderer.compose(localized, size) { WidgetContent(localized, session, mood, dark) }.remoteViews
                instrumentation.runOnMainSync {
                    val parent = FrameLayout(localized)
                    val view = views.apply(localized, parent)
                    val density = context.resources.displayMetrics.density
                    val width = (size.width.value * density).toInt()
                    val height = (size.height.value * density).toInt()
                    view.measure(View.MeasureSpec.makeMeasureSpec(width, View.MeasureSpec.EXACTLY), View.MeasureSpec.makeMeasureSpec(height, View.MeasureSpec.EXACTLY))
                    view.layout(0, 0, width, height)
                    val texts = textViews(view)
                    assertTrue("Missing widget copy: $language $size $mood", texts.isNotEmpty())
                    if (mood == WidgetMood.STALE || mood == WidgetMood.UNLINKED) {
                        assertFalse(texts.any { it.text.contains("840") })
                    } else assertTrue(texts.any { it.text.contains("840") })
                    // All labels remain inside the host at the provider's minimum dimensions.
                    texts.forEach { text ->
                        assertTrue("Clipped vertically: $language $size $mood ${text.text}", text.height >= (text.layout?.height ?: 0))
                    }
                    if (mood == WidgetMood.CONTINUE || (language == "uz" && !dark && size == sizes.last())) {
                        val image = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
                        view.draw(Canvas(image))
                        val folder = File(context.getExternalFilesDir(null), "widget-qa").apply { mkdirs() }
                        File(folder, "$language-${if (dark) "dark" else "light"}-${size.width.value.toInt()}x${size.height.value.toInt()}-$mood.png")
                            .outputStream().use { image.compress(Bitmap.CompressFormat.PNG, 100, it) }
                        image.recycle()
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
        val mood = args.getString("mood") ?: "continue"
        val fixture = snapshot().copy(
            dayComplete = mood == "complete", foundationRequired = mood == "foundation",
            fetchedAtMillis = if (mood == "stale") 1 else System.currentTimeMillis(),
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
