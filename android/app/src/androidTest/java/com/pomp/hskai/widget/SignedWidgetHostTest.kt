package com.pomp.hskai.widget

import android.Manifest
import android.appwidget.AppWidgetHost
import android.appwidget.AppWidgetHostView
import android.appwidget.AppWidgetManager
import android.content.ComponentName
import android.content.pm.ApplicationInfo
import android.os.Build
import android.os.Bundle
import android.util.SizeF
import android.view.View
import android.view.ViewGroup
import android.widget.FrameLayout
import android.widget.ImageView
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import java.util.concurrent.atomic.AtomicReference
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith

/** Bind the real normal signed APK, without seeding any account or grant. */
@RunWith(AndroidJUnit4::class)
class SignedWidgetHostTest {
    @Test fun normalSignedProviderRendersInARealHostWithoutCredentials() {
        val target = InstrumentationRegistry.getArguments().getString("signedWidgetPackage")
        assumeTrue(target == "com.pomp.hskai")
        check(Build.HARDWARE in setOf("ranchu", "goldfish")) { "Owned emulator only" }
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val context = instrumentation.targetContext
        val signed = context.createPackageContext(target, 0)
        assertEquals(0, signed.applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE)
        val manager = AppWidgetManager.getInstance(context)
        val provider = ComponentName(target!!, "com.pomp.hskai.widget.HskAiWidgetReceiver")
        val host = AppWidgetHost(context, 17756)
        val id = host.allocateAppWidgetId()
        val view = AtomicReference<AppWidgetHostView>()
        try {
            instrumentation.uiAutomation.adoptShellPermissionIdentity(Manifest.permission.BIND_APPWIDGET)
            val bound = try {
                manager.bindAppWidgetIdIfAllowed(id, provider, Bundle().apply {
                    putInt(AppWidgetManager.OPTION_APPWIDGET_MIN_WIDTH, 130)
                    putInt(AppWidgetManager.OPTION_APPWIDGET_MIN_HEIGHT, 110)
                    putInt(AppWidgetManager.OPTION_APPWIDGET_MAX_WIDTH, 260)
                    putInt(AppWidgetManager.OPTION_APPWIDGET_MAX_HEIGHT, 210)
                    if (Build.VERSION.SDK_INT >= 31) {
                        putParcelableArrayList(AppWidgetManager.OPTION_APPWIDGET_SIZES, arrayListOf(SizeF(170f, 210f)))
                    }
                })
            } finally { instrumentation.uiAutomation.dropShellPermissionIdentity() }
            assertTrue("Fixture host must bind the actual signed receiver", bound)
            ActivityScenario.launch(ComponentActivity::class.java).use { scenario ->
                scenario.onActivity { activity ->
                    view.set(host.createView(activity, id, manager.getAppWidgetInfo(id)))
                    val density = activity.resources.displayMetrics.density
                    val container = FrameLayout(activity)
                    container.addView(view.get(), FrameLayout.LayoutParams(
                        (170 * density).toInt(), (210 * density).toInt()))
                    activity.setContentView(container)
                    host.startListening()
                }
                val countId = signed.resources.getIdentifier("widget_streak_count", "id", target)
                assertNotEquals(0, countId)
                var rendered = false
                val deadline = android.os.SystemClock.elapsedRealtime() + 30_000
                while (!rendered && android.os.SystemClock.elapsedRealtime() < deadline) {
                    instrumentation.runOnMainSync {
                        rendered = view.get()?.findViewById<TextView>(countId)?.text?.toString() == "HSK AI"
                    }
                    if (!rendered) Thread.sleep(100)
                }
                assertTrue("Signed provider must produce the native neutral header, not an error view", rendered)
                instrumentation.runOnMainSync {
                    val messageId = signed.resources.getIdentifier("widget_streak_message", "id", target)
                    val message = view.get().findViewById<TextView>(messageId)?.text
                    val panda = descendants(view.get()).filterIsInstance<ImageView>()
                        .firstOrNull { it.contentDescription == message && message != null }
                    assertNotNull("Signed portrait host must receive the panda image view", panda)
                    assertTrue("Panda must have drawable content and visible space",
                        panda!!.isShown && panda.width > 0 && panda.height > 0 && panda.drawable != null)
                }
            }
        } finally { host.stopListening(); host.deleteAppWidgetId(id) }
    }

    private fun descendants(view: View): Sequence<View> = sequence {
        yield(view)
        if (view is ViewGroup) {
            for (index in 0 until view.childCount) yieldAll(descendants(view.getChildAt(index)))
        }
    }
}
