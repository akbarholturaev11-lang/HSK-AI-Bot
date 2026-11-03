package com.pomp.hskai.feature.auth

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.ContextWrapper
import android.content.Intent
import android.os.Bundle
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.pomp.hskai.core.auth.authActivity
import com.pomp.hskai.core.design.PompHskAiTheme
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class ExternalAuthLaunchTest {
    @get:Rule val compose = createComposeRule()
    private class LaunchContext(base: Context, val fail: Boolean = false) : ContextWrapper(base) {
        val launches = mutableListOf<Intent>()
        override fun startActivity(intent: Intent) = record(intent)
        override fun startActivity(intent: Intent, options: Bundle?) = record(intent)
        private fun record(intent: Intent) {
            if (fail) throw ActivityNotFoundException("Synthetic missing provider")
            launches += intent
        }
    }
    @Test fun activityHandoffsShareTheHostTaskAndApplicationHandoffsRequireANewTask() {
        lateinit var hosted: LaunchContext
        compose.setContent { hosted = LaunchContext(LocalContext.current) }
        compose.runOnIdle {
            assertNotNull(hosted.authActivity())
            assertTrue(openCustomTab(hosted, "https://example.test/oauth"))
            assertTrue(openTelegram(hosted, "https://t.me/example_bot?start=test"))
            assertTrue(hosted.launches.all { it.flags and Intent.FLAG_ACTIVITY_NEW_TASK == 0 })
            val standalone = LaunchContext(InstrumentationRegistry.getInstrumentation().targetContext.applicationContext)
            assertTrue(openCustomTab(standalone, "https://example.test/oauth"))
            assertTrue(openTelegram(standalone, "https://t.me/example_bot?start=test"))
            assertTrue(standalone.launches.all { it.flags and Intent.FLAG_ACTIVITY_NEW_TASK != 0 })
        }
    }
    @Test fun failedBrowserHandoffIsReportedOnceAndNeverAcknowledgedAsOpened() = failure(true)
    @Test fun failedTelegramHandoffIsReportedOnceAndNeverAcknowledgedAsOpened() = failure(false)
    private fun failure(browser: Boolean) {
        val url = if (browser) "https://example.test/oauth" else "https://t.me/example_bot?start=test"
        var opened = 0
        val failures = mutableListOf<String>()
        compose.setContent {
            val failing = LaunchContext(LocalContext.current, fail = true)
            CompositionLocalProvider(LocalContext provides failing) {
                PompHskAiTheme {
                    LinkScreen(state = LinkUiState(
                        pendingBrowserUrl = url.takeIf { browser }, pendingTelegramUrl = url.takeUnless { browser }),
                        onBrowserUrlOpened = { opened++ }, onTelegramUrlOpened = { opened++ },
                        onExternalLaunchFailed = failures::add)
                }
            }
        }
        compose.runOnIdle { assertEquals(0, opened); assertEquals(listOf(url), failures) }
    }
}
