package com.pomp.hskai.widget

import android.Manifest
import android.appwidget.AppWidgetManager
import android.content.ComponentName
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.Rect
import android.os.Build
import android.view.KeyEvent
import android.view.accessibility.AccessibilityNodeInfo
import androidx.datastore.preferences.core.emptyPreferences
import androidx.glance.appwidget.GlanceAppWidgetManager
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.pomp.hskai.BuildConfig
import com.pomp.hskai.HskAiApplication
import com.pomp.hskai.MainActivity
import com.pomp.hskai.core.i18n.AppLanguage
import com.pomp.hskai.core.i18n.AppLocale
import java.io.File
import java.time.ZonedDateTime
import kotlinx.coroutines.runBlocking
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.encodeToJsonElement
import kotlinx.serialization.json.jsonObject
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith

/** Opt-in system-launcher checks, restricted to the isolated synthetic QA APK. */
@RunWith(AndroidJUnit4::class)
class WidgetLauncherTest {
    private val instrumentation = InstrumentationRegistry.getInstrumentation()
    private val context = instrumentation.targetContext
    private val app get() = context.applicationContext as HskAiApplication
    private val ui get() = instrumentation.uiAutomation
    private val manager get() = AppWidgetManager.getInstance(context)
    private val provider get() = ComponentName(context, HskAiWidgetReceiver::class.java)
    private val output by lazy {
        File(context.getExternalFilesDir(null), InstrumentationRegistry.getArguments()
            .getString("widgetQaOutput") ?: "widget-launcher-qa").apply { mkdirs() }
    }

    @Test fun pinResizeRefreshAndTapWithOffAndDeniedPermission() = runBlocking {
        assumeTrue(InstrumentationRegistry.getArguments().getString("widgetHost") == "true")
        check(BuildConfig.QA_BUILD && BuildConfig.APPLICATION_ID.endsWith(".qa"))
        check(Build.HARDWARE in setOf("ranchu", "goldfish")) { "Use the owned QA emulator" }
        ui.serviceInfo = ui.serviceInfo.apply {
            flags = flags or android.accessibilityservice.AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS
        }
        assertTrue(manager.isRequestPinAppWidgetSupported)
        assertFalse(app.widgetStore.read().reminderEnabled)
        assertEquals(PackageManager.PERMISSION_DENIED,
            context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS))
        val before = manager.getAppWidgetIds(provider).toSet()
        assertTrue("Start with a fresh isolated QA installation", before.isEmpty())
        var placed = AppWidgetManager.INVALID_APPWIDGET_ID
        ActivityScenario.launch(MainActivity::class.java).use {
            assertTrue(GlanceAppWidgetManager(context).requestPinGlanceAppWidget(
                receiver = HskAiWidgetReceiver::class.java,
                preview = HskAiSmartWidget(), previewState = emptyPreferences()))
            val add = awaitNode { node ->
                node.isClickable && node.text?.toString()?.lowercase()?.let { text ->
                    text == "add to home screen" || text == "add automatically"
                } == true
            }
            capture("pin-dialog")
            assertTrue(add.performAction(AccessibilityNodeInfo.ACTION_CLICK))
            awaitCondition { manager.getAppWidgetIds(provider).any { id -> id !in before } }
            placed = manager.getAppWidgetIds(provider).single { it !in before }
            assertFalse(app.widgetStore.read().reminderEnabled)
            assertEquals(PackageManager.PERMISSION_DENIED,
                context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS))
        }
        // The real pin receiver has run. Isolate deterministic cached-frame checks
        // from its no-credential refresh; no production account or bearer is seeded.
        WidgetScheduler.cancel(context)
        androidx.work.WorkManager.getInstance(context).cancelAllWork().result.get()
        home()
        val workspace = awaitNode { it.viewIdResourceName?.endsWith("/workspace") == true }
        if (nodes(ui.rootInActiveWindow).none { isHost(it) && visible(it) }) {
            assertTrue(workspace.performAction(AccessibilityNodeInfo.ACTION_SCROLL_FORWARD))
        }
        awaitNode(::isHost)
        recordHost(placed, "pinned")
        capture("pinned")

        for (language in AppLanguage.entries) {
            AppLocale.sync(context, language)
            assertEquals(language, AppLocale.current(context))
            for (phase in listOf("before_study", "study_time_reached", "completed")) {
                seed(phase)
                app.widgetCoordinator.render()
                val session = app.widgetStore.read()
                val expected = widgetCopy(AppLocale.wrap(context), session,
                    WidgetStateResolver.resolve(session), WidgetVisualResolver.resolve(session))
                awaitNode { it.text?.toString() == expected.message }
                assertTrue(nodes(ui.rootInActiveWindow).any { visible(it) && it.text?.toString() == "8" })
                capture("${language.androidTag}-$phase")
                assertPassive()
            }
        }
        val host = awaitNode(::isHost)
        File(output, "host-actions.txt").writeText(host.actionList.joinToString("\n") { "${it.id}: ${it.label}" })
        val resize = host.actionList.single { it.label?.toString()?.equals("Resize", true) == true }
        assertTrue(host.performAction(resize.id))
        capture("resize-menu")
        val increase = awaitNode { it.text?.toString() == "Increase width" }
        click(increase)
        awaitCondition { manager.getAppWidgetOptions(placed).getInt(AppWidgetManager.OPTION_APPWIDGET_MIN_WIDTH) >= 260 }
        awaitNode(::isHost)
        recordHost(placed, "resized")
        capture("resized")
        val height = manager.getAppWidgetOptions(placed).getInt(AppWidgetManager.OPTION_APPWIDGET_MIN_HEIGHT)
        val verticalHost = awaitNode(::isHost)
        assertTrue(verticalHost.performAction(verticalHost.actionList.single { it.label?.toString() == "Resize" }.id))
        click(awaitNode { it.text?.toString() == "Decrease height" })
        awaitCondition { manager.getAppWidgetOptions(placed).getInt(AppWidgetManager.OPTION_APPWIDGET_MIN_HEIGHT) < height }
        recordHost(placed, "shortened")
        capture("shortened")

        seed("study_time_reached", expiresInSeconds = 2)
        app.widgetCoordinator.render()
        Thread.sleep(2_100)
        app.widgetCoordinator.render()
        assertEquals("neutral", WidgetVisualResolver.resolve(app.widgetStore.read()).personalPhase)
        awaitCurrentCopy()
        capture("expired-after-redraw")
        assertPassive()

        seed("completed")
        val originalZone = ZonedDateTime.now().zone.id
        try {
            shell("cmd alarm set-timezone Pacific/Pago_Pago")
            awaitCondition { ZonedDateTime.now().zone.id == "Pacific/Pago_Pago" }
            // Exercise the real OS broadcast; the previous day/zone cannot stay current.
            // Preference sync can also discover the deliberately missing QA auth
            // and clear the link. Both outcomes must remove the personal frame.
            awaitSafeCopy()
            assertTrue(WidgetStateResolver.resolve(app.widgetStore.read()) in setOf(WidgetAccess.STALE, WidgetAccess.UNLINKED))
            assertEquals("neutral", WidgetVisualResolver.resolve(app.widgetStore.read()).personalPhase)
            capture("zone-and-day-change")
            assertPassive()
        } finally {
            shell("cmd alarm set-timezone $originalZone")
            awaitCondition { ZonedDateTime.now().zone.id == originalZone }
            WidgetScheduler.cancel(context)
        }

        // Roll back the optional projection while retaining ordinary linked data.
        seed("completed")
        val old = app.widgetStore.read()
        val pending = requireNotNull(app.widgetStore.beginRefresh(old.epoch))
        app.widgetStore.clear()
        app.widgetCoordinator.render()
        awaitCurrentCopy()
        assertFalse(nodes(ui.rootInActiveWindow).any { visible(it) && it.text?.toString() == "8" })
        capture("logout")
        app.widgetStore.linked(newSession = true)
        assertFalse(app.widgetStore.savePersonal(requireNotNull(old.snapshot), old.snapshot.personalContext,
            pending, ZonedDateTime.now()))
        val linked = app.widgetStore.read()
        app.widgetStore.save(old.snapshot.copy(personalContext = null), linked.epoch)
        app.widgetCoordinator.render()
        awaitCurrentCopy()
        assertEquals("neutral", WidgetVisualResolver.resolve(app.widgetStore.read()).personalPhase)
        capture("relink-and-legacy-rollback")
        assertPassive()

        // Unknown future wire data must preserve linking, without personal mood.
        seed("study_time_reached", future = true)
        app.widgetCoordinator.render()
        assertEquals("neutral", WidgetVisualResolver.resolve(app.widgetStore.read()).personalPhase)
        awaitCurrentCopy()
        capture("future-neutral")
        assertPassive()

        // Actual passive refresh with no credentials clears cached proof safely.
        seed("completed")
        app.widgetCoordinator.refresh()
        assertNull(app.widgetStore.read().snapshot)
        app.widgetCoordinator.render()
        awaitSafeCopy()
        capture("offline-neutral")
        assertPassive()

        // A launcher click uses the ordinary entry intent and cannot grant auth.
        val monitor = instrumentation.addMonitor(MainActivity::class.java.name, null, false)
        // Missing credentials may also finish invalidation and show UNLINKED.
        // Both states use the same normal entry, rather than a cached lesson grant.
        click(awaitNode { it.packageName?.toString() == context.packageName && it.isClickable })
        val opened = instrumentation.waitForMonitorWithTimeout(monitor, 10_000)
        try {
            assertNotNull("Widget did not open MainActivity", opened)
            assertEquals("widget", opened.intent.getStringExtra(WidgetIntents.SOURCE))
            assertEquals(WidgetIntents.open(context, "widget").data, opened.intent.data)
            awaitCondition { ui.rootInActiveWindow?.packageName?.toString() == context.packageName }
            assertTrue(app.authRepository.authenticatedSession() is com.pomp.hskai.core.network.ApiResult.Failure)
            val greetings = AppLanguage.entries.map { language ->
                context.createConfigurationContext(android.content.res.Configuration(context.resources.configuration).apply {
                    setLocale(java.util.Locale.forLanguageTag(language.androidTag))
                }).getString(com.pomp.hskai.R.string.auth_welcome_greeting)
            }.toSet()
            awaitNode { it.text?.toString() in greetings }
            capture("tap-unauthenticated")
            assertPassive()
        } finally {
            instrumentation.removeMonitor(monitor)
            opened?.let { activity -> instrumentation.runOnMainSync { activity.finish() } }
        }
    }

    private suspend fun seed(phase: String, future: Boolean = false, expiresInSeconds: Long = 600) {
        app.widgetStore.linked(newSession = true)
        val session = app.widgetStore.read()
        val now = ZonedDateTime.now()
        val complete = phase == "completed"
        val envelope = WidgetPersonalContext(1, "smart-widget-context-v1", "a".repeat(64), session.epoch, 1,
            now.minusSeconds(1).toInstant().toString(), minOf(now.plusSeconds(expiresInSeconds).toInstant(),
                now.toLocalDate().plusDays(1).atStartOfDay(now.zone).toInstant()).toString(),
            "hsk1", "hsk20", now.toLocalDate().toString(), now.zone.id, 5, 100,
            if (complete) 20 else 0, 20, if (complete) "met" else "not_proven", false,
            if (complete) null else "14:00", if (complete) "unknown" else "saved", "qa_fixture", phase,
            if (complete) "goal_completed" else if (phase == "before_study") "before_personal_time" else "personal_time_reached",
            if (complete) "course" else "continue", if (complete) null else 6, emptyList(), null, false, true)
        val raw = Json.encodeToJsonElement(envelope)
        val snapshot = WidgetSnapshot(now.toInstant().toEpochMilli(), now.toLocalDate().toString(), now.zone.id,
            "hsk1", 6, 500, 8, false, false, personalContext = raw)
        val ticket = requireNotNull(app.widgetStore.beginRefresh(session.epoch))
        if (future) {
            // A future wire version is refused without losing the linked session.
            val unknown = kotlinx.serialization.json.JsonObject(raw.jsonObject + ("version" to JsonPrimitive(2)))
            assertFalse(app.widgetStore.savePersonal(snapshot, unknown, ticket, now))
            assertTrue(app.widgetStore.read().linked)
        } else assertTrue(app.widgetStore.savePersonal(snapshot, raw, ticket, now))
    }

    private suspend fun assertPassive() {
        val session = app.widgetStore.read()
        assertFalse(session.reminderEnabled)
        assertNull(session.lastReminderDay)
        assertTrue(session.events.all { it.event_name in setOf("android_widget_pinned", "android_widget_opened") })
        assertEquals(PackageManager.PERMISSION_DENIED,
            context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS))
        assertTrue(androidx.work.WorkManager.getInstance(context)
            .getWorkInfosForUniqueWork("study_reminder_daily").get().all { it.state.isFinished })
    }

    private suspend fun awaitCurrentCopy() {
        val session = app.widgetStore.read()
        val expected = widgetCopy(AppLocale.wrap(context), session,
            WidgetStateResolver.resolve(session), WidgetVisualResolver.resolve(session))
        awaitNode { it.text?.toString() == expected.message }
    }

    private fun awaitSafeCopy() {
        val localized = AppLocale.wrap(context)
        val allowed = setOf(localized.getString(com.pomp.hskai.R.string.widget_stale),
            localized.getString(com.pomp.hskai.R.string.widget_unlinked))
        awaitNode { it.text?.toString() in allowed }
    }

    private fun shell(command: String) {
        ui.executeShellCommand(command).use { descriptor ->
            android.os.ParcelFileDescriptor.AutoCloseInputStream(descriptor).bufferedReader().use { it.readText() }
        }
    }

    private fun recordHost(id: Int, label: String) {
        val options = manager.getAppWidgetOptions(id)
        File(output, "$label-host.txt").writeText("provider=$provider\nid=$id\n" +
            options.keySet().sorted().joinToString("\n") { "$it=${options.get(it)}" })
    }

    private fun isHost(node: AccessibilityNodeInfo) = node.className?.toString()?.contains("AppWidgetHostView") == true

    private fun visible(node: AccessibilityNodeInfo): Boolean {
        val bounds = Rect().also(node::getBoundsInScreen)
        return node.isVisibleToUser && !bounds.isEmpty
    }

    private fun click(node: AccessibilityNodeInfo) {
        val target = generateSequence(node) { it.parent }.first { it.isClickable }
        assertTrue(target.performAction(AccessibilityNodeInfo.ACTION_CLICK))
    }

    private fun home() {
        ui.injectInputEvent(KeyEvent(KeyEvent.ACTION_DOWN, KeyEvent.KEYCODE_HOME), true)
        ui.injectInputEvent(KeyEvent(KeyEvent.ACTION_UP, KeyEvent.KEYCODE_HOME), true)
        awaitNode { it.viewIdResourceName?.endsWith("/workspace") == true }
    }

    private fun awaitCondition(predicate: () -> Boolean) {
        val deadline = android.os.SystemClock.uptimeMillis() + 15_000
        while (!predicate() && android.os.SystemClock.uptimeMillis() < deadline) Thread.sleep(100)
        assertTrue("Launcher condition timed out; ${dump()}", predicate())
    }

    private fun awaitNode(predicate: (AccessibilityNodeInfo) -> Boolean): AccessibilityNodeInfo {
        var found: AccessibilityNodeInfo? = null
        awaitCondition { found = nodes(ui.rootInActiveWindow).firstOrNull { visible(it) && predicate(it) }; found != null }
        return requireNotNull(found)
    }

    private fun nodes(node: AccessibilityNodeInfo?): List<AccessibilityNodeInfo> =
        if (node == null) emptyList() else listOf(node) + (0 until node.childCount).flatMap { nodes(node.getChild(it)) }

    private fun dump() = nodes(ui.rootInActiveWindow).joinToString("\n") {
        val bounds = Rect().also(it::getBoundsInScreen)
        "${it.packageName} ${it.className} ${it.text} ${it.contentDescription} clickable=${it.isClickable} bounds=$bounds"
    }

    private fun capture(name: String) {
        File(output, "$name.txt").writeText(dump())
        ui.takeScreenshot()?.let { bitmap ->
            File(output, "$name.png").outputStream().use { bitmap.compress(Bitmap.CompressFormat.PNG, 100, it) }
            bitmap.recycle()
        }
    }
}
